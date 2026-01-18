from zk import ZK
import requests
import json
from datetime import datetime

def log(text, box):
    box.insert("end", text + "\n")
    box.see("end")

def fetch_logs_and_sync(api_url, devices, log_box):
    log("Connecting to devices...", log_box)

    for dev in devices:
        ip = dev["ip"]
        pwd = dev["password"]

        try:
            log(f"🔌 Connecting: {ip}", log_box)
            zk = ZK(ip, port=4370, timeout=5, password=pwd)
            conn = zk.connect()
            conn.disable_device()
        except Exception as e:
            log(f"❌ Failed: {ip} — {e}", log_box)
            continue

        try:
            logs = conn.get_attendance()
            log(f"✔ Logs: {len(logs)}", log_box)
        except:
            log(f"❌ Could not read logs from {ip}", log_box)
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
                    log(f"Synced → User {l.user_id}", log_box)
                else:
                    log(f"API Error {r.status_code}", log_box)
            except Exception as e:
                log(f"API Failed: {e}", log_box)

        conn.enable_device()
        conn.disconnect()

    log("🎉 Sync Complete!", log_box)

