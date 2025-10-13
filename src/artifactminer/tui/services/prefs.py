# Written by Ahmad, reviewed by GenAI - Preferences persistence service
import json, os
from pathlib import Path

CONFIG_PATH = Path(os.path.expanduser("~/.499/config.json"))

def load_prefs() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}

def save_prefs(prefs: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(prefs, indent=2))

# GenAI: Generated validation logic, reviewed and tested by Ahmad
def validate_path(p: str) -> tuple[bool, str]:
    if not p:
        return False, "Path is empty."
    if not os.path.isabs(p):
        return False, "Use an absolute path."
    if not os.path.isdir(p):
        return False, "Folder does not exist."
    if not os.access(p, os.R_OK):
        return False, "No read permission."
    return True, ""
