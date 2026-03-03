from zk import ZK
import requests
from datetime import datetime, date
import time
from sync_dup import SyncDUP

# ZKTeco Verify Type Mapping
verifyTypes = {
    '0': 'Password/Other',
    '1': 'Fingerprint',
    '2': 'Card',
    '3': 'Password',
    '15': 'Face',
    '25': 'Palm'
}

dup = SyncDUP()

def fetch_logs_and_sync(api_url, devices, log_fn, start_date=None, end_date=None):

    def log(text):
        log_fn(text)

    log("🔄 Starting sync with devices...")

    # Parse selected date range or use today
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            log(f"📅 Filtering logs for date range: {start_dt} to {end_dt}")
        except ValueError:
            log(f"❌ Invalid date format, using today")
            today = date.today()
            start_dt = today
            end_dt = today
    else:
        today = date.today()
        start_dt = today
        end_dt = today
        log(f"📅 Filtering logs for date: {today}")

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

            # Get last sync time for this device
            last_sync = dup.get_last_sync(sn)
            # Only use last_sync if it's from the same date range
            if last_sync and isinstance(last_sync, datetime):
                if last_sync.date() < start_dt or last_sync.date() > end_dt:
                    last_sync = None  # Different date range, reset

            if last_sync:
                log(f"🧠 Last sync time: {last_sync}")

            logs = conn.get_attendance()
            log(f"✔ {len(logs)} log(s) fetched from {ip}")

            max_synced_time = last_sync
            sent_count = 0

            for l in logs:
                # Filter by date range
                log_date = l.timestamp.date()
                if log_date < start_dt or log_date > end_dt:
                    continue

                # ⛔ Skip logs already synced
                if last_sync and l.timestamp <= last_sync:
                    continue

                payload = {
                    "user_id": l.user_id,
                    "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": l.status,
                    "type_code": str(l.verify_type) if hasattr(l, 'verify_type') else '0',
                    "type_name": verifyTypes.get(str(l.verify_type), 'Unknown') if hasattr(l, 'verify_type') else 'Other',
                    "device": ip,
                    "device_sn": sn
                }

                try:
                    r = requests.post(api_url, json=payload, timeout=10)

                    if r.status_code == 200:
                        log(f"✅ Synced → User {l.user_id} at {l.timestamp.strftime('%H:%M:%S')}")
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
                except Exception as e:
                    log(f"⚠️ Failed to enable/disconnect: {e}")

    log("🎉 Sync complete!")
