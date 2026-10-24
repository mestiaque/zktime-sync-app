# sync_dup.py
import json
from datetime import datetime
import os
import sys
import threading


def get_data_dir():
    """Persistent, user-writable folder (NOT the PyInstaller temp folder)."""
    if os.name == "nt":
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ZKTimeSync")
    elif getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return base


class SyncDUP:
    """Remembers the newest successfully synced log time per device SN."""

    def __init__(self, filename="last_sync.json"):
        self.filename = os.path.join(get_data_dir(), filename)
        self.lock = threading.Lock()  # 🔐 Thread safety

        # 📥 Load existing data
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}

    def get_last_sync(self, sn):
        with self.lock:
            ts = self.data.get(str(sn))
            if ts:
                try:
                    return datetime.fromisoformat(ts)
                except ValueError:
                    return None
            return None

    def save_last_sync(self, sn, dt: datetime):
        with self.lock:
            self.data[str(sn)] = dt.isoformat()
            tmp = self.filename + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            os.replace(tmp, self.filename)
