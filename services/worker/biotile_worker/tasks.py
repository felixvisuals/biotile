"""Worker entry points (RQ resolves these by dotted path; inline mode calls them directly)."""

from biotile_api.design_service import run_export, run_generate


def generate(job_id: str) -> None:
    run_generate(job_id)


def export(job_id: str) -> None:
    run_export(job_id)
