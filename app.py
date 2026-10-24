import json
import os
import sys
import threading
import copy
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from tkinter import font as tkfont
from zk_sync import fetch_logs_and_sync, check_device
from datetime import datetime, timedelta
from urllib.parse import urlparse
import requests

# Optional calendar widget for date selection
try:
    from tkcalendar import DateEntry
    TKCALENDAR_AVAILABLE = True
except Exception:
    DateEntry = None
    TKCALENDAR_AVAILABLE = False

# ===== DATA STORAGE - Uses Windows Registry (No file permission issues) =====
USE_REGISTRY = os.name == "nt"  # Windows only
REG_KEY_PATH = r"SOFTWARE\ZKTimeSync"

def get_registry_config():
    """Load config from Windows Registry"""
    if not USE_REGISTRY:
        return None
    
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
        try:
            data, _ = winreg.QueryValueEx(key, "Config")
            return json.loads(data)
        except FileNotFoundError:
            return None
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None

def save_registry_config(cfg):
    """Save config to Windows Registry"""
    if not USE_REGISTRY:
        return False
    
    try:
        import winreg
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH)
        try:
            winreg.SetValueEx(key, "Config", 0, winreg.REG_SZ, json.dumps(cfg))
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False

# ===== CONFIG HANDLING =====
def load_config():
    """Load config - tries registry first on Windows, then file fallback"""
    # Try Windows Registry first
    if USE_REGISTRY:
        cfg = get_registry_config()
        if cfg is not None:
            return cfg
    
    # Fallback to file-based config
    config_file = get_config_file_path()
    if not os.path.exists(config_file):
        cfg = {"devices": [], "auto_sync_interval": 0, "api_url": FIXED_API_URL}
        save_config(cfg)
        return cfg
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"devices": [], "auto_sync_interval": 0, "api_url": FIXED_API_URL}

def save_config(cfg):
    """Save config - tries registry first on Windows"""
    # Try Windows Registry first
    if USE_REGISTRY:
        if save_registry_config(cfg):
            return
    
    # Fallback to file
    try:
        config_file = get_config_file_path()
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save config:\n{str(e)}")

def get_config_file_path():
    """Get config file path for fallback"""
    if os.name == "nt":
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(app_data, 'ZKTimeSync', ".zkdata")
    else:
        if getattr(sys, "frozen", False):
            return os.path.join(os.path.dirname(sys.executable), ".zkdata")
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".zkdata")

FIXED_API_URL = "https://payrool.nitbd.com/api/iclock/cdata"
SECRET_PASSWORD = "mes@ft"


# ===== THEME =====
COLORS = {
    "bg": "#F1F5F9",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "header": "#0F172A",
    "header_sub": "#94A3B8",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_light": "#DBEAFE",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "disabled": "#94A3B8",
    "log_bg": "#0F172A",
    "log_fg": "#E2E8F0",
}


def enable_dpi_awareness():
    """Sharp text on high-DPI Windows screens"""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def resource_path(name):
    """File next to the exe (installer copies app_icon.ico there) or next to this script"""
    if getattr(sys, "frozen", False):
        candidates = [os.path.dirname(sys.executable), getattr(sys, "_MEIPASS", "")]
    else:
        candidates = [os.path.dirname(os.path.abspath(__file__))]
    for base in candidates:
        path = os.path.join(base, name)
        if base and os.path.exists(path):
            return path
    return None


def pick_font_family(root):
    families = set(tkfont.families(root))
    for name in ("Segoe UI", "Inter", "Helvetica Neue", "Ubuntu", "DejaVu Sans"):
        if name in families:
            return name
    return tkfont.nametofont("TkDefaultFont").actual("family")


def pick_mono_family(root):
    families = set(tkfont.families(root))
    for name in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"):
        if name in families:
            return name
    return "Courier"


