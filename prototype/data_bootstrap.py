"""Ensure the IPEDS SQLite data is present before the app reads it.

Local development (IPEDS_DATA_DIR unset): a no-op — the app uses the repo's own data/ folder.

Server (IPEDS_DATA_DIR set, e.g. a Render persistent disk mounted at /var/data/ipeds): on the
first run the data isn't there yet, so download it once from the public Hugging Face Dataset repo
named by IPEDS_DATASET_REPO (e.g. 'yul13011/ipeds-data'). On every later start the files already
exist, so this returns immediately. No HF token is needed for a public dataset repo.
"""
import os
from pathlib import Path

# File that must exist for the dataset to count as fully present (the always-needed catalog DB).
_MARKER = "metadata_catalog.sqlite"


def ensure_data():
    data_dir = os.environ.get("IPEDS_DATA_DIR")
    if not data_dir:
        return  # local dev: use the repo's bundled data/ folder
    target = Path(data_dir)
    if (target / _MARKER).exists():
        return  # already synced (persistent disk) — fast no-op
    repo = os.environ.get("IPEDS_DATASET_REPO")
    if not repo:
        raise RuntimeError(
            "IPEDS_DATA_DIR is set but IPEDS_DATASET_REPO is not; cannot fetch the data."
        )
    from huggingface_hub import snapshot_download

    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo, repo_type="dataset", local_dir=str(target))
