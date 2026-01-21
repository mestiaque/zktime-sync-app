from zk import ZK
import requests
from datetime import datetime
import time

def fetch_logs_and_sync(api_url, devices, log_fn):
    """
    Fetch attendance logs from ZKTeco devices and sync to API.

    Args:
        api_url (str): API endpoint URL
        devices (list): List of dicts: {"ip": str, "port": int, "password": int}
        log_fn (callable): Function to log messages (thread-safe for UI)
    """

    def log(text):
        # Wrap log function
        log_fn(text)

    log("🔄 Starting sync with devices...")

    for dev in devices:
        ip = dev.get("ip")
        pwd = dev.get("password", 0)
        port = dev.get("port", 4370)

        conn = None
        try:
            log(f"🔌 Connecting to {ip}:{port}")
            zk = ZK(ip, port=port, timeout=5, password=pwd)
            conn = zk.connect()
            conn.disable_device()

            sn = conn.get_serialnumber()
            log(f"📟 Device SN: {sn}")

            logs = conn.get_attendance()
            log(f"✔ {len(logs)} log(s) fetched from {ip}")

            for l in logs:
                payload = {
                    "user_id": l.user_id,
                    "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": l.status,
                    "device": ip,
                    "device_sn": sn
                }

                try:
                    r = requests.post(api_url, json=payload, timeout=10)
                    if r.status_code == 200:
                        log(f"✅ Synced → User {l.user_id}")
                    else:
                        log(f"❌ API Error {r.status_code} for User {l.user_id}")
                except Exception as e:
                    log(f"❌ API Failed for User {l.user_id}: {e}")

        except Exception as e:
            log(f"❌ Connection/Fetch failed for {ip}: {e}")

        finally:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                    log(f"🔌 Disconnected {ip}")
                except:
                    pass

    log("🎉 Sync complete!")
