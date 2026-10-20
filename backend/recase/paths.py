"""Stable source and shared-data locations, independent of the launch directory."""
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def workspace_path(value):
    """Resolve service configuration paths against the shared workspace root."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
