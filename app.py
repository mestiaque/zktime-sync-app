import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
from zk_sync import fetch_logs_and_sync
import time

# ===== PATHS SAFE =====
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FIXED_API_URL = "https://payrool.nitbd.com/api/iclock/cdata"

# ===== CONFIG HANDLING =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"devices": [], "auto_sync_interval": 0}  # interval in seconds
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

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

        # ===== SYNC & DEV INFO =====
        action_frame = tk.Frame(root)
        action_frame.pack(pady=10)
        self.sync_btn = tk.Button(action_frame, text="SYNC NOW", bg="green", fg="white", width=25,
                                  font=("Arial", 11, "bold"), command=self.run_sync)
        self.sync_btn.grid(row=0, column=0, padx=5)
        tk.Button(action_frame, text="Developer Info", width=20, command=self.show_dev_info).grid(row=0, column=1, padx=5)

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

    # ===== HELPER =====
    def log(self, text):
        self.root.after(0, lambda: (self.log_box.insert(tk.END, text + "\n"),
                                    self.log_box.see(tk.END)))

    def seconds_to_label(self, sec):
        mapping = {0: "Off", 3600: "1h", 14400: "4h", 21600: "6h", 28800: "8h", 43200: "12h", 86400: "24h"}
        return mapping.get(sec, "Off")

    def label_to_seconds(self, label):
        mapping = {"Off": 0, "1h": 3600, "4h": 14400, "6h": 21600, "8h": 28800, "12h": 43200, "24h": 86400}
        return mapping.get(label, 0)

    # ===== DEVICE MANAGEMENT =====
    def refresh_devices(self):
        self.tree.delete(*self.tree.get_children())
        for i, dev in enumerate(self.config["devices"]):
            sn = dev.get("sn", "Unknown")
            self.tree.insert("", "end", iid=i, values=(dev["ip"], dev.get("port", 4370), sn))

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
        self.config["devices"].append({"ip": ip.strip(), "port": port, "password": password})
        save_config(self.config)
        self.refresh_devices()

    def edit_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit Device", "Please select a device first")
            return
        idx = int(selected[0])
        dev = self.config["devices"][idx]
        ip = simpledialog.askstring("Edit Device", "Enter Device IP:", initialvalue=dev["ip"])
        port = simpledialog.askstring("Edit Device", "Enter Port:", initialvalue=str(dev.get("port", 4370)))
        password = simpledialog.askstring("Edit Device", "Enter Password:", initialvalue=str(dev.get("password", 0)))
        try:
            port = int(port or 4370)
            password = int(password or 0)
        except ValueError:
            messagebox.showerror("Error", "Port and Password must be numbers")
            return
        self.config["devices"][idx].update({"ip": ip.strip(), "port": port, "password": password})
        save_config(self.config)
        self.refresh_devices()

    def remove_device(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Remove Device", "Please select a device first")
            return
        idx = int(selected[0])
        del self.config["devices"][idx]
        save_config(self.config)
        self.refresh_devices()

    # ===== SYNC =====
    def run_sync(self):
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return
        if self.sync_thread_running:
            self.log("⚠ Sync already running...")
            return
        self.sync_thread_running = True
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        threading.Thread(target=self.sync_thread, daemon=True).start()

    def sync_thread(self):
        try:
            fetch_logs_and_sync(FIXED_API_URL, self.config["devices"], self.log)
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
            self.run_sync()
            self.auto_sync_job = self.root.after(interval * 1000, job)
        self.auto_sync_job = self.root.after(interval * 1000, job)

    # ===== DEV INFO =====
    def show_dev_info(self):
        messagebox.showinfo("Developer Info",
                            "M. Estiaque Ahmed Khan\nNatore IT (natoreit.com)")

# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()