# sync_dup.py
import json
from datetime import datetime, date
import os

class SyncDUP:
    def __init__(self, filename="last_sync.json"):
        self.filename = filename
        # ফাইল থাকলে load করো, না থাকলে empty dict
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self.data = json.load(f)
            except:
                self.data = {}
        else:
            self.data = {}

    def get_last_sync(self, sn):
        """
        sn = device serial number
        return datetime object বা None
        """
        ts = self.data.get(str(sn))
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except:
                return None
        return None

    def save_last_sync(self, sn, dt: datetime):
        """
        sn = device serial number
        dt = datetime object
        """
        self.data[str(sn)] = dt.isoformat()
        # ফাইল update করো
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)
        print(f"💾 Last sync saved for {sn}: {dt}")
