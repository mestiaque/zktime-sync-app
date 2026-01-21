import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
from zk_sync import fetch_logs_and_sync

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
        return {"devices": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

# ===== UI APP =====
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTeco Time Sync")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        self.config = load_config()
        self.sync_btn_pressed = False  # Auto-sync tracker

        tk.Label(root, text="Device List", font=("Arial", 11, "bold")).pack(pady=5)

        self.device_frame = tk.Frame(root)
        self.device_frame.pack()
        self.refresh_devices()

        tk.Button(root, text="Add Device", width=20,
                  command=self.add_device).pack(pady=5)

        self.sync_btn = tk.Button(
            root, text="SYNC NOW", bg="green", fg="white",
            font=("Arial", 11, "bold"), width=25,
            command=self.run_sync
        )
        self.sync_btn.pack(pady=10)

        tk.Label(root, text="Log Output", font=("Arial", 10, "bold")).pack()
        self.log_box = scrolledtext.ScrolledText(root, width=80, height=15)
        self.log_box.pack(padx=10, pady=5)

        # Safe close
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # ===== AUTO-SYNC in 1 hour =====
        self.auto_sync_id = self.root.after(3600*1000, self.auto_sync)

    # ===== SAFE LOG =====
    def log(self, text):
        self.root.after(0, lambda: (
            self.log_box.insert(tk.END, text + "\n"),
            self.log_box.see(tk.END)
        ))

    # ===== DEVICE MANAGEMENT =====
    def refresh_devices(self):
        for w in self.device_frame.winfo_children():
            w.destroy()

        tk.Label(self.device_frame, text="IP Address", width=20).grid(row=0, column=0)
        tk.Label(self.device_frame, text="Port", width=10).grid(row=0, column=1)
        tk.Label(self.device_frame, text="Device SN", width=15).grid(row=0, column=2)

        for i, dev in enumerate(self.config["devices"]):
            tk.Label(self.device_frame, text=dev["ip"]).grid(row=i+1, column=0)
            tk.Label(self.device_frame, text=str(dev.get("port", 4370))).grid(row=i+1, column=1)
            tk.Label(self.device_frame, text=dev.get("sn", "Unknown")).grid(row=i+1, column=2)
            tk.Button(
                self.device_frame, text="Remove", fg="red",
                command=lambda x=i: self.remove_device(x)
            ).grid(row=i+1, column=3)

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

        # SN will be fetched during sync
        self.config["devices"].append({"ip": ip.strip(), "port": port, "password": password, "sn": "Unknown"})
        save_config(self.config)
        self.refresh_devices()

    def remove_device(self, index):
        del self.config["devices"][index]
        save_config(self.config)
        self.refresh_devices()

    # ===== SYNC =====
    def run_sync(self):
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return

        try:
            self.sync_btn_pressed = True
            if hasattr(self, 'auto_sync_id'):
                self.root.after_cancel(self.auto_sync_id)

            self.log("🔄 Starting Sync...")
            self.sync_btn.config(state="disabled")
            self.root.protocol("WM_DELETE_WINDOW", self.disable_close)

            threading.Thread(target=self.sync_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Critical Error", f"Unexpected error: {e}")
            self.root.destroy()

    def sync_thread(self):
        try:
            fetch_logs_and_sync(
                FIXED_API_URL,
                self.config["devices"],
                self.log  # pass log function
            )
        except Exception as e:
            # Critical failure during sync
            self.root.after(0, lambda: (
                messagebox.showerror("Sync Failed", f"Critical error:\n{e}"),
                self.root.destroy()
            ))
        finally:
            self.root.after(0, self.finish_sync)

    def finish_sync(self):
        self.sync_btn.config(state="normal")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.refresh_devices()  # Update SNs if available

    def disable_close(self):
        messagebox.showwarning(
            "Sync Running",
            "Sync is running. Please wait until it finishes."
        )

    # ===== AUTO SYNC =====
    def auto_sync(self):
        if not self.sync_btn_pressed:
            self.log("⏰ Auto-sync after 1 hour")
            self.run_sync()

# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()
