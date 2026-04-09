from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings


settings = get_settings()
BACKEND_ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = BACKEND_ROOT_DIR / "scripts" / "run_style_ingestion.py"
ADMIN_DIR = settings.media_root / "style_ingestion_admin"
LOG_PATH = ADMIN_DIR / "style_ingestion_worker.log"
PID_PATH = ADMIN_DIR / "style_ingestion_worker.pid"


@dataclass(frozen=True)
class ParserProcessSnapshot:
    state: str
    pid: int | None
    started_at: datetime | None
    stop_requested_at: datetime | None
    last_exit_code: int | None
    last_error: str | None
    command: str | None
    log_path: str
    pid_file_path: str


class StyleIngestionAdminService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._started_at: datetime | None = None
        self._stop_requested_at: datetime | None = None
        self._last_exit_code: int | None = None
        self._last_error: str | None = None
        self._command: str | None = None

    def build_commands(
        self,
        *,
        source_name: str,
        limit: int,
        worker_max_jobs: int,
        title_contains: str | None = None,
    ) -> dict[str, str]:
        effective_worker_max_jobs = max(worker_max_jobs, (max(limit, 1) * 2) + 1)
        title_filter = f" --title-contains {shlex.quote(title_contains)}" if title_contains else ""
        enqueue_command = (
            "docker compose exec backend sh -lc "
            f"\"cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode enqueue-jobs --source-name "
            f"{source_name} --limit {limit}{title_filter}\""
        )
        worker_command = (
            "docker compose exec backend sh -lc "
            f"\"cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-worker --source-name "
            f"{source_name} --worker-max-jobs {effective_worker_max_jobs} --worker-stop-when-idle\""
        )
        combined_command = (
            "nohup bash -lc "
            + shlex.quote(f"{enqueue_command} && {worker_command}")
            + " > ~/style_ingestion_api_worker.log 2>&1 &"
        )
        stop_command = (
            "docker compose exec backend sh -lc "
            f"\"if [ -f {PID_PATH} ]; then kill -TERM -- -$(cat {PID_PATH}); fi\""
        )
        return {
            "enqueue_command": enqueue_command,
            "worker_command": worker_command,
            "combined_command": combined_command,
            "stop_command": stop_command,
        }

    def start(
        self,
        *,
        source_name: str,
        limit: int,
        worker_max_jobs: int,
        title_contains: str | None = None,
    ) -> ParserProcessSnapshot:
        with self._lock:
            self._refresh_locked()
            if self._process is not None:
                raise RuntimeError("Style ingestion worker is already running")

            ADMIN_DIR.mkdir(parents=True, exist_ok=True)
            commands = self.build_commands(
                source_name=source_name,
                limit=limit,
                worker_max_jobs=worker_max_jobs,
                title_contains=title_contains,
            )
            shell_command = (
                f"cd {shlex.quote(str(BACKEND_ROOT_DIR))} && "
                f"{shlex.quote(sys.executable)} {shlex.quote(str(SCRIPT_PATH))} --mode enqueue-jobs "
                f"--source-name {shlex.quote(source_name)} --limit {limit}"
            )
            if title_contains:
                shell_command += f" --title-contains {shlex.quote(title_contains)}"
            shell_command += (
                f" && {shlex.quote(sys.executable)} {shlex.quote(str(SCRIPT_PATH))} --mode run-worker "
                f"--source-name {shlex.quote(source_name)} --worker-max-jobs "
                f"{max(worker_max_jobs, (max(limit, 1) * 2) + 1)} --worker-stop-when-idle"
            )

            with LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.now(UTC).isoformat()}] starting style ingestion admin worker\n")
                handle.write(f"[command] {commands['combined_command']}\n")

            stdout_handle = LOG_PATH.open("a", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    ["sh", "-lc", shell_command],
                    cwd=BACKEND_ROOT_DIR,
                    stdout=stdout_handle,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    start_new_session=True,
                )
            except Exception as exc:
                stdout_handle.close()
                self._last_error = str(exc)
                raise
            stdout_handle.close()

            self._process = process
            self._started_at = datetime.now(UTC)
            self._stop_requested_at = None
            self._last_exit_code = None
            self._last_error = None
            self._command = shell_command
            PID_PATH.write_text(str(process.pid), encoding="utf-8")
            return self._snapshot_locked()

    def stop(self) -> ParserProcessSnapshot:
        with self._lock:
            self._refresh_locked()
            process = self._process
            if process is None:
                return self._snapshot_locked()

            self._stop_requested_at = datetime.now(UTC)
            try:
                self._terminate_process_group(process)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._kill_process_group(process)
                process.wait(timeout=5)
            except Exception as exc:
                self._last_error = str(exc)
            self._refresh_locked()
            return self._snapshot_locked()

    def snapshot(self) -> ParserProcessSnapshot:
        with self._lock:
            self._refresh_locked()
            return self._snapshot_locked()

    def read_log_tail(self, *, lines: int = 40) -> list[str]:
        ADMIN_DIR.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            return []
        raw_lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        return raw_lines[-max(lines, 1) :]

    def shutdown(self) -> None:
        with self._lock:
            if self._process is None:
                return
            try:
                self._terminate_process_group(self._process)
            except Exception:
                pass
            self._refresh_locked()

    def _snapshot_locked(self) -> ParserProcessSnapshot:
        state = "running" if self._process is not None else "idle"
        if self._process is not None and self._stop_requested_at is not None:
            state = "stopping"
        return ParserProcessSnapshot(
            state=state,
            pid=self._process.pid if self._process is not None else None,
            started_at=self._started_at,
            stop_requested_at=self._stop_requested_at,
            last_exit_code=self._last_exit_code,
            last_error=self._last_error,
            command=self._command,
            log_path=str(LOG_PATH),
            pid_file_path=str(PID_PATH),
        )

    def _refresh_locked(self) -> None:
        process = self._process
        if process is None:
            if PID_PATH.exists():
                PID_PATH.unlink(missing_ok=True)
            return

        return_code = process.poll()
        if return_code is None:
            PID_PATH.write_text(str(process.pid), encoding="utf-8")
            return

        self._last_exit_code = return_code
        self._process = None
        self._stop_requested_at = None
        PID_PATH.unlink(missing_ok=True)

    def _terminate_process_group(self, process: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            process.terminate()
            return
        os.killpg(process.pid, signal.SIGTERM)

    def _kill_process_group(self, process: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            process.kill()
            return
        os.killpg(process.pid, signal.SIGKILL)


style_ingestion_admin_service = StyleIngestionAdminService()
