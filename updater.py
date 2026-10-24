# updater.py - checks GitHub Releases and installs a newer ZKTime Sync
import os
import re
import sys
import tempfile
import requests

from version import APP_VERSION

REPO = "mestiaque/zktime-sync-app"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
INSTALLER_NAME = "ZKTimeSyncInstaller.exe"


def parse_version(text):
    """'v5.3.0' -> (5, 3, 0); None if it is not a release version"""
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$", str(text or "").strip())
    if not m:
        return None
    return tuple(int(x or 0) for x in m.groups())


def is_newer(remote, current=APP_VERSION):
    r = parse_version(remote)
    if r is None:
        return False
    c = parse_version(current)
    return c is None or r > c   # "dev" builds always accept a release


def check_latest(timeout=10):
    """
    Returns {"version", "url", "size", "notes"} when a newer release with an
    installer exists, otherwise None. Raises on network errors.
    """
    r = requests.get(LATEST_URL, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
    if r.status_code == 404:
        return None   # no releases yet
    r.raise_for_status()
    data = r.json()
    tag = data.get("tag_name", "")
    if not is_newer(tag):
        return None
    for asset in data.get("assets", []):
        if asset.get("name") == INSTALLER_NAME:
            return {
                "version": tag.lstrip("v"),
                "url": asset["browser_download_url"],
                "size": asset.get("size", 0),
                "notes": data.get("body") or "",
            }
    return None


def download(url, progress=None, timeout=30):
    """Download the installer to a temp file and return its path"""
    path = os.path.join(tempfile.gettempdir(), INSTALLER_NAME)
    tmp = path + ".part"
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            for block in r.iter_content(64 * 1024):
                f.write(block)
                done += len(block)
                if progress:
                    progress(done, total)
    if total and done != total:
        raise IOError(f"Download incomplete ({done}/{total} bytes)")
    os.replace(tmp, path)
    return path


def run_installer(path):
    """
    Start the installer and return immediately. The caller must exit the app so
    the files can be replaced; the installer starts the new version when done.
    """
    if os.name != "nt":
        raise OSError("Updates can only be installed on Windows")
    # ShellExecute (os.startfile) shows the UAC prompt the installer needs
    os.startfile(path, "open", "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS")


def can_self_update():
    return os.name == "nt" and getattr(sys, "frozen", False)
