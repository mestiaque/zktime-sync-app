from zk import ZK
import requests
from datetime import datetime, date, timedelta
import time
from sync_dup import SyncDUP

# ZKTeco Verify Type Mapping (pyzk puts the verify mode in Attendance.status)
verifyTypes = {
    '0': 'Password/Other',
    '1': 'Fingerprint',
    '2': 'Card',
    '3': 'Password',
    '15': 'Face',
    '25': 'Palm'
}

REQUEST_DELAY = 0.4   # 🔹 delay between requests to avoid 429
MAX_RETRIES = 3

dup = SyncDUP()


def _parse_date(value, fallback):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def _post_with_retry(session, api_url, payload, log):
    """POST one record. Retries on 429 / 5xx / network errors so records are not silently dropped."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(api_url, json=payload, timeout=15)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                log(f"API Failed: {e}")
                return False
            time.sleep(attempt)
            continue

        if r.ok:
            return True

        if r.status_code == 429 or r.status_code >= 500:
            if attempt == MAX_RETRIES:
                log(f"API Error {r.status_code} (gave up after {MAX_RETRIES} tries)")
                return False
            wait = 2 * attempt
            log(f"API {r.status_code}, retrying in {wait}s...")
            time.sleep(wait)
            continue

        # 4xx (validation etc.) - retrying will not help
        log(f"API Error {r.status_code}: {r.text[:200]}")
        return False
    return False


def friendly_error(e):
    """Short, human readable reason for a failed device connection"""
    text = str(e)
    lower = text.lower()
    if "unauth" in lower:
        return "Wrong Comm Key (password)"
    if "timed out" in lower or "timeout" in lower:
        return "No response - check IP, power and network"
    if "refused" in lower:
        return "Connection refused - check port / firewall"
    if "unreachable" in lower or "no route" in lower or "can't reach" in lower:
        return "Network unreachable - device not on this network"
    if "getaddrinfo" in lower or "name or service" in lower:
        return "Invalid IP address"
    return text or e.__class__.__name__


def check_device(ip, port=4370, password=0, timeout=5):
    """
    Quick connection test: connect, read SN + device clock, disconnect.
    Does not disable the device or touch attendance logs.
    """
    conn = None
    try:
        # ommit_ping: pyzk's ping runs a console command (flashes a window in the .exe)
        zk = ZK(ip, port=port, timeout=timeout, password=password, ommit_ping=True)
        conn = zk.connect()
        sn = conn.get_serialnumber()
        try:
            device_time = conn.get_time()
        except Exception:
            device_time = None
        return {"ok": True, "sn": sn, "time": device_time, "error": ""}
    except Exception as e:
        return {"ok": False, "sn": None, "time": None, "error": friendly_error(e)}
    finally:
        if conn:
            try:
                conn.disconnect()
            except Exception:
                pass


def _fetch_device_logs(ip, port, pwd, log):
    """Connect, read SN + attendance, and release the device immediately."""
    conn = None
    try:
        log(f"[CONNECT] {ip}:{port}")
        zk = ZK(ip, port=port, timeout=10, password=pwd)
        conn = zk.connect()
        conn.disable_device()
        sn = conn.get_serialnumber()
        log(f"[DEVICE] SN={sn}")
        logs = conn.get_attendance() or []
        log(f"[FETCH] {len(logs)} log(s) fetched from {ip}")
        return sn, logs
    finally:
        # Device is locked only while reading, not while pushing to the API
        if conn:
            try:
                conn.enable_device()
                conn.disconnect()
                log(f"[DISCONNECT] {ip}")
            except Exception as e:
                log(f"[DISCONNECT] Failed to enable/disconnect {ip}: {e}")


def fetch_logs_and_sync(api_url, devices, log_fn, start_date=None, end_date=None, incremental=False):
    """
    Sync attendance logs from devices to the API.

    Manual mode: sends every log between start_date and end_date (inclusive).
    Incremental mode (auto sync): sends only logs newer than the last successfully
    synced log of each device, so missed days are caught up and nothing is resent.

    Returns {device_ip: serial_number} for devices that connected.
    """

    def log(text):
        log_fn(f"--> [{datetime.now().strftime('%H:%M:%S')}] {text}")

    today = date.today()
    end_dt = _parse_date(end_date, today)
    start_dt = _parse_date(start_date, end_dt - timedelta(days=6))
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    if incremental:
        log("[SYNC] Starting auto sync (new logs only)")
    else:
        log(f"[SYNC] Starting sync for {start_dt} -> {end_dt}")

    serials = {}
    session = requests.Session()
    total_sent = total_failed = 0

    for dev in devices:
        ip = dev.get("ip")
        pwd = dev.get("password", 0)
        port = dev.get("port", 4370)

        try:
            sn, logs = _fetch_device_logs(ip, port, pwd, log)
        except Exception as e:
            log(f"[ERROR] Connection/Fetch failed for {ip}: {friendly_error(e)} ({e})")
            continue

        serials[ip] = sn

        last_sync = dup.get_last_sync(sn) if incremental else None
        if incremental:
            if last_sync:
                log(f"[FILTER] Logs after {last_sync}")
            else:
                log(f"[FILTER] First auto sync for this device, sending today's logs")

        selected = []
        for l in logs:
            ts = l.timestamp
            if incremental:
                if last_sync:
                    if ts <= last_sync:
                        continue
                elif ts.date() != today:
                    continue
            elif ts.date() < start_dt or ts.date() > end_dt:
                continue
            selected.append(l)

        selected.sort(key=lambda l: l.timestamp)
        log(f"[FILTER] {len(selected)} log(s) to send from {ip}")

        sent = failed = 0
        watermark = last_sync
        contiguous = True  # only advance last_sync while there is no gap of failed records

        for l in selected:
            status = str(l.status)
            payload = {
                "user_id": l.user_id,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "status": l.status,
                "punch": getattr(l, "punch", 0),
                "type_code": status,
                "type_name": verifyTypes.get(status, 'Unknown'),
                "device": ip,
                "device_sn": sn
            }

            if _post_with_retry(session, api_url, payload, log):
                sent += 1
                if contiguous:
                    watermark = l.timestamp
            else:
                failed += 1
                contiguous = False
                log(f"[FAILED] User {l.user_id} at {payload['timestamp']}")

            time.sleep(REQUEST_DELAY)

        if incremental and watermark and watermark != last_sync:
            dup.save_last_sync(sn, watermark)
            log(f"[SAVE] Last sync -> {watermark}")

        log(f"[RESULT] {ip}: sent {sent}, failed {failed}")
        total_sent += sent
        total_failed += failed

    session.close()
    log(f"[SYNC] Complete! Sent {total_sent}, failed {total_failed}")
    return serials