def setup_styles(root):
    f = pick_font_family(root)
    c = COLORS
    style = ttk.Style(root)
    style.theme_use("clam")

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=f, size=10)
        except tk.TclError:
            pass

    style.configure(".", background=c["bg"], foreground=c["text"], font=(f, 10))
    style.configure("TFrame", background=c["bg"])
    style.configure("Card.TFrame", background=c["card"])
    style.configure("TLabel", background=c["bg"], foreground=c["text"])
    style.configure("Card.TLabel", background=c["card"], foreground=c["text"])
    style.configure("CardTitle.TLabel", background=c["card"], foreground=c["text"], font=(f, 11, "bold"))
    style.configure("Muted.TLabel", background=c["card"], foreground=c["muted"], font=(f, 9))
    style.configure("Field.TLabel", background=c["card"], foreground=c["muted"], font=(f, 9, "bold"))
    style.configure("Status.TLabel", background=c["card"], foreground=c["muted"], font=(f, 9))
    style.configure("Link.TLabel", background=c["card"], foreground=c["primary"], font=(f, 9, "underline"))

    # Buttons
    style.configure("TButton", background=c["card"], foreground=c["text"], bordercolor=c["border"],
                    lightcolor=c["card"], darkcolor=c["card"], focuscolor=c["card"],
                    padding=(12, 6), font=(f, 10))
    style.map("TButton",
              background=[("disabled", c["bg"]), ("pressed", c["border"]), ("active", c["bg"])],
              foreground=[("disabled", c["disabled"])])

    style.configure("Primary.TButton", background=c["primary"], foreground="#FFFFFF",
                    bordercolor=c["primary"], lightcolor=c["primary"], darkcolor=c["primary"],
                    focuscolor=c["primary"], padding=(16, 10), font=(f, 11, "bold"))
    style.map("Primary.TButton",
              background=[("disabled", c["disabled"]), ("pressed", c["primary_dark"]), ("active", c["primary_dark"])],
              bordercolor=[("disabled", c["disabled"]), ("active", c["primary_dark"])],
              lightcolor=[("disabled", c["disabled"]), ("active", c["primary_dark"])],
              darkcolor=[("disabled", c["disabled"]), ("active", c["primary_dark"])],
              foreground=[("disabled", "#F8FAFC")])

    style.configure("Danger.TButton", foreground=c["danger"])
    style.configure("Chip.TButton", padding=(8, 3), font=(f, 9))

    style.configure("Header.TButton", background=c["header"], foreground="#FFFFFF",
                    bordercolor="#334155", lightcolor=c["header"], darkcolor=c["header"],
                    focuscolor=c["header"], padding=(8, 4))
    style.map("Header.TButton", background=[("active", "#1E293B")])
    style.configure("HeaderIcon.TButton", background=c["header"], foreground="#FFFFFF",
                    bordercolor=c["header"], lightcolor=c["header"], darkcolor=c["header"],
                    focuscolor=c["header"], padding=(4, 4), font=(f, 14))
    style.map("HeaderIcon.TButton", background=[("active", "#1E293B")],
              bordercolor=[("active", "#334155")])

    # Inputs
    style.configure("TCombobox", fieldbackground=c["card"], background=c["card"], bordercolor=c["border"],
                    lightcolor=c["card"], darkcolor=c["card"], arrowcolor=c["muted"], padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", c["card"])],
              selectbackground=[("readonly", c["card"])], selectforeground=[("readonly", c["text"])])
    style.configure("TEntry", fieldbackground=c["card"], bordercolor=c["border"],
                    lightcolor=c["card"], darkcolor=c["card"], padding=4)
    style.configure("DateEntry", fieldbackground=c["card"], bordercolor=c["border"],
                    lightcolor=c["card"], darkcolor=c["card"], arrowcolor=c["muted"], padding=4)

    # Device table
    style.configure("Treeview", background=c["card"], fieldbackground=c["card"], foreground=c["text"],
                    bordercolor=c["border"], lightcolor=c["card"], darkcolor=c["card"],
                    rowheight=30, font=(f, 10))
    style.map("Treeview", background=[("selected", c["primary_light"])],
              foreground=[("selected", c["text"])])
    style.configure("Treeview.Heading", background="#F8FAFC", foreground=c["muted"],
                    bordercolor=c["border"], lightcolor="#F8FAFC", darkcolor="#F8FAFC",
                    relief="flat", padding=(8, 6), font=(f, 9, "bold"))
    style.map("Treeview.Heading", background=[("active", c["bg"])])

    style.configure("Horizontal.TProgressbar", background=c["primary"], troughcolor=c["bg"],
                    bordercolor=c["bg"], lightcolor=c["primary"], darkcolor=c["primary"], thickness=6)
    style.configure("TScrollbar", background=c["bg"], troughcolor=c["card"], bordercolor=c["card"],
                    arrowcolor=c["muted"], lightcolor=c["bg"], darkcolor=c["bg"])
    return f


