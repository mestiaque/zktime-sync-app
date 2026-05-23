from zk import ZK
import requests
from datetime import datetime, date, timedelta
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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log(f"--> [SYNC:{timestamp}] Starting device sync")

    # Parse selected date range or set minimum 7 days
    today = date.today()
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            log(f"--> [FILTER:{timestamp}] Date range {start_dt} -> {end_dt}")
        except ValueError:
            log(f"--> [FILTER:{timestamp}] Invalid date format, using last 7 days")
            end_dt = today
            start_dt = today - timedelta(days=6)
            log(f"--> [FILTER:{timestamp}] Date range {start_dt} -> {end_dt}")
    else:
        end_dt = today
        start_dt = today - timedelta(days=6)
        log(f"--> [FILTER:{timestamp}] Date range {start_dt} -> {end_dt}")

    for dev in devices:
        ip = dev.get("ip")
        pwd = dev.get("password", 0)
        port = dev.get("port", 4370)

        conn = None
        try:
            log(f"--> [CONNECT:{timestamp}] {ip}:{port}")
            zk = ZK(ip, port=port, timeout=5, password=pwd)
            conn = zk.connect()
            conn.disable_device()

            sn = conn.get_serialnumber()
            log(f"--> [DEVICE:{timestamp}] SN={sn}")
            # last_sync logic disabled as per request
            # last_sync = dup.get_last_sync(sn)
            # if last_sync and isinstance(last_sync, datetime):
            #     if last_sync.date() < start_dt or last_sync.date() > end_dt:
            #         last_sync = None
            # if last_sync:
            #     log(f"🧠 Last sync time: {last_sync}")

            logs = conn.get_attendance()
            log(f"--> [FETCH:{timestamp}] {len(logs)} log(s) fetched from {ip}")

            sent_count = 0

            for l in logs:
                # Filter by date range
                log_date = l.timestamp.date()
                if log_date < start_dt or log_date > end_dt:
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
                        log(f"--> [SYNC:{timestamp}] Synced → User {l.user_id} at {l.timestamp.strftime('%H:%M:%S')}")
                        sent_count += 1

                    elif r.status_code == 429:
                        log(f"--> [SYNC:{timestamp}] Rate limit hit, waiting 2s...")
                        time.sleep(2)
                        continue

                    else:
                        log(f"--> [SYNC:{timestamp}] API Error {r.status_code}: {r.text}")

                except Exception as e:
                    log(f"--> [SYNC:{timestamp}] API Failed: {e}")

                time.sleep(0.4)  # 🔹 delay to avoid 429

            # last_sync save logic disabled
            # if sent_count > 0 and max_synced_time:
            #     dup.save_last_sync(sn, max_synced_time)
            #     log(f"💾 Last sync updated → {max_synced_time}")

            log(f"--> [SYNC:{timestamp}] Sent {sent_count} new log(s) from {ip}")

        except Exception as e:
            log(f"--> [SYNC:{timestamp}] Connection/Fetch failed for {ip}: {e}")

        finally:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                    log(f"--> [DISCONNECT:{timestamp}] Disconnected {ip}")
                except Exception as e:
                    log(f"--> [DISCONNECT:{timestamp}] Failed to enable/disconnect: {e}")

    log(f"--> [SYNC:{timestamp}] Sync complete!")
