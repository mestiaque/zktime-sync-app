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

# ===== PATHS SAFE =====
if getattr(sys, "frozen", False):
    # When running as a bundled exe, use the app installation directory
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # During development, use script directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(BASE_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(BASE_DIR, ".zkdata")

FIXED_API_URL = "https://payrool.nitbd.com/api/iclock/cdata"

# ===== CONFIG HANDLING =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {"devices": [], "auto_sync_interval": 0}
        save_config(cfg)
        return cfg

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def hide_file(path):
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
    except:
        pass

def fix_file_permissions(path):
    """Attempt to fix file permissions to make it writable"""
    try:
        if os.path.exists(path):
            # Remove read-only attribute
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            return True
    except Exception as e:
        print(f"Failed to fix permissions: {e}")
    return False

def ensure_file_writable(path):
    """Check if file is writable, attempt to fix if not"""
    if not os.path.exists(path):
        return True
    try:
        if not os.access(path, os.W_OK):
            return fix_file_permissions(path)
        return True
    except:
        return False

def save_config(cfg):
    try:
        # Ensure file is writable before attempting to save
        if not ensure_file_writable(CONFIG_FILE):
            raise PermissionError(f"Cannot write to {CONFIG_FILE}. File is read-only or permission denied.")

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

        # hide file after save (Windows)
        if os.name == "nt":
            hide_file(CONFIG_FILE)

    except PermissionError as e:
        messagebox.showerror(
            "Permission Error",
            f"Cannot write config file:\n{CONFIG_FILE}\n\n"
            f"Error: {str(e)}\n\n"
            "Solutions:\n"
            "1. Close the .zkdata file in any text editor\n"
            "2. Check file properties - remove 'Read-only' attribute\n"
            "3. Run app as Administrator\n"
            "4. Check antivirus restrictions"
        )
        raise
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save config:\n{str(e)}")
        raise