class Tooltip:
    """Small hover label for icon-only buttons"""

    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def show(self, event=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        tk.Label(self.tip, text=self.text, bg="#1E293B", fg="#FFFFFF", padx=8, pady=3,
                 font=(tkfont.nametofont("TkDefaultFont").actual("family"), 9)).pack()
        self.tip.update_idletasks()
        self.tip.wm_geometry(f"+{x - self.tip.winfo_width() // 2}+{y}")

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


CLOCK_DRIFT_WARN = timedelta(minutes=5)
STATUS_RECHECK_MS = 5 * 60 * 1000

# state -> (label, dot color)
DEVICE_STATES = {
    "online": ("Online", "#16A34A"),
    "warning": ("Online", "#D97706"),
    "offline": ("Offline", "#DC2626"),
    "checking": ("Checking…", "#60A5FA"),
    "unknown": ("Unknown", "#94A3B8"),
}


def make_dot(color, size=14, radius=5):
    """Small anti-aliased status dot for the device table"""
    img = tk.PhotoImage(width=size, height=size)
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    cx = cy = (size - 1) / 2
    for y in range(size):
        row = []
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            a = max(0.0, min(1.0, radius + 0.5 - d))  # edge coverage
            if a <= 0:
                row.append("#FFFFFF")
            else:
                # blend onto white
                row.append("#%02x%02x%02x" % tuple(int(255 + (c - 255) * a) for c in (r, g, b)))
        img.put("{" + " ".join(row) + "}", to=(0, y))
        for x in range(size):
            if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 > radius + 0.5:
                img.tk.call(img.name, "transparency", "set", x, y, 1)  # corners see-through
    return img


class RowTooltip:
    """Hover tooltip for Treeview rows; text comes from a callback(item_id)"""

    def __init__(self, tree, get_text):
        self.tree, self.get_text = tree, get_text
        self.tip, self.item = None, None
        tree.bind("<Motion>", self.on_motion, add="+")
        tree.bind("<Leave>", lambda e: self.hide(), add="+")

    def on_motion(self, event):
        item = self.tree.identify_row(event.y)
        if item == self.item:
            return
        self.hide()
        self.item = item
        text = self.get_text(item) if item else ""
        if not text:
            return
        self.tip = tk.Toplevel(self.tree)
        self.tip.wm_overrideredirect(True)
        tk.Label(self.tip, text=text, bg="#1E293B", fg="#FFFFFF", padx=10, pady=6, justify="left",
                 font=(tkfont.nametofont("TkDefaultFont").actual("family"), 9)).pack()
        self.tip.wm_geometry(f"+{event.x_root + 14}+{event.y_root + 16}")

    def hide(self):
        self.item = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


def make_card(parent, title, subtitle=None):
    """White card with a thin border; returns (outer, body)"""
    outer = tk.Frame(parent, bg=COLORS["card"], highlightthickness=1,
                     highlightbackground=COLORS["border"], highlightcolor=COLORS["border"])
    head = ttk.Frame(outer, style="Card.TFrame", padding=(16, 14, 16, 0))
    head.pack(fill="x")
    ttk.Label(head, text=title, style="CardTitle.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(head, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
    body = ttk.Frame(outer, style="Card.TFrame", padding=16)
    body.pack(fill="both", expand=True)
    return outer, body


# ===== DEVICE FORM =====
class DeviceDialog(tk.Toplevel):
    """One form for IP / Port / Comm Key instead of three separate popups"""

    def __init__(self, parent, title, device=None):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.configure(bg=COLORS["card"])
        self.resizable(False, False)
        self.transient(parent)

        device = device or {}
        body = ttk.Frame(self, style="Card.TFrame", padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=title, style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(body, text="ZKTeco device connection details", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

        self.ip_var = tk.StringVar(value=device.get("ip", ""))
        self.port_var = tk.StringVar(value=str(device.get("port", 4370)))
        self.pwd_var = tk.StringVar(value=str(device.get("password", 0)))

        fields = (("IP Address", self.ip_var, "e.g. 192.168.1.201"),
                  ("Port", self.port_var, "Default 4370"),
                  ("Comm Key (Password)", self.pwd_var, "0 if none"))
        self.entries = []
        for i, (label, var, hint) in enumerate(fields):
            r = 2 + i * 2
            ttk.Label(body, text=label, style="Field.TLabel").grid(row=r, column=0, sticky="w")
            ttk.Label(body, text=hint, style="Muted.TLabel").grid(row=r, column=1, sticky="e")
            e = ttk.Entry(body, textvariable=var, width=36)
            e.grid(row=r + 1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
            self.entries.append(e)
        self.entries[2].configure(show="•")

        self.error_var = tk.StringVar()
        self.msg_label = tk.Label(body, textvariable=self.error_var, bg=COLORS["card"], fg=COLORS["danger"],
                                  anchor="w", justify="left", wraplength=320)
        self.msg_label.grid(row=8, column=0, columnspan=2, sticky="ew")

        btns = ttk.Frame(body, style="Card.TFrame")
        btns.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.test_btn = ttk.Button(btns, text="Test", command=self.on_test)
        self.test_btn.pack(side="left")
        ttk.Button(btns, text="Save Device", style="Primary.TButton", command=self.on_save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=8)

        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.entries[0].focus_set()
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def show_message(self, text, color="danger"):
        self.msg_label.configure(fg=COLORS[color])
        self.error_var.set(text)

    def parse_fields(self):
        """Validated {ip, port, password}, or None after showing the error"""
        ip = self.ip_var.get().strip()
        if not ip:
            self.show_message("IP address is required")
            return None
        try:
            port = int(self.port_var.get().strip() or 4370)
            password = int(self.pwd_var.get().strip() or 0)
        except ValueError:
            self.show_message("Port and Comm Key must be numbers")
            return None
        if not 1 <= port <= 65535:
            self.show_message("Port must be between 1 and 65535")
            return None
        return {"ip": ip, "port": port, "password": password}

    def on_test(self):
        data = self.parse_fields()
        if not data:
            return
        self.show_message(f"Connecting to {data['ip']}:{data['port']}…", "muted")
        self.test_btn.state(["disabled"])

        def worker():
            res = check_device(data["ip"], data["port"], data["password"])
            if res["ok"]:
                msg = (f"✔ Connected — SN {res['sn']}", "success")
            else:
                msg = (f"✖ {res['error']}", "danger")
            self.after(0, lambda: self._test_done(*msg))

        threading.Thread(target=worker, daemon=True).start()

    def _test_done(self, text, color):
        if self.winfo_exists():
            self.test_btn.state(["!disabled"])
            self.show_message(text, color)

    def on_save(self):
        # Secret trigger: special password opens the API URL setter
        if self.pwd_var.get().strip() == SECRET_PASSWORD:
            self.result = {"secret": True}
            self.destroy()
            return

        data = self.parse_fields()
        if not data:
            return
        self.result = data
        self.destroy()

    def show(self):
        self.wait_window(self)
        return self.result


# ===== SETTINGS FORM =====
def validate_api_url(url):
    """Return an error message, or "" if the URL looks usable"""
    if not url:
        return "API URL is required"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "Enter a full URL starting with http:// or https://"
    return ""


class SettingsDialog(tk.Toplevel):
    """Visible form to add / edit the sync API URL"""

    def __init__(self, parent, current_url):
        super().__init__(parent)
        self.result = None
        self.title("Settings")
        self.configure(bg=COLORS["card"])
        self.resizable(False, False)
        self.transient(parent)

        body = ttk.Frame(self, style="Card.TFrame", padding=24)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text="Sync Settings", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(body, text="Attendance logs are sent to this payroll API", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

        ttk.Label(body, text="Sync API URL", style="Field.TLabel").grid(row=2, column=0, sticky="w")
        reset = ttk.Label(body, text="Reset to default", style="Link.TLabel", cursor="hand2")
        reset.grid(row=2, column=1, sticky="e")
        reset.bind("<Button-1>", lambda e: self.url_var.set(FIXED_API_URL))

        self.url_var = tk.StringVar(value=current_url or "")
        self.entry = ttk.Entry(body, textvariable=self.url_var, width=60)
        self.entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        ttk.Label(body, text=f"Example: {FIXED_API_URL}", style="Muted.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w")

        self.msg_label = tk.Label(body, text="", bg=COLORS["card"], fg=COLORS["danger"], anchor="w",
                                  justify="left", wraplength=460)
        self.msg_label.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        btns = ttk.Frame(body, style="Card.TFrame")
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.test_btn = ttk.Button(btns, text="Test Connection", command=self.on_test)
        self.test_btn.pack(side="left")
        ttk.Button(btns, text="Save", style="Primary.TButton", command=self.on_save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=8)

        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.entry.focus_set()
        self.entry.icursor("end")
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def show_message(self, text, color="danger"):
        self.msg_label.configure(text=text, fg=COLORS[color])

    def on_test(self):
        url = self.url_var.get().strip()
        error = validate_api_url(url)
        if error:
            self.show_message(error)
            return
        self.show_message("Testing connection…", "muted")
        self.test_btn.state(["disabled"])

        def worker():
            try:
                r = requests.get(url, timeout=8)
                # Any HTTP reply (even 405 for a POST-only endpoint) means the server is reachable
                result = (f"✔ Server reachable (HTTP {r.status_code})", "success")
            except requests.RequestException as e:
                result = (f"✖ Cannot reach server: {e.__class__.__name__}", "danger")
            self.after(0, lambda: self._test_done(*result))

        threading.Thread(target=worker, daemon=True).start()

    def _test_done(self, text, color):
        if self.winfo_exists():
            self.test_btn.state(["!disabled"])
            self.show_message(text, color)

    def on_save(self):
        url = self.url_var.get().strip()
        error = validate_api_url(url)
        if error:
            self.show_message(error)
            return
        self.result = url
        self.destroy()

    def show(self):
        self.wait_window(self)
        return self.result


# ===== MAIN APP =====
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTime Sync")
        self.root.configure(bg=COLORS["bg"])
        self.font = setup_styles(root)
        self.mono = pick_mono_family(root)

        icon = resource_path("app_icon.ico")
        if icon and os.name == "nt":
            try:
                self.root.iconbitmap(icon)
            except tk.TclError:
                pass

        self.config = load_config()
        # Hidden API URL setter shortcut: Ctrl+Alt+A
        try:
            self.root.bind("<Control-Alt-a>", lambda e: self.prompt_set_api_url())
        except Exception:
            pass
        self.sync_thread_running = False
        self.auto_sync_job = None
        self.device_status = {}   # (ip, port) -> {"state", "detail", "checked"}
        self.checks_running = 0
        self.waiting_sync = None

        self.build_header()
        self.build_status_bar()  # packed before the body so it always stays visible

        body = ttk.Frame(root, padding=(20, 16, 20, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0, minsize=330)
        body.rowconfigure(1, weight=1)

        self.build_devices_card(body).grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.build_sync_card(body).grid(row=0, column=1, sticky="nsew")
        self.build_log_card(body).grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 0))

        # close handler
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # Initial populate tree
        self.refresh_devices()

        # Check device connections now and every few minutes
        self.root.after(600, self.check_devices)
        self.root.after(STATUS_RECHECK_MS, self.periodic_check)

        # Start auto sync if configured
        current = self.config.get("auto_sync_interval", 0)
        if current > 0:
            self.schedule_auto_sync(current)

        storage_type = "Windows Registry" if USE_REGISTRY else "File"
        self.log(f"📁 Data storage: {storage_type}")

        self.root.update_idletasks()
        self.root.minsize(940, 680)
        self.root.geometry("1000x720")

    # ===== LAYOUT =====
    def build_header(self):
        c = COLORS
        header = tk.Frame(self.root, bg=c["header"], padx=20, pady=14)
        header.pack(fill="x")

        logo = tk.Canvas(header, width=36, height=36, bg=c["header"], highlightthickness=0)
        logo.create_oval(2, 2, 34, 34, fill=c["primary"], outline="")
        logo.create_text(18, 18, text="ZK", fill="#FFFFFF", font=(self.font, 11, "bold"))
        logo.pack(side="left")

        titles = tk.Frame(header, bg=c["header"])
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="ZKTime Sync", bg=c["header"], fg="#FFFFFF",
                 font=(self.font, 15, "bold")).pack(anchor="w")
        tk.Label(titles, text="Attendance device sync to payroll", bg=c["header"], fg=c["header_sub"],
                 font=(self.font, 9)).pack(anchor="w")

        about_btn = ttk.Button(header, text="ℹ", style="HeaderIcon.TButton", width=3,
                               command=self.show_dev_info)
        about_btn.pack(side="right")
        Tooltip(about_btn, "About")
        settings_btn = ttk.Button(header, text="⚙", style="HeaderIcon.TButton", width=3,
                                  command=self.open_settings)
        settings_btn.pack(side="right", padx=(0, 6))
        Tooltip(settings_btn, "Settings")

        self.status_pill = tk.Label(header, text="", bg=c["header"], font=(self.font, 9, "bold"),
                                    padx=12, pady=4)
        self.status_pill.pack(side="right", padx=12)
        self.set_status("ready")

    def build_devices_card(self, parent):
        outer, body = make_card(parent, "Devices", "Attendance machines on your network")

        table = ttk.Frame(body, style="Card.TFrame")
        table.pack(fill="both", expand=True)
        self.dots = {state: make_dot(color) for state, (_, color) in DEVICE_STATES.items()}
        self.tree = ttk.Treeview(table, columns=("IP", "Port", "SN"), show="tree headings", height=6,
                                 selectmode="browse")
        self.tree.heading("#0", text="STATUS", anchor="w")
        self.tree.column("#0", width=120, anchor="w", stretch=False)
        self.tree.heading("IP", text="IP ADDRESS", anchor="w")
        self.tree.heading("Port", text="PORT", anchor="w")
        self.tree.heading("SN", text="SERIAL NUMBER", anchor="w")
        self.tree.column("IP", width=150, anchor="w")
        self.tree.column("Port", width=70, anchor="w", stretch=False)
        self.tree.column("SN", width=200, anchor="w")
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.empty_label = ttk.Label(table, text="No devices yet. Click “Add Device” to get started.",
                                     style="Muted.TLabel")

        self.tree.bind("<Double-1>", lambda e: self.edit_device())
        self.tree.bind("<Delete>", lambda e: self.remove_device())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_device_buttons())
        RowTooltip(self.tree, self.status_tooltip)

        btns = ttk.Frame(body, style="Card.TFrame")
        btns.pack(fill="x", pady=(12, 0))
        ttk.Button(btns, text="＋  Add Device", command=self.add_device).pack(side="left")
        self.edit_btn = ttk.Button(btns, text="Edit", command=self.edit_device)
        self.edit_btn.pack(side="left", padx=8)
        self.remove_btn = ttk.Button(btns, text="Remove", style="Danger.TButton", command=self.remove_device)
        self.remove_btn.pack(side="left")
        self.device_count_var = tk.StringVar()
        ttk.Label(btns, textvariable=self.device_count_var, style="Muted.TLabel").pack(side="right")
        self.check_btn = ttk.Button(btns, text="↻  Check", command=self.check_devices)
        self.check_btn.pack(side="right", padx=(0, 12))
        Tooltip(self.check_btn, "Check device connections")
        return outer

    def build_sync_card(self, parent):
        outer, body = make_card(parent, "Sync", "Send attendance logs to payroll")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="FROM", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(body, text="TO", style="Field.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        # Use tkcalendar.DateEntry if available, otherwise fallback to simple Entry
        if TKCALENDAR_AVAILABLE and DateEntry is not None:
            cal = dict(date_pattern='yyyy-mm-dd', width=12, font=(self.font, 10),
                       background=COLORS["primary"], foreground="white",
                       headersbackground=COLORS["bg"], selectbackground=COLORS["primary"],
                       maxdate=datetime.now().date() + timedelta(days=1))
            self.start_entry = DateEntry(body, textvariable=self.start_date_var, **cal)
            self.end_entry = DateEntry(body, textvariable=self.end_date_var, **cal)
        else:
            self.start_entry = ttk.Entry(body, textvariable=self.start_date_var, width=12)
            self.end_entry = ttk.Entry(body, textvariable=self.end_date_var, width=12)

        # DateEntry resets its variable to today on creation, so set defaults afterwards
        now = datetime.now()
        self.set_date_range(now - timedelta(days=1), now, announce=False)

        self.start_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.end_entry.grid(row=1, column=1, sticky="ew", pady=(4, 0), padx=(8, 0))

        chips = ttk.Frame(body, style="Card.TFrame")
        chips.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(chips, text="Today", style="Chip.TButton", command=self.set_today_range).pack(side="left")
        ttk.Button(chips, text="Yesterday", style="Chip.TButton",
                   command=self.set_yesterday_range).pack(side="left", padx=6)
        ttk.Button(chips, text="Last 7 days", style="Chip.TButton", command=self.set_last_7_days).pack(side="left")

        ttk.Separator(body).grid(row=3, column=0, columnspan=2, sticky="ew", pady=16)

        ttk.Label(body, text="AUTO SYNC", style="Field.TLabel").grid(row=4, column=0, sticky="w")
        self.auto_var = tk.StringVar()
        intervals = ["Off", "1h", "4h", "6h", "8h", "12h", "24h"]
        self.auto_menu = ttk.Combobox(body, textvariable=self.auto_var, values=intervals, state="readonly", width=8)
        self.auto_menu.grid(row=4, column=1, sticky="e")
        # set default
        self.auto_var.set(self.seconds_to_label(self.config.get("auto_sync_interval", 0)))
        self.auto_menu.bind("<<ComboboxSelected>>", self.set_auto_sync)
        ttk.Label(body, text="Sends only new logs, in the background", style="Muted.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.sync_btn = ttk.Button(body, text="⟳  Sync Now", style="Primary.TButton", command=self.run_sync)
        self.sync_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        self.progress = ttk.Progressbar(body, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.progress.grid_remove()
        return outer

    def build_log_card(self, parent):
        outer, body = make_card(parent, "Activity Log")
        ttk.Button(outer.winfo_children()[0], text="Clear", style="Chip.TButton",
                   command=self.clear_log).place(relx=1.0, x=0, y=0, anchor="ne")

        self.log_box = scrolledtext.ScrolledText(
            body, height=10, wrap="word", relief="flat", borderwidth=0,
            bg=COLORS["log_bg"], fg=COLORS["log_fg"], insertbackground=COLORS["log_fg"],
            font=(self.mono, 9), padx=12, pady=10)
        self.log_box.pack(fill="both", expand=True)
        self.log_box.tag_configure("error", foreground="#F87171")
        self.log_box.tag_configure("success", foreground="#4ADE80")
        self.log_box.tag_configure("warn", foreground="#FBBF24")
        self.log_box.tag_configure("muted", foreground="#94A3B8")
        self.log_box.configure(state="disabled")
        return outer

    def build_status_bar(self):
        bar = tk.Frame(self.root, bg=COLORS["card"], highlightthickness=1,
                       highlightbackground=COLORS["border"])
        bar.pack(fill="x", side="bottom")
        inner = ttk.Frame(bar, style="Card.TFrame", padding=(20, 6))
        inner.pack(fill="x")
        self.last_sync_var = tk.StringVar(value="Last sync: —")
        self.api_url_var = tk.StringVar(value=f"API: {self.get_api_url()}")
        ttk.Label(inner, textvariable=self.last_sync_var, style="Status.TLabel").pack(side="left")
        ttk.Label(inner, text="Natore IT", style="Status.TLabel").pack(side="right")
        api = ttk.Label(inner, textvariable=self.api_url_var, style="Link.TLabel", cursor="hand2")
        api.pack(side="right", padx=(0, 24))
        api.bind("<Button-1>", lambda e: self.open_settings())

    # ===== HELPER =====
    def log(self, text):
        self.root.after(0, lambda: self._append_log(text))

    def _append_log(self, text):
        lower = text.lower()
        if "complete" in lower:
            tag = "warn" if "failed 0" not in lower and "failed" in lower else "success"
        elif any(k in lower for k in ("error", "[failed]", "failed for", "❌", "gave up")):
            tag = "error"
        elif any(k in lower for k in ("✅", "synced", "[save]")):
            tag = "success"
        elif any(k in lower for k in ("retry", "⚠", "skipped", "rate limit")):
            tag = "warn"
        elif text.startswith("📁") or "[connect]" in lower or "[disconnect]" in lower:
            tag = "muted"
        else:
            tag = ""
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, text + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")

    def set_status(self, state):
        states = {
            "ready": ("●  Ready", "#4ADE80"),
            "syncing": ("●  Syncing…", "#FBBF24"),
            "error": ("●  Last sync failed", "#F87171"),
        }
        text, color = states[state]
        self.status_pill.configure(text=text, fg=color)

    def set_date_range(self, start, end, announce=True):
        """Update both date widgets (DateEntry needs set_date to keep its calendar in sync)"""
        for widget, var, value in ((self.start_entry, self.start_date_var, start),
                                   (self.end_entry, self.end_date_var, end)):
            if TKCALENDAR_AVAILABLE and isinstance(widget, DateEntry):
                widget.set_date(value.date())
            else:
                var.set(value.strftime("%Y-%m-%d"))
        if announce:
            self.log(f"Date range set to: {start:%Y-%m-%d} to {end:%Y-%m-%d}")

    def set_today_range(self):
        """Set date range to today"""
        now = datetime.now()
        self.set_date_range(now, now)

    def set_yesterday_range(self):
        """Set date range to yesterday only"""
        yesterday = datetime.now() - timedelta(days=1)
        self.set_date_range(yesterday, yesterday)

    def set_last_7_days(self):
        """Set date range to last 7 days"""
        now = datetime.now()
        self.set_date_range(now - timedelta(days=6), now)

    def validate_date_range(self, start_date, end_date):
        """Validate date range format YYYY-MM-DD"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                return False, "Start date cannot be after end date"
            return True, ""
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"

    def seconds_to_label(self, sec):
        mapping = {0: "Off", 3600: "1h", 14400: "4h", 21600: "6h", 28800: "8h", 43200: "12h", 86400: "24h"}
        return mapping.get(sec, "Off")

    def label_to_seconds(self, label):
        mapping = {"Off": 0, "1h": 3600, "4h": 14400, "6h": 21600, "8h": 28800, "12h": 43200, "24h": 86400}
        return mapping.get(label, 0)

    # ===== DEVICE MANAGEMENT =====
    def refresh_devices(self):
        # selection ধরে রাখি
        selected = self.tree.selection()
        sel_idx = self.tree.index(selected[0]) if selected else None

        # Treeview খালি করা
        for item in self.tree.get_children():
            self.tree.delete(item)

        devices = self.config.get("devices", [])

        # ডিভাইস লিস্ট Treeview-এ দেখানো
        for i, dev in enumerate(devices):
            ip = str(dev.get("ip", ""))
            port = str(dev.get("port", 4370))
            sn = str(dev.get("sn") or "Not synced yet")
            state = self.device_status.get(self.device_key(dev), {}).get("state", "unknown")
            label = DEVICE_STATES[state][0]
            self.tree.insert("", "end", text=f" {label}", image=self.dots[state],
                             values=(ip, port, sn), tags=("odd",) if i % 2 else ())

        children = self.tree.get_children()
        if sel_idx is not None and sel_idx < len(children):
            self.tree.selection_set(children[sel_idx])

        if devices:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.55, anchor="center")
        self.device_count_var.set(f"{len(devices)} device{'s' if len(devices) != 1 else ''}")
        self.update_device_buttons()

    def update_device_buttons(self):
        state = "!disabled" if self.tree.selection() else "disabled"
        self.edit_btn.state([state])
        self.remove_btn.state([state])

    # ===== DEVICE STATUS =====
    @staticmethod
    def device_key(dev):
        return (str(dev.get("ip", "")), int(dev.get("port", 4370) or 4370))

    def set_device_status(self, dev, state, detail=""):
        self.device_status[self.device_key(dev)] = {"state": state, "detail": detail,
                                                    "checked": datetime.now()}

    def status_tooltip(self, item):
        idx = self.tree.index(item)
        devices = self.config.get("devices", [])
        if idx >= len(devices):
            return ""
        info = self.device_status.get(self.device_key(devices[idx]))
        if not info:
            return "Not checked yet"
        if info["state"] == "checking":
            return "Checking connection…"
        lines = [info["detail"]] if info["detail"] else []
        lines.append(f"Checked at {info['checked']:%I:%M %p}")
        return "\n".join(lines)

    def check_devices(self, indices=None):
        """Test device connections in the background and update the STATUS column"""
        if self.sync_thread_running:
            return  # sync is talking to the devices right now
        devices = self.config.get("devices", [])
        if indices is None:
            indices = range(len(devices))
        targets = [copy.deepcopy(devices[i]) for i in indices if i < len(devices)]
        if not targets:
            return
        for dev in targets:
            self.set_device_status(dev, "checking")
        self.checks_running += len(targets)
        self.check_btn.state(["disabled"])
        self.refresh_devices()

        for dev in targets:
            threading.Thread(target=self._check_worker, args=(dev,), daemon=True).start()

    def _check_worker(self, dev):
        res = check_device(dev.get("ip"), dev.get("port", 4370), dev.get("password", 0))
        self.root.after(0, lambda: self._check_done(dev, res))

    def _check_done(self, dev, res):
        self.checks_running = max(0, self.checks_running - 1)
        if res["ok"]:
            detail, state = f"Connected · SN {res['sn']}", "online"
            device_time = res.get("time")
            if isinstance(device_time, datetime):
                drift = device_time - datetime.now()
                if abs(drift) > CLOCK_DRIFT_WARN:
                    minutes = int(abs(drift).total_seconds() // 60)
                    way = "ahead" if drift.total_seconds() > 0 else "behind"
                    detail += f"\n⚠ Device clock is {minutes} min {way} ({device_time:%Y-%m-%d %H:%M})"
                    state = "warning"
            self.set_device_status(dev, state, detail)
            self.update_serials({dev.get("ip"): res["sn"]}, refresh=False)
        else:
            self.set_device_status(dev, "offline", res["error"])
            self.log(f"⚠ Device {dev.get('ip')} offline: {res['error']}")
        if self.checks_running == 0:
            self.check_btn.state(["!disabled"])
        self.refresh_devices()

    def periodic_check(self):
        if not self.sync_thread_running and self.checks_running == 0:
            self.check_devices()
        self.root.after(STATUS_RECHECK_MS, self.periodic_check)

    def ask_device(self, title, device=None):
        return DeviceDialog(self.root, title, device).show()

    def add_device(self):
        data = self.ask_device("Add Device")
        if not data:
            return
        if data.get("secret"):
            self.prompt_set_api_url()
            return

        try:
            # পুরনো config লোড করি
            cfg = load_config()

            # নতুন ডিভাইস যোগ
            cfg.setdefault("devices", []).append({**data, "sn": None})

            # সংরক্ষণ
            save_config(cfg)

            # GUI update
            self.config = cfg
            self.refresh_devices()
            self.log(f"✅ Device added: {data['ip']}:{data['port']}")
            self.check_devices([len(cfg["devices"]) - 1])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save device:\n{str(e)}", parent=self.root)

    def edit_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit Device", "Please select a device first", parent=self.root)
            return
        idx = self.tree.index(selected[0])

        try:
            # ফাইল থেকে fresh config লোড
            cfg = load_config()
            dev = cfg["devices"][idx]

            data = self.ask_device("Edit Device", dev)
            if not data:
                return  # cancelled
            if data.get("secret"):
                self.prompt_set_api_url()
                return

            # IP বদলালে পুরনো SN আর প্রযোজ্য না
            if dev.get("ip") != data["ip"]:
                dev["sn"] = None
            dev.update(data)

            # সংরক্ষণ
            save_config(cfg)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            self.log(f"✅ Device updated: {data['ip']}:{data['port']}")
            self.check_devices([idx])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit device:\n{str(e)}", parent=self.root)

    def remove_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Remove Device", "Please select a device first", parent=self.root)
            return
        idx = self.tree.index(selected[0])
        ip = self.tree.item(selected[0], "values")[0]
        if not messagebox.askyesno("Remove Device", f"Remove device {ip}?", parent=self.root):
            return

        try:
            # ফাইল থেকে fresh config লোড
            cfg = load_config()

            # remove the device
            removed = cfg["devices"].pop(idx)
            self.device_status.pop(self.device_key(removed), None)

            # সংরক্ষণ
            save_config(cfg)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            self.log(f"Device removed: {ip}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove device:\n{str(e)}", parent=self.root)

    # ===== SYNC =====
    def get_date_range(self):
        """Read the selected dates as YYYY-MM-DD strings"""
        values = []
        for widget, var in ((self.start_entry, self.start_date_var), (self.end_entry, self.end_date_var)):
            if TKCALENDAR_AVAILABLE and isinstance(widget, DateEntry):
                try:
                    values.append(widget.get_date().strftime("%Y-%m-%d"))
                    continue
                except Exception:
                    pass
            values.append(var.get().strip())
        return values

    def run_sync(self):
        if not self.config.get("devices"):
            messagebox.showerror("Error", "No devices added!", parent=self.root)
            return

        # Validate selected date range
        start_date, end_date = self.get_date_range()
        valid, error_msg = self.validate_date_range(start_date, end_date)
        if not valid:
            messagebox.showerror("Invalid Date Range", error_msg, parent=self.root)
            return

        self.start_sync(start_date, end_date, incremental=False)

    def start_sync(self, start_date, end_date, incremental):
        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return False
        if self.checks_running:
            # a device accepts one connection at a time - wait for the status check
            if self.waiting_sync is None:
                self.log("⏳ Waiting for device check to finish…")
            self.waiting_sync = self.root.after(500, lambda: self._resume_sync(start_date, end_date, incremental))
            return True
        self.sync_thread_running = True
        self.sync_btn.state(["disabled"])
        self.sync_btn.configure(text="Syncing…")
        self.progress.grid()
        self.progress.start(12)
        self.set_status("syncing")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        devices = copy.deepcopy(self.config.get("devices", []))
        threading.Thread(target=self.sync_thread, args=(devices, start_date, end_date, incremental),
                         daemon=True).start()
        return True

    def _resume_sync(self, start_date, end_date, incremental):
        self.waiting_sync = None
        self.start_sync(start_date, end_date, incremental)

    def sync_thread(self, devices, start_date, end_date, incremental):
        serials = {}
        ok = False
        try:
            api_url = self.get_api_url()
            serials = fetch_logs_and_sync(api_url, devices, self.log, start_date=start_date,
                                          end_date=end_date, incremental=incremental) or {}
            ok = True
            self.root.after(0, lambda: self.mark_sync_status(devices, serials))
        except Exception as e:
            msg = str(e)
            self.log(f"❌ Sync failed: {msg}")
            if not incremental:
                self.root.after(0, lambda: messagebox.showerror("Sync Failed", msg, parent=self.root))
        finally:
            self.root.after(0, lambda: self.finish_sync(serials, ok))

    def finish_sync(self, serials=None, ok=True):
        self.sync_thread_running = False
        self.progress.stop()
        self.progress.grid_remove()
        self.sync_btn.state(["!disabled"])
        self.sync_btn.configure(text="⟳  Sync Now")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.set_status("ready" if ok else "error")
        self.last_sync_var.set(f"Last sync: {datetime.now():%d %b %Y, %I:%M %p}"
                               + ("" if ok else "  (failed)"))
        self.update_serials(serials or {})

    def mark_sync_status(self, devices, serials):
        """Sync already tried every device - reuse that as the connection status"""
        for dev in devices:
            if dev.get("ip") in serials:
                self.set_device_status(dev, "online", f"Connected during sync · SN {serials[dev['ip']]}")
            else:
                self.set_device_status(dev, "offline", "Could not connect during sync (see Activity Log)")
        self.refresh_devices()

    def update_serials(self, serials, refresh=True):
        """Store device SNs read during sync so the Device List shows them"""
        changed = False
        for dev in self.config.get("devices", []):
            sn = serials.get(dev.get("ip"))
            if sn and dev.get("sn") != sn:
                dev["sn"] = sn
                changed = True
        if changed:
            save_config(self.config)
            if refresh:
                self.refresh_devices()

    def get_api_url(self):
        """Return configured API URL or default."""
        return self.config.get("api_url") or FIXED_API_URL

    def open_settings(self):
        """Settings window: add / edit the sync API URL"""
        new_url = SettingsDialog(self.root, self.get_api_url()).show()
        if not new_url or new_url == self.get_api_url():
            return
        self.config["api_url"] = new_url
        save_config(self.config)
        self.api_url_var.set(f"API: {new_url}")
        self.log(f"🔒 API URL updated: {new_url}")

    # Old shortcuts (Ctrl+Alt+A, secret password) open the same Settings window
    prompt_set_api_url = open_settings

    def disable_close(self):
        messagebox.showwarning("Sync Running", "Sync is running. Please wait until it finishes.", parent=self.root)

    # ===== AUTO SYNC =====
    def set_auto_sync(self, event=None):
        label = self.auto_var.get()
        interval = self.label_to_seconds(label)
        self.config["auto_sync_interval"] = interval
        save_config(self.config)
        if self.auto_sync_job:
            self.root.after_cancel(self.auto_sync_job)
            self.auto_sync_job = None
        if interval > 0:
            self.schedule_auto_sync(interval)
            self.log(f"⏰ Auto sync every {label}")
        else:
            self.log("⏰ Auto sync turned off")

    def schedule_auto_sync(self, interval):
        def job():
            # reschedule first so an error in this run never stops auto sync
            self.auto_sync_job = self.root.after(interval * 1000, job)
            if not self.config.get("devices"):
                self.log("⏰ Auto Sync skipped: no devices added")
                return
            self.log("⏰ Auto Sync triggered")
            # Auto sync sends every log newer than the last synced one (catches up missed days)
            today = datetime.now().strftime("%Y-%m-%d")
            self.start_sync(today, today, incremental=True)
        self.auto_sync_job = self.root.after(interval * 1000, job)

    # ===== DEV INFO =====
    def show_dev_info(self):
        messagebox.showinfo("About ZKTime Sync",
                            "ZKTime Sync\n\nDeveloped by M. Estiaque Ahmed Khan\nNatore IT (natoreit.com)",
                            parent=self.root)

# ===== MAIN =====
if __name__ == "__main__":
    enable_dpi_awareness()
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()
