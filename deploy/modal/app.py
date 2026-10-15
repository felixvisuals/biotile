"""BIOTILE backend on Modal (free Starter plan: $30 compute credits / month, scales to zero).

Netlify serves the frontend and proxies /api/* to the URL printed by `modal deploy`.
SQLite and stored files live on a Modal Volume. One container serves every request, so SQLite
never sees two writers; it stays warm for 20 minutes after the last request so background jobs
(a Tripo generation takes ~6 min) can finish.

    modal deploy deploy/modal/app.py              # build + publish
    modal run deploy/modal/app.py::seed           # once: jury invite, demo patterns, map tiles
Secrets come from the Modal secret "biotile" (TRIPO_API_KEY, SECRET_KEY), never from the repo.
"""
from pathlib import Path

import modal

# The image is built from the local checkout; inside the container this module lives at /root.
ROOT = Path(__file__).resolve().parents[2] if modal.is_local() else Path("/app")
FRONTEND = "https://biotile-tripothon.netlify.app"
SKIP = ["**/__pycache__/**", "**/*.pyc"]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install_from_requirements(str(ROOT / "deploy/modal/requirements.txt"))
    .env({
        "PYTHONPATH": "/app/packages:/app/services/api:/app/services/worker",
        "DATABASE_URL": "sqlite:////vol/biotile.db",
        "STORAGE_DIR": "/vol/storage",
        "TRIPO_MODE": "live",
        "TRIPO_RECORD": "false",
        "COOKIE_SECURE": "true",
        "PUBLIC_BASE_URL": FRONTEND,
    })
    .add_local_dir(ROOT / "packages", "/app/packages", ignore=SKIP)
    .add_local_dir(ROOT / "services", "/app/services", ignore=SKIP)
    .add_local_dir(ROOT / "scripts", "/app/scripts", ignore=SKIP)
    .add_local_dir(ROOT / "data", "/app/data", ignore=SKIP)
    .add_local_dir(ROOT / "tests/fixtures", "/app/tests/fixtures", ignore=SKIP + ["recorded/**"])
)

app = modal.App("biotile")
volume = modal.Volume.from_name("biotile-data", create_if_missing=True)
secrets = [modal.Secret.from_name("biotile")]
# 1 core; memory request 1 GiB, limit 8 GiB (an export peaks at ~2.3 GB; two jobs and a preview
# can overlap). Only memory actually used is billed above the request.
RES = dict(image=image, volumes={"/vol": volume}, secrets=secrets, cpu=1.0, memory=(1024, 8192))


@app.function(**RES, max_containers=1, scaledown_window=1200, timeout=1800)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def api():
    from biotile_api.main import app as fastapi_app

    return fastapi_app


@app.function(**RES, timeout=1800)
def seed():
    import os
    import subprocess

    os.chdir("/app")
    env = {**os.environ, "TRIPO_MODE": "mock"}
    for cmd in (["python", "-c", "from biotile_api.models import init_db; init_db()"],
                ["python", "scripts/invites.py", "create", "--code", "1852", "--uses", "500",
                 "--days", "60", "--note", "jury"],
                ["python", "scripts/seed_demo.py"],
                ["python", "scripts/seed_barcelona.py"]):
        subprocess.run(cmd, check=True, env=env)
    volume.commit()


@app.function(**RES, timeout=600)
def sites():
    """Add or update the Barcelona example locations and their photos (idempotent).
    Stop the running api container first, so it does not commit an older database over this."""
    import os
    import subprocess

    os.chdir("/app")
    subprocess.run(["python", "scripts/seed_barcelona.py"], check=True)
    volume.commit()


@app.function(**RES, timeout=300)
def invite(note: str, limit: int = 0, uses: int = 1, days: int = 60):
    """Create one invite code on the hosted database; limit > 0 gives accounts created with it
    their own live generation limit. Stop the running api container first (see sites())."""
    import os
    import subprocess

    os.chdir("/app")
    cmd = ["python", "scripts/invites.py", "create", "--note", note, "--uses", str(uses), "--days", str(days)]
    if limit:
        cmd += ["--limit", str(limit)]
    subprocess.run(cmd, check=True)
    volume.commit()
