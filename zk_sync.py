from zk import ZK
import requests
from datetime import datetime, date
import time
from sync_dup import SyncDUP

dup = SyncDUP()

def fetch_logs_and_sync(api_url, devices, log_fn):

    def log(text):
        log_fn(text)

    log("🔄 Starting sync with devices...")

    today = date.today()  # আজকের তারিখ

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

            # আগের আজকের সিঙ্ক সময়
            last_sync = dup.get_last_sync(sn)
            if last_sync and last_sync.date() != today:
                last_sync = None  # আগের দিনের last_sync আজকের জন্য বাদ

            if last_sync:
                log(f"🧠 Last sync time today: {last_sync}")

            logs = conn.get_attendance()
            log(f"✔ {len(logs)} log(s) fetched from {ip}")

            max_synced_time = last_sync
            sent_count = 0

            for l in logs:
                # ⛔ Skip logs not from today
                if l.timestamp.date() != today:
                    continue

                # ⛔ Skip logs already synced today
                if last_sync and l.timestamp <= last_sync:
                    continue

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
                        sent_count += 1

                        if not max_synced_time or l.timestamp > max_synced_time:
                            max_synced_time = l.timestamp

                    elif r.status_code == 429:
                        log("⏳ Rate limit hit, waiting 2s...")
                        time.sleep(2)
                        continue

                    else:
                        log(f"❌ API Error {r.status_code}: {r.text}")

                except Exception as e:
                    log(f"❌ API Failed: {e}")

                time.sleep(0.4)  # 🔹 delay to avoid 429

            # 💾 Save last sync ONLY if something sent
            if sent_count > 0 and max_synced_time:
                dup.save_last_sync(sn, max_synced_time)
                log(f"💾 Last sync updated → {max_synced_time}")

            log(f"📊 Sent {sent_count} new log(s) from {ip}")

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
