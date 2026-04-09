from datetime import datetime

from pydantic import BaseModel, Field


class ParserAdminStartRequest(BaseModel):
    source_name: str = "aesthetics_wiki"
    limit: int = Field(default=50, ge=1, le=500)
    worker_max_jobs: int = Field(default=50, ge=1, le=1000)
    title_contains: str | None = None


class ParserAdminProcessRead(BaseModel):
    state: str
    pid: int | None = None
    started_at: datetime | None = None
    stop_requested_at: datetime | None = None
    last_exit_code: int | None = None
    last_error: str | None = None
    command: str | None = None
    log_path: str
    pid_file_path: str


class ParserAdminCommandsRead(BaseModel):
    enqueue_command: str
    worker_command: str
    combined_command: str
    stop_command: str


class ParserAdminStatsRead(BaseModel):
    styles_total: int
    source_pages_total: int
    source_page_versions_total: int
    style_profiles_total: int
    style_traits_total: int
    taxonomy_links_total: int
    relations_total: int
    jobs_total: int
    jobs_queued: int
    jobs_running: int
    jobs_succeeded: int
    jobs_soft_failed: int
    jobs_hard_failed: int
    jobs_cooldown_deferred: int
    runs_total: int
    runs_completed: int
    runs_failed: int
    runs_completed_with_failures: int
    runs_aborted: int


class ParserAdminRecentRunRead(BaseModel):
    run_id: int
    source_name: str
    source_url: str | None = None
    run_status: str
    styles_seen: int
    styles_created: int
    styles_updated: int
    styles_failed: int
    started_at: datetime
    finished_at: datetime | None = None


class ParserAdminOverviewRead(BaseModel):
    process: ParserAdminProcessRead
    commands: ParserAdminCommandsRead
    stats: ParserAdminStatsRead
    recent_runs: list[ParserAdminRecentRunRead]
    log_tail: list[str]
