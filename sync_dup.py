# sync_dup.py
import json
from datetime import datetime
import os

class SyncDUP:
    def __init__(self, filename="last_sync.json"):

        # 🔒 Always store file beside this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filename = os.path.join(base_dir, filename)

        # 📂 If file doesn't exist, create it safely
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump({}, f)

        # 📥 Load existing data
        try:
            with open(self.filename, "r") as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load sync file: {e}")
            self.data = {}

    def get_last_sync(self, sn):
        ts = self.data.get(str(sn))
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except:
                return None
        return None

    def save_last_sync(self, sn, dt: datetime):
        self.data[str(sn)] = dt.isoformat()

        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)

        print(f"💾 Last sync saved for {sn}: {dt}")
