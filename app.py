import json
import os
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
from zk_sync import fetch_logs_and_sync

# ===== CONFIG =====
CONFIG_FILE = "config.json"
DEFAULT_API_URL = "https://your-api-url.com/sync"  # <-- change this


# ===== CONFIG HANDLING =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "api_url": DEFAULT_API_URL,
            "devices": []
        }
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


# ===== UI APP =====
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTeco Time Sync")
        self.root.geometry("650x480")
        self.root.resizable(False, False)

        self.config = load_config()

        # ===== DEVICE LIST =====
        tk.Label(root, text="Device List", font=("Arial", 11, "bold")).pack(pady=5)

        self.device_frame = tk.Frame(root)
        self.device_frame.pack()

        self.refresh_devices()

        tk.Button(
            root,
            text="Add Device",
            width=15,
            command=self.add_device
        ).pack(pady=5)

        # ===== SYNC BUTTON =====
        self.sync_btn = tk.Button(
            root,
            text="SYNC NOW",
            bg="green",
            fg="white",
            font=("Arial", 11, "bold"),
            width=20,
            command=self.run_sync
        )
        self.sync_btn.pack(pady=10)

        # ===== LOG BOX =====
        tk.Label(root, text="Log Output", font=("Arial", 10, "bold")).pack()
        self.log_box = scrolledtext.ScrolledText(
            root,
            width=75,
            height=14,
            state="normal"
        )
        self.log_box.pack(padx=10, pady=5)

        # Allow close initially
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    # ===== DEVICE MANAGEMENT =====
    def refresh_devices(self):
        for w in self.device_frame.winfo_children():
            w.destroy()

        tk.Label(self.device_frame, text="IP Address", width=20).grid(row=0, column=0)
        tk.Label(self.device_frame, text="Password", width=15).grid(row=0, column=1)

        for i, dev in enumerate(self.config["devices"]):
            tk.Label(self.device_frame, text=dev["ip"]).grid(row=i + 1, column=0)
            tk.Label(self.device_frame, text=dev["password"]).grid(row=i + 1, column=1)
            tk.Button(
                self.device_frame,
                text="Remove",
                fg="red",
                command=lambda x=i: self.remove_device(x)
            ).grid(row=i + 1, column=2)

    def add_device(self):
        ip = simpledialog.askstring("Add Device", "Enter Device IP:")
        if not ip:
            return

        pwd = simpledialog.askstring(
            "Device Password",
            "Enter device password (0 if none):"
        )

        try:
            pwd = int(pwd or 0)
        except ValueError:
            messagebox.showerror("Error", "Password must be a number")
            return

        self.config["devices"].append({
            "ip": ip.strip(),
            "password": pwd
        })

        save_config(self.config)
        self.refresh_devices()

    def remove_device(self, index):
        del self.config["devices"][index]
        save_config(self.config)
        self.refresh_devices()

    # ===== SYNC LOGIC =====
    def run_sync(self):
        if not self.config["devices"]:
            messagebox.showerror("Error", "No devices added!")
            return

        self.log_box.insert(tk.END, "🔄 Starting Sync...\n")
        self.log_box.see(tk.END)

        # Disable UI
        self.sync_btn.config(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)

        t = threading.Thread(target=self.sync_thread, daemon=True)
        t.start()

    def sync_thread(self):
        try:
            fetch_logs_and_sync(
                self.config["api_url"],
                self.config["devices"],
                self.log_box
            )
        finally:
            self.sync_btn.config(state="normal")
            self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def disable_close(self):
        messagebox.showwarning(
            "Sync Running",
            "Sync is running. Please wait until it finishes."
        )


# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = ZKApp(root)
    root.mainloop()
