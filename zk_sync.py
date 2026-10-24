from zk import ZK, const
from zk.exception import ZKErrorResponse
from struct import pack, unpack
from types import MethodType
import requests
from datetime import datetime, date, timedelta
import time
import json
import os
from sync_dup import SyncDUP, get_data_dir

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


FETCH_TIMEOUT = 20      # seconds per network read while downloading logs
CHECK_TIMEOUT = 5
RETRY_WAIT = 10         # let the device settle after a failed session

# Ways to download logs, tried in order until one works. pyzk's default is
# ~64 KB TCP chunks, which many firmwares stall on; smaller chunks use the same protocol.
STRATEGIES = [
    ("TCP", 16 * 1024),
    ("TCP", 4 * 1024),
    ("TCP", 1024),
    ("UDP", None),
]
PREFS_FILE = "device_prefs.json"


def _strategy_name(strategy):
    proto, chunk = strategy
    return proto if chunk is None else f"{proto} {chunk // 1024} KB"


def _load_prefs():
    try:
        with open(os.path.join(get_data_dir(), PREFS_FILE), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_pref(ip, index):
    prefs = _load_prefs()
    if prefs.get(ip) == index:
        return
    prefs[ip] = index
    try:
        path = os.path.join(get_data_dir(), PREFS_FILE)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4)
        os.replace(path + ".tmp", path)
    except Exception:
        pass


def _strategy_order(ip):
    """Remembered working strategy first, then the rest in default order"""
    pref = _load_prefs().get(ip)
    order = list(range(len(STRATEGIES)))
    if isinstance(pref, int) and 0 <= pref < len(STRATEGIES):
        order.remove(pref)
        order.insert(0, pref)
    return order


def _force_close(conn):
    """Drop the socket so the device frees its session even if CMD_EXIT failed"""
    try:
        conn._ZK__sock.close()
    except Exception:
        pass


def _protocols(ip):
    """force_udp flags to try for a quick check, remembered protocol first"""
    first = STRATEGIES[_strategy_order(ip)[0]][0]
    return [True, False] if first == "UDP" else [False, True]


def check_device(ip, port=4370, password=0, timeout=CHECK_TIMEOUT):
    """
    Quick connection test: connect, read SN + device clock, disconnect.
    Does not disable the device or touch attendance logs. Tries TCP, then UDP.
    """
    error = None
    for udp in _protocols(ip):
        conn = None
        try:
            # ommit_ping: pyzk's ping runs a console command (flashes a window in the .exe)
            zk = ZK(ip, port=port, timeout=timeout, password=password, force_udp=udp, ommit_ping=True)
            conn = zk.connect()
            sn = conn.get_serialnumber()
            try:
                device_time = conn.get_time()
            except Exception:
                device_time = None
            return {"ok": True, "sn": sn, "time": device_time, "error": "", "udp": udp}
        except Exception as e:
            error = e
            if "unauth" in str(e).lower():
                break   # wrong comm key - the other protocol will not help
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                _force_close(conn)
    return {"ok": False, "sn": None, "time": None, "error": friendly_error(error), "udp": None}


def _use_small_chunks(conn, chunk, progress=None):
    """
    Replace pyzk's read_with_buffer on this connection with one that reads in
    smaller chunks over TCP and reports progress. Same protocol, smaller pieces.
    """
    if not getattr(conn, "tcp", False) or not hasattr(conn, "_ZK__read_chunk"):
        return

    def read_with_buffer(self, command, fct=0, ext=0):
        command_string = pack('<bhii', 1, command, fct, ext)
        cmd_response = self._ZK__send_command(1503, command_string, 1024)
        if not cmd_response.get('status'):
            raise ZKErrorResponse("RWB Not supported")
        if cmd_response['code'] == const.CMD_DATA:
            # small payload came back in one piece
            data = self._ZK__data
            need = (self._ZK__tcp_length - 8) - len(data)
            if need > 0:
                more = self._ZK__recieve_raw_data(need)
                return b''.join([data, more]), len(data) + len(more)
            return data, len(data)

        size = unpack('I', self._ZK__data[1:5])[0]
        parts, start = [], 0
        while start < size:
            n = min(chunk, size - start)
            parts.append(self._ZK__read_chunk(start, n))
            start += n
            if progress:
                progress(command, start, size)
        self.free_data()
        return b''.join(parts), start

    conn.read_with_buffer = MethodType(read_with_buffer, conn)


