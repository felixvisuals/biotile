"""Create/update the backend Space on Hugging Face from the committed tree (git archive, so .env
and var/ can never be uploaded). Needs a prior `hf auth login` by the account owner.

    uvx --with huggingface_hub python deploy/hf-space/push.py
Secrets (TRIPO_API_KEY, SECRET_KEY) are added by hand in the Space settings."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

REPO = sys.argv[1] if len(sys.argv) > 1 else "Felixvisuals/biotile"
FRONTEND = "https://biotile-tripothon.netlify.app"
here = Path(__file__).resolve().parent
root = here.parents[1]

with tempfile.TemporaryDirectory() as tmp:
    archive = subprocess.run(["git", "-C", str(root), "archive", "HEAD"], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
    shutil.copy(here / "Dockerfile", Path(tmp) / "Dockerfile")
    shutil.copy(here / "README.md", Path(tmp) / "README.md")
    api = HfApi()
    api.create_repo(REPO, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(folder_path=tmp, repo_id=REPO, repo_type="space",
                      ignore_patterns=["apps/**", "docs/**", ".github/**"],
                      commit_message="Deploy from GitHub main")
    for k, v in {"TRIPO_MODE": "live", "PUBLIC_BASE_URL": FRONTEND}.items():
        api.add_space_variable(REPO, k, v)
print(f"https://huggingface.co/spaces/{REPO}")
