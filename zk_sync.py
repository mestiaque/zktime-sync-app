from zk import ZK
import requests
from datetime import datetime

def fetch_logs_and_sync(api_url, devices, log_fn):
    def log(text):
        log_fn(text)

    log("Connecting to devices...")

    for dev in devices:
        ip = dev["ip"]
        pwd = dev["password"]

        try:
            log(f"🔌 Connecting: {ip}")
            zk = ZK(ip, port=4370, timeout=5, password=pwd)
            conn = zk.connect()
            conn.disable_device()
        except Exception as e:
            log(f"❌ Failed: {ip} — {e}")
            continue

        try:
            logs = conn.get_attendance()
            log(f"✔ Logs: {len(logs)}")
        except:
            log(f"❌ Could not read logs from {ip}")
            continue

        for l in logs:
            payload = {
                "user_id": l.user_id,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "status": l.status,
                "device": ip
            }

            try:
                r = requests.post(api_url, json=payload)
                if r.status_code == 200:
                    log(f"Synced → User {l.user_id}")
                else:
                    log(f"API Error {r.status_code}")
            except Exception as e:
                log(f"API Failed: {e}")

        conn.enable_device()
        conn.disconnect()

    log("🎉 Sync Complete!")