class FetchError(Exception):
    def __init__(self, step, error):
        super().__init__(f"{step}: {error}")
        self.step, self.error = step, error


def _release_device(conn, locked, ip, port, pwd, udp, log):
    """Unlock + disconnect. If that fails, reconnect once just to unlock the device."""
    try:
        if locked:
            conn.enable_device()
        conn.disconnect()
        log(f"[DISCONNECT] {ip}")
        return
    except Exception as e:
        log(f"[DISCONNECT] {ip}: {e}")
    finally:
        _force_close(conn)

    if not locked:
        return
    time.sleep(2)
    rconn = None
    try:
        rconn = ZK(ip, port=port, timeout=10, password=pwd, force_udp=udp, ommit_ping=True).connect()
        rconn.enable_device()
        log(f"[RECOVER] Device {ip} unlocked again")
    except Exception as e:
        log(f"[ERROR] Could not unlock {ip} ({friendly_error(e)}). "
            f"If the device screen is stuck on 'Working', restart the device.")
    finally:
        if rconn:
            try:
                rconn.disconnect()
            except Exception:
                pass
            _force_close(rconn)


def _fetch_once(ip, port, pwd, strategy, log):
    udp = strategy[0] == "UDP"
    conn, locked, step = None, False, "connect"
    try:
        log(f"[CONNECT] {ip}:{port} ({_strategy_name(strategy)})")
        zk = ZK(ip, port=port, timeout=FETCH_TIMEOUT, password=pwd, force_udp=udp, ommit_ping=True)
        conn = zk.connect()

        step = "read serial number"
        sn = conn.get_serialnumber()

        step = "read record count"
        conn.read_sizes()
        log(f"[DEVICE] SN={sn} · {conn.users} user(s), {conn.records} log(s) on device")

        step = "lock device"
        conn.disable_device()
        locked = True

        last_pct = [-1]

        def progress(command, done, total):
            if command != const.CMD_ATTLOG_RRQ:
                return
            pct = done * 100 // total
            if pct // 25 != last_pct[0] // 25 or done == total:   # log every ~25%
                last_pct[0] = pct
                log(f"[FETCH] downloading {done // 1024}/{total // 1024} KB ({pct}%)")

        if not udp:
            _use_small_chunks(conn, strategy[1], progress)

        step = "download logs"
        started = time.time()
        logs = conn.get_attendance() or []
        log(f"[FETCH] {len(logs)} log(s) fetched from {ip} in {time.time() - started:.0f}s")
        return sn, logs
    except Exception as e:
        raise FetchError(step, e) from e
    finally:
        # Device is locked only while reading, not while pushing to the API
        if conn:
            _release_device(conn, locked, ip, port, pwd, udp, log)


def _fetch_device_logs(ip, port, pwd, log):
    """
    Read SN + attendance. Tries smaller TCP chunks and then UDP until one works,
    and remembers the working way for this device.
    """
    error, tried, tcp_reachable = None, 0, True
    for index in _strategy_order(ip):
        strategy = STRATEGIES[index]
        if strategy[0] == "TCP" and not tcp_reachable:
            continue   # TCP did not even connect - smaller chunks will not help
        if tried:
            log(f"[RETRY] Trying {ip} again with {_strategy_name(strategy)} in {RETRY_WAIT}s…")
            time.sleep(RETRY_WAIT)
        tried += 1
        try:
            result = _fetch_once(ip, port, pwd, strategy, log)
            _save_pref(ip, index)
            return result
        except FetchError as e:
            error = e
            log(f"[ERROR] {ip}: failed at '{e.step}' - {friendly_error(e.error)}")
            if "unauth" in str(e.error).lower():
                break   # wrong comm key - nothing else will help
            if strategy[0] == "TCP" and e.step == "connect":
                tcp_reachable = False
    raise error


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
    total_sent = total_failed = unreachable = 0

    for dev in devices:
        ip = dev.get("ip")
        pwd = dev.get("password", 0)
        port = dev.get("port", 4370)

        try:
            sn, logs = _fetch_device_logs(ip, port, pwd, log)
        except Exception as e:
            reason = friendly_error(e.error if isinstance(e, FetchError) else e)
            log(f"[ERROR] Connection/Fetch failed for {ip}: {reason}")
            unreachable += 1
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
    summary = f"Sent {total_sent}, failed {total_failed}"
    if unreachable:
        summary += f", {unreachable} device(s) unreachable"
    log(f"[SYNC] Complete! {summary}")
    return serials
