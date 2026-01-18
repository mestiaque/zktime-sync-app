import json
import os
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
from zk_sync import fetch_logs_and_sync

CONFIG_FILE = "config.json"

# Load config.json
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_url": "", "devices": []}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

# UI App
class ZKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZKTeco Sync Tool")
        self.root.geometry("600x450")
        
        self.config = load_config()

        # API URL Input
        tk.Label(root, text="API URL:").pack()
        self.api_entry = tk.Entry(root, width=60)
        self.api_entry.insert(0, self.config.get("api_url", ""))
        self.api_entry.pack()

        tk.Button(root, text="Save API URL", command=self.save_api).pack(pady=5)

        # Device list
        self.device_frame = tk.Frame(root)
        self.device_frame.pack()

        tk.Label(self.device_frame, text="Device List:").grid(row=0, column=0)

        self.refresh_devices()

        tk.Button(root, text="Add Device", command=self.add_device).pack(pady=5)

        # Sync Button
        tk.Button(root, text="Sync Now", bg="green", fg="white",
                  command=self.run_sync).pack(pady=10)

        # Log Box
        tk.Label(root, text="Log Output:").pack()
        self.log_box = scrolledtext.ScrolledText(root, width=70, height=10)
        self.log_box.pack()

    def save_api(self):
        self.config["api_url"] = self.api_entry.get()
        save_config(self.config)
        messagebox.showinfo("Saved", "API URL Saved!")

    def refresh_devices(self):
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        tk.Label(self.device_frame, text="IP").grid(row=0, column=0)
        tk.Label(self.device_frame, text="Password").grid(row=0, column=1)

        for idx, dev in enumerate(self.config["devices"]):
            tk.Label(self.device_frame, text=dev["ip"]).grid(row=idx+1, column=0)
            tk.Label(self.device_frame, text=dev["password"]).grid(row=idx+1, column=1)
            tk.Button(self.device_frame, text="Remove", 
                      command=lambda i=idx: self.remove_device(i)).grid(row=idx+1, column=2)

    def add_device(self):
        ip = simpledialog.askstring("Add Device", "Enter Device IP:")
        pwd = simpledialog.askstring("Device Password", "Enter password (0 if none):")

        if not ip:
            return

        self.config["devices"].append({"ip": ip, "password": int(pwd or 0)})
        save_config(self.config)
        self.refresh_devices()

    def remove_device(self, index):
        del self.config["devices"][index]
        save_config(self.config)
        self.refresh_devices()

    def run_sync(self):
        self.log_box.insert(tk.END, "Starting Sync...\n")
        self.log_box.see(tk.END)

        api = self.config["api_url"]
        devices = self.config["devices"]

        if not api:
            messagebox.showerror("Error", "API URL is required!")
            return

        if not devices:
            messagebox.showerror("Error", "No devices added!")
            return

        fetch_logs_and_sync(api, devices, self.log_box)

root = tk.Tk()
app = ZKApp(root)
root.mainloop()