# ===== MAIN APP =====
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTeco Time Sync")
        self.root.geometry("800x550")
        self.root.resizable(False, False)

        self.config = load_config()
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
        tk.Button(btn_frame, text="🔧 Fix Permissions", width=15, command=self.fix_permissions).grid(row=0, column=3, padx=5)

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

        # ===== DATE SELECTION =====
        date_frame = tk.Frame(root)
        date_frame.pack(pady=10)
        tk.Label(date_frame, text="Sync Date:", font=("Arial", 10, "bold")).pack(side="left")

        self.date_var = tk.StringVar()
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_var.set(today)

        # Use tkcalendar.DateEntry if available, otherwise fallback to simple Entry
        if TKCALENDAR_AVAILABLE and DateEntry is not None:
            date_entry = DateEntry(date_frame, textvariable=self.date_var, date_pattern='yyyy-mm-dd', width=12, font=("Arial", 10))
        else:
            date_entry = tk.Entry(date_frame, textvariable=self.date_var, width=12, font=("Arial", 10))
        date_entry.pack(side="left", padx=5)
        tk.Label(date_frame, text="(YYYY-MM-DD)", font=("Arial", 9)).pack(side="left", padx=2)
        
        tk.Button(date_frame, text="📅 Today", width=8, command=self.set_today).pack(side="left", padx=2)
        tk.Button(date_frame, text="📅 Yesterday", width=10, command=self.set_yesterday).pack(side="left", padx=2)

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
        self.log("Data file: " + CONFIG_FILE)

    # ===== HELPER =====
    def log(self, text):
        self.root.after(0, lambda: (self.log_box.insert(tk.END, text + "\n"),
                                    self.log_box.see(tk.END)))

    def set_today(self):
        """Set date picker to today"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_var.set(today)
        self.log(f"Date set to: {today}")

    def set_yesterday(self):
        """Set date picker to yesterday"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.date_var.set(yesterday)
        self.log(f"Date set to: {yesterday}")

    def validate_date(self, date_str):
        """Validate date format YYYY-MM-DD"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

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
        self.log(f"Refreshing devices: {len(devices)} devices")  # debug log

        # ডিভাইস লিস্ট Treeview-এ দেখানো
        for dev in devices:
            ip = str(dev.get("ip", ""))
            port = str(dev.get("port", 4370))
            sn = str(dev.get("sn") or "N/A")
            self.tree.insert("", "end", values=(ip, port, sn))

    def add_device(self):
        ip = simpledialog.askstring("Add Device", "Enter Device IP:")
        if not ip:
            return
        
        port = simpledialog.askstring("Add Device", "Enter Port (default 4370):")
        password = simpledialog.askstring("Add Device", "Enter Device Password (0 if none):")
        
        try:
            port = int(port or 4370)
            password = int(password or 0)
        except ValueError:
            messagebox.showerror("Error", "Port and Password must be numbers")
            return

        try:
            # Ensure file is writable
            if not ensure_file_writable(CONFIG_FILE):
                messagebox.showerror("Permission Error", f"Cannot write to {CONFIG_FILE}.\nTry the 'Fix Permissions' button or run as Administrator.")
                return

            # পুরনো config লোড করি
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                cfg = {"devices": [], "auto_sync_interval": 0}

            # নতুন ডিভাইস যোগ
            cfg["devices"].append({
                "ip": ip.strip(),
                "port": port,
                "password": password,
                "sn": None
            })

            # ফাইলে সংরক্ষণ
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)

            # Windows হলে হাইড করে দাও
            if os.name == "nt":
                hide_file(CONFIG_FILE)

            messagebox.showinfo("Success", "Device successfully saved to .zkdata")

            # GUI update
            self.config = cfg
            self.refresh_devices()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save device:\n{str(e)}\n\nTry 'Fix Permissions' button.")

    def edit_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit Device", "Please select a device first")
            return
        idx = self.tree.index(selected[0])

        try:
            # Ensure file is writable
            if not ensure_file_writable(CONFIG_FILE):
                messagebox.showerror("Permission Error", f"Cannot write to {CONFIG_FILE}.\nTry the 'Fix Permissions' button or run as Administrator.")
                return

            # ফাইল থেকে fresh config লোড
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                messagebox.showerror("Error", ".zkdata file not found")
                return

            dev = cfg["devices"][idx]
            ip = simpledialog.askstring("Edit Device", "Enter Device IP:", initialvalue=dev["ip"])
            port = simpledialog.askstring("Edit Device", "Enter Port:", initialvalue=str(dev.get("port", 4370)))
            password = simpledialog.askstring("Edit Device", "Enter Password:", initialvalue=str(dev.get("password", 0)))

            try:
                port = int(port or 4370)
                password = int(password or 0)
            except ValueError:
                messagebox.showerror("Error", "Port and Password must be numbers")
                return

            # Update device in file config
            cfg["devices"][idx].update({"ip": ip.strip(), "port": port, "password": password})

            # ফাইলে লিখা
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            if os.name == "nt":
                hide_file(CONFIG_FILE)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            messagebox.showinfo("Success", "Device updated in .zkdata")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit device:\n{str(e)}\n\nTry 'Fix Permissions' button.")

    def remove_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Remove Device", "Please select a device first")
            return
        idx = self.tree.index(selected[0])

        try:
            # Ensure file is writable
            if not ensure_file_writable(CONFIG_FILE):
                messagebox.showerror("Permission Error", f"Cannot write to {CONFIG_FILE}.\nTry the 'Fix Permissions' button or run as Administrator.")
                return

            # ফাইল থেকে fresh config লোড
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                messagebox.showerror("Error", ".zkdata file not found")
                return

            # remove the device
            del cfg["devices"][idx]

            # ফাইলে write
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            if os.name == "nt":
                hide_file(CONFIG_FILE)

            # মেমোরি আপডেট ও Treeview refresh
            self.config = cfg
            self.refresh_devices()
            messagebox.showinfo("Success", "Device removed from .zkdata")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove device:\n{str(e)}\n\nTry 'Fix Permissions' button.")


    # ===== SYNC =====
    def run_sync(self):
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return
        
        # Validate selected date
        selected_date = self.date_var.get().strip()
        if not self.validate_date(selected_date):
            messagebox.showerror("Invalid Date", f"Date must be in format YYYY-MM-DD\nYou entered: {selected_date}")
            return

        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return
        self.sync_thread_running = True
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        threading.Thread(target=self.sync_thread, args=(selected_date,), daemon=True).start()

    def sync_thread(self, sync_date):
        try:
            self.log(f"📅 Syncing data for date: {sync_date}")
            fetch_logs_and_sync(FIXED_API_URL, self.config["devices"], self.log, sync_date=sync_date)
        except Exception as e:
            self.root.after(0, lambda: (messagebox.showerror("Sync Failed", str(e)), self.root.destroy()))
        finally:
            self.root.after(0, self.finish_sync)

    def finish_sync(self):
        self.sync_thread_running = False
        self.sync_btn.config(state="normal")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

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
            self.sync_thread_with_date(today)
            self.auto_sync_job = self.root.after(interval * 1000, job)
        self.auto_sync_job = self.root.after(interval * 1000, job)

    def sync_thread_with_date(self, sync_date):
        """Helper method to start sync with specific date"""
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return
        
        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return
        
        self.sync_thread_running = True
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        threading.Thread(target=self.sync_thread, args=(sync_date,), daemon=True).start()

    # ===== DEV INFO =====
    def show_dev_info(self):
        messagebox.showinfo("Developer Info",
                            "M. Estiaque Ahmed Khan\nNatore IT (natoreit.com)")

    def fix_permissions(self):
        """Manually fix file permissions"""
        try:
            if fix_file_permissions(CONFIG_FILE):
                messagebox.showinfo("Success", f"File permissions fixed:\n{CONFIG_FILE}")
                self.log("✓ File permissions fixed")
            else:
                messagebox.showerror("Failed", "Could not fix permissions. Try running as Administrator.")
        except Exception as e:
            messagebox.showerror("Error", f"Error fixing permissions:\n{str(e)}")

# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()


    #app .zkdata permission passe na