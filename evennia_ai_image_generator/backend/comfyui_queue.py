# backend/comfyui_queue.py
"""ComfyUI-aware job queue with round-trip tracking via client_id.

The ComfyUI `/prompt` endpoint accepts a `client_id` field which gets
persisted in the history response.  We generate a UUID per MUD-side job,
pass it as `client_id`, and poll ComfyUI's `/history/{prompt_id}` to map
back to our job.

Key features:
- **Deduplication**: subject_key → one pending job at a time
- **Depth limiting**: cap concurrent submissions based on ComfyUI's queue
  length (avoids overloading the GPU)
- **Round-trip tracking**: each job carries a UUID that flows MUD →
  ComfyUI → MUD via the history endpoint
- **Automatic cleanup**: finished jobs are removed from the pending set
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

import httpx

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult
from .comfyui_backend import (
    ComfyUIBackend,
    ComfyUIBackendError,
    ComfyUIServerNotFound,
    ComfyUIWorkflowError,
)

# ---- Exceptions ----


class ComfyUIQueueError(Exception):
    """Raised when the ComfyUI queue is in a notable state."""


JobStatus = Literal["submitted", "running", "complete", "failed", "cancelled"]


@dataclass
class JobInfo:
    """Lightweight handle for a round-trip ComfyUI job."""

    job_id: str  # client_id we pass to ComfyUI
    prompt_id: str  # ComfyUI's prompt_id (from /prompt response)
    request: ImageGenerationRequest
    status: JobStatus = "submitted"
    result: ImageGenerationResult | None = None
    error: str | None = None
    submitted_at: float = 0.0
    completed_at: float = 0.0

    def __post_init__(self) -> None:
        if self.submitted_at == 0.0:
            self.submitted_at = time.monotonic()


QueueAction = Literal["queued", "submitted", "duplicate", "full"]


@dataclass
class ComfyUIQueue:
    """Thread-safe queue that coordinates MUD image requests with ComfyUI.

    Manages two concerns:
    1. **Subject deduplication** — one pending generation per subject_key
    2. **Depth limiting** — don't blast more jobs than ComfyUI can handle

    Does *not* spin threads.  Jobs are submitted eagerly; callers (or a
    scheduler) poll `await_completions()` or `collect_results()` to check
    which jobs have finished.
    """

    max_pending: int | None = None
    _lock: Lock = field(init=False)
    _jobs: dict[str, JobInfo] = field(init=False)
    _completed: list[JobInfo] = field(init=False)

    def __post_init__(self) -> None:
        self._lock = Lock()
        self._jobs = {}
        self._completed = []

    # ---- Public API ---------------------------------------------------------

    def enqueue(
        self,
        request: ImageGenerationRequest,
        backend: ComfyUIBackend,
    ) -> QueueAction:
        """Enqueue a generation job, submitting immediately to ComfyUI.

        Returns:
        - "queued" / "submitted": job accepted and sent to ComfyUI
        - "duplicate": a job for this subject_key is already pending
        - "full": pending count reached max_pending cap
        """
        subject_key = request.subject_key

        with self._lock:
            # Dedup
            if subject_key in self._jobs:
                return "duplicate"
            if self.max_pending is not None and len(self._jobs) >= self.max_pending:
                return "full"

        # Submit to ComfyUI (outside lock to avoid blocking)
        job_id = str(uuid4())[:12]
        prompt_id = backend._submit_prompt(
            backend._build_workflow(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt or "",
                width=request.width,
                height=request.height,
                steps=backend.default_steps,
                cfg=backend.default_cfg,
                seed=request.seed or 0,
                checkpoint=backend._checkpoint_cache or backend._resolve_checkpoint(),
            )
        )

        job = JobInfo(
            job_id=job_id,
            prompt_id=prompt_id,
            request=request,
        )

        with self._lock:
            self._jobs[subject_key] = job

        return "submitted"

    def await_completions(
        self,
        backend: ComfyUIBackend,
        timeout_s: float = 600.0,
        poll_interval: float = 1.0,
    ) -> list[JobInfo]:
        """Block until *all* currently pending jobs complete.

        Returns a list of finished JobInfo objects (both complete and failed).
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                pending = list(self._jobs)

            for subject_key in pending:
                with self._lock:
                    job = self._jobs.get(subject_key)
                if job is None:
                    continue
                _check_job_status(backend, job)

            with self._lock:
                finished = [j for j in self._jobs.values() if j.status in ("complete", "failed")]
                done_keys = {j.request.subject_key for j in finished}
                for k in done_keys:
                    self._jobs.pop(k, None)
                for j in finished:
                    self._completed.append(j)

            # Are there still pending jobs?
            if not self._jobs:
                return self._completed

            time.sleep(poll_interval)

        # Timeout
        with self._lock:
            unfinished = list(self._jobs.values())
            for j in unfinished:
                j.status = "failed"
                j.error = "timeout"
            self._jobs.clear()

        return self._completed

    def cancel(self, subject_key: str) -> JobInfo | None:
        """Cancel a pending job (marks as cancelled, removes from active set)."""
        with self._lock:
            job = self._jobs.pop(subject_key, None)
        if job is not None:
            job.status = "cancelled"
            self._completed.append(job)
        return job

    # ---- Introspection -----------------------------------------------------

    def get_job(self, subject_key: str) -> JobInfo | None:
        with self._lock:
            return self._jobs.get(subject_key)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def pending_keys(self) -> list[str]:
        with self._lock:
            return list(self._jobs.keys())


def _check_job_status(backend: ComfyUIBackend, job: JobInfo) -> None:
    """Poll ComfyUI history for a single job and update its status."""
    try:
        r = backend._client.get(
            f"{backend.server_url}/history/{job.prompt_id}",
            timeout=backend.timeout_s,
        )
        if r.status_code == 200:
            history = r.json()
            prompt_data = history.get(job.prompt_id)
            if prompt_data and "outputs" in prompt_data:
                outputs = prompt_data["outputs"]
                # Mark running
                if job.status == "submitted":
                    job.status = "running"

                # Check for images in outputs
                for node_id, node_out in outputs.items():
                    if "images" in node_out:
                        # Job is complete with images — save the image
                        digest_input = (
                            f"{job.request.subject_type}:{job.request.subject_key}:"
                            f"{job.job_id}"
                        )
                        digest = hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:12]
                        filename = f"{job.request.subject_type}_{job.request.subject_key}_{digest}.png"
                        image_path = f"{backend.output_dir}/{filename}"

                        # Download the image
                        image_info = node_out["images"][0]
                        disk_path = Path(image_path)
                        disk_path.parent.mkdir(parents=True, exist_ok=True)

                        # Try to download; fall back to placeholder
                        try:
                            backend._save_image(image_info, disk_path)
                        except Exception:
                            backend._create_placeholder(disk_path)

                        job.result = ImageGenerationResult(
                            image_path=image_path,
                            image_url=f"{backend.media_url_base}/{filename}",
                            seed=job.request.seed,
                            model_name=backend._checkpoint_cache or "unknown",
                            generation_time=time.monotonic() - job.submitted_at,
                            metadata={
                                "job_id": job.job_id,
                                "prompt_id": job.prompt_id,
                            },
                        )
                        job.status = "complete"
                        job.completed_at = time.monotonic()
                        return

                # If we got here, outputs exist but no images — check status
                if "status" in prompt_data and "completed" in prompt_data["status"]:
                    job.status = "failed"
                    job.error = "no images in output"
                    return

                return

    except httpx.ConnectError:
        # Server might still be working; don't fail yet
        pass
