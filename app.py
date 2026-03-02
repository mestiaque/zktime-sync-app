import json
import os
import sys
import threading
import ctypes
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
from zk_sync import fetch_logs_and_sync
import time
import stat
from datetime import datetime, timedelta

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

# ===== MAIN APP =====
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTeco Time Sync")
        self.root.geometry("800x550")
        self.root.resizable(False, False)

        self.config = load_config()
        # Hidden API URL setter shortcut: Ctrl+Alt+A
        try:
            self.root.bind("<Control-Alt-a>", lambda e: self.prompt_set_api_url())
        except Exception:
            pass
        self.sync_thread_running = False
        self.auto_sync_job = None

        # ===== DEVICE LIST FRAME =====
        device_frame = tk.Frame(root)
        device_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(device_frame, text="Device List", font=("Arial", 11, "bold")).pack(anchor="w")

        self.tree = ttk.Treeview(device_frame, columns=("IP", "Port", "SN"), show="headings", height=8)
        self.tree.heading("IP", text="IP Address")
        self.tree.heading("Port", text="Port")
        self.tree.heading("SN", text="Device SN")
        self.tree.pack(side="left", fill="x", expand=True)

        scrollbar = ttk.Scrollbar(device_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Buttons Frame
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Add Device", width=15, command=self.add_device).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Edit Device", width=15, command=self.edit_device).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Remove Device", width=15, command=self.remove_device).grid(row=0, column=2, padx=5)

        # ===== AUTO SYNC =====
        auto_frame = tk.Frame(root)
        auto_frame.pack(pady=10)
        tk.Label(auto_frame, text="Auto Sync Interval:", font=("Arial", 10, "bold")).pack(side="left")

        self.auto_var = tk.StringVar()
        intervals = ["Off", "1h", "4h", "6h", "8h", "12h", "24h"]
        self.auto_menu = ttk.Combobox(auto_frame, textvariable=self.auto_var, values=intervals, state="readonly", width=5)
        self.auto_menu.pack(side="left", padx=5)
        # set default
        current = self.config.get("auto_sync_interval", 0)
        self.auto_var.set(self.seconds_to_label(current))
        self.auto_menu.bind("<<ComboboxSelected>>", self.set_auto_sync)

        # ===== DATE RANGE SELECTION =====
        date_frame = tk.Frame(root)
        date_frame.pack(pady=10)
        tk.Label(date_frame, text="Date Range:", font=("Arial", 10, "bold")).pack(side="left")

        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.start_date_var.set(yesterday)  # Default to yesterday
        self.end_date_var.set(today)  # Default to today

        # Use tkcalendar.DateEntry if available, otherwise fallback to simple Entry
        if TKCALENDAR_AVAILABLE and DateEntry is not None:
            start_entry = DateEntry(date_frame, textvariable=self.start_date_var, date_pattern='yyyy-mm-dd', width=12, font=("Arial", 10))
            end_entry = DateEntry(date_frame, textvariable=self.end_date_var, date_pattern='yyyy-mm-dd', width=12, font=("Arial", 10))
        else:
            start_entry = tk.Entry(date_frame, textvariable=self.start_date_var, width=12, font=("Arial", 10))
            end_entry = tk.Entry(date_frame, textvariable=self.end_date_var, width=12, font=("Arial", 10))
        
        start_entry.pack(side="left", padx=5)
        tk.Label(date_frame, text="to", font=("Arial", 10)).pack(side="left", padx=2)
        end_entry.pack(side="left", padx=5)
        tk.Label(date_frame, text="(YYYY-MM-DD)", font=("Arial", 9)).pack(side="left", padx=2)
        
        tk.Button(date_frame, text="📅 Today", width=8, command=self.set_today_range).pack(side="left", padx=2)
        tk.Button(date_frame, text="📅 Yesterday", width=10, command=self.set_yesterday_range).pack(side="left", padx=2)
        tk.Button(date_frame, text="📅 Last 7 Days", width=12, command=self.set_last_7_days).pack(side="left", padx=2)

        # ===== SYNC & DEV INFO =====
        action_frame = tk.Frame(root)
        action_frame.pack(pady=10)
        self.sync_btn = tk.Button(action_frame, text="SYNC NOW", bg="green", fg="white", width=25,
                                  font=("Arial", 11, "bold"), command=self.run_sync)
        self.sync_btn.grid(row=0, column=0, padx=5)
        
        tk.Button( action_frame, text="ℹ", width=3, font=("Arial", 11, "bold"), command=self.show_dev_info ).grid(row=0, column=1, padx=5)

        # ===== LOG BOX =====
        tk.Label(root, text="Log Output", font=("Arial", 10, "bold")).pack()
        self.log_box = scrolledtext.ScrolledText(root, width=95, height=15)
        self.log_box.pack(padx=10, pady=5)

        # close handler
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # Initial populate tree
        self.refresh_devices()

        # Start auto sync if configured
        if current > 0:
            self.schedule_auto_sync(current)
        
        storage_type = "Windows Registry" if USE_REGISTRY else "File"
        self.log(f"📁 Data storage: {storage_type}")

    # ===== HELPER =====
    def log(self, text):
        self.root.after(0, lambda: (self.log_box.insert(tk.END, text + "\n"),
                                    self.log_box.see(tk.END)))

    def set_today_range(self):
        """Set date range to today"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_date_var.set(today)
        self.end_date_var.set(today)
        self.log(f"Date range set to: {today} to {today}")

    def set_yesterday_range(self):
        """Set date range to yesterday only"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.start_date_var.set(yesterday)
        self.end_date_var.set(yesterday)
        self.log(f"Date range set to: {yesterday} to {yesterday}")

    def set_last_7_days(self):
        """Set date range to last 7 days"""
        today = datetime.now().strftime("%Y-%m-%d")
        last_week = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        self.start_date_var.set(last_week)
        self.end_date_var.set(today)
        self.log(f"Date range set to: {last_week} to {today}")

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
        # Treeview খালি করা
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        devices = self.config.get("devices", [])
        self.log(f"Refreshing devices: {len(devices)} devices")

        # ডিভাইস লিস্ট Treeview-এ দেখানো
        for dev in devices:
            ip = str(dev.get("ip", ""))
            port = str(dev.get("port", 4370))
            sn = str(dev.get("sn") or "N/A")
            self.tree.insert("", "end", values=(ip, port, sn))

    def add_device(self):
        ip = simpledialog.askstring("Add Device", "Enter Device IP:", parent=self.root)
        if not ip:
            return
        
        port = simpledialog.askstring("Add Device", "Enter Port (default 4370):", parent=self.root)
        password_raw = simpledialog.askstring("Add Device", "Enter Device Password (0 if none):", parent=self.root)

        # Secret trigger: if special password entered, open API URL setter
        if password_raw == SECRET_PASSWORD:
            self.prompt_set_api_url()
            return

        try:
            port = int(port or 4370)
            password = int(password_raw or 0)
        except ValueError:
            messagebox.showerror("Error", "Port and Password must be numbers", parent=self.root)
            return

        try:
            # পুরনো config লোড করি
            cfg = load_config()

            # নতুন ডিভাইস যোগ
            cfg["devices"].append({
                "ip": ip.strip(),
                "port": port,
                "password": password,
                "sn": None
            })

            # সংরক্ষণ
            save_config(cfg)

            messagebox.showinfo("Success", "Device added successfully!", parent=self.root)

            # GUI update
            self.config = cfg
            self.refresh_devices()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save device:\n{str(e)}", parent=self.root)

    def edit_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit Device", "Please select a device first")
            return
        idx = self.tree.index(selected[0])

        try:
            # ফাইল থেকে fresh config লোড
            cfg = load_config()

            dev = cfg["devices"][idx]
            ip = simpledialog.askstring("Edit Device", "Enter Device IP:", initialvalue=dev["ip"], parent=self.root)
            port = simpledialog.askstring("Edit Device", "Enter Port:", initialvalue=str(dev.get("port", 4370)), parent=self.root)
            password_raw = simpledialog.askstring("Edit Device", "Enter Password:", initialvalue=str(dev.get("password", 0)), parent=self.root)

            # Secret trigger: open API URL setter
            if password_raw == SECRET_PASSWORD:
                self.prompt_set_api_url()
                return

            try:
                port = int(port or 4370)
                password = int(password_raw or 0)
            except ValueError:
                messagebox.showerror("Error", "Port and Password must be numbers", parent=self.root)
                return

            # Update device in config
            cfg["devices"][idx].update({"ip": ip.strip(), "port": port, "password": password})

            # সংরক্ষণ
            save_config(cfg)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            messagebox.showinfo("Success", "Device updated successfully!", parent=self.root)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit device:\n{str(e)}", parent=self.root)

    def remove_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Remove Device", "Please select a device first", parent=self.root)
            return
        idx = self.tree.index(selected[0])

        try:
            # ফাইল থেকে fresh config লোড
            cfg = load_config()

            # remove the device
            del cfg["devices"][idx]

            # সংরক্ষণ
            save_config(cfg)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            messagebox.showinfo("Success", "Device removed successfully!", parent=self.root)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove device:\n{str(e)}", parent=self.root)


    # ===== SYNC =====
    def run_sync(self):
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return
        
        # Validate selected date range
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        
        valid, error_msg = self.validate_date_range(start_date, end_date)
        if not valid:
            messagebox.showerror("Invalid Date Range", error_msg)
            return

        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return
        self.sync_thread_running = True
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        threading.Thread(target=self.sync_thread, args=(start_date, end_date), daemon=True).start()

    def sync_thread(self, start_date, end_date):
        try:
            self.log(f"📅 Syncing data for date range: {start_date} to {end_date}")
            api_url = self.get_api_url()
            fetch_logs_and_sync(api_url, self.config["devices"], self.log, start_date=start_date, end_date=end_date)
        except Exception as e:
            self.root.after(0, lambda: (messagebox.showerror("Sync Failed", str(e)), self.root.destroy()))
        finally:
            self.root.after(0, self.finish_sync)

    def finish_sync(self):
        self.sync_thread_running = False
        self.sync_btn.config(state="normal")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def get_api_url(self):
        """Return configured API URL or default."""
        return self.config.get("api_url") or FIXED_API_URL

    def prompt_set_api_url(self):
        """Hidden prompt to set the API URL (trigger with Ctrl+Alt+A)."""
        try:
            new_url = simpledialog.askstring("Set API URL (hidden)", "Enter API URL:", initialvalue=self.get_api_url(), parent=self.root)
            if new_url is None:
                return
            new_url = new_url.strip()
            if not new_url:
                messagebox.showwarning("Invalid", "API URL cannot be empty", parent=self.root)
                return
            self.config["api_url"] = new_url
            save_config(self.config)
            self.log(f"🔒 API URL updated (hidden): {new_url}")
            messagebox.showinfo("Saved", "API URL updated and saved", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set API URL:\n{e}", parent=self.root)

    def disable_close(self):
        messagebox.showwarning("Sync Running", "Sync is running. Please wait until it finishes.")

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

    def schedule_auto_sync(self, interval):
        def job():
            self.log("⏰ Auto Sync triggered")
            # Auto sync should always use today's date
            today = datetime.now().strftime("%Y-%m-%d")
            self.sync_thread_with_date(today, today)
            self.auto_sync_job = self.root.after(interval * 1000, job)
        self.auto_sync_job = self.root.after(interval * 1000, job)

    def sync_thread_with_date(self, start_date, end_date):
        """Helper method to start sync with specific date range"""
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return
        
        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return
        
        self.sync_thread_running = True
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        threading.Thread(target=self.sync_thread, args=(start_date, end_date), daemon=True).start()

    # ===== DEV INFO =====
    def show_dev_info(self):
        messagebox.showinfo("Developer Info",
                            "M. Estiaque Ahmed Khan\nNatore IT (natoreit.com)")

# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()
