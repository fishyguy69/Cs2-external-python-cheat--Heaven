import tkinter as tk
from tkinter import ttk
import threading
import pymem
import requests
import re
import time


class Config:
    def __init__(self):
        self.focused_process = "cs2.exe"  # Simulation
        self.config = {
            "fov": {
                "enabled": False,
                "value": 90
            }
        }


class FOV:
    def __init__(self, obsidian):
        self.obsidian = obsidian
        self.offsets_url = "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.hpp"
        self.client_url = "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.hpp"
        self.pm = None
        self.client = None
        self.offsets = {}
        self.default_fov = 90
        self.initialize()

    def initialize(self):
        try:
            self.pm = pymem.Pymem("cs2.exe")
            self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll")
            self.fetch_offsets()
        except Exception as e:
            print(f"FOV initialization failed: {e}")

    def fetch_offsets(self):
        try:
            offsets_content = requests.get(self.offsets_url).text
            client_content = requests.get(self.client_url).text

            pattern = re.compile(r'dwLocalPlayerController\s*=\s*0x([0-9A-Fa-f]+)')
            match = pattern.search(offsets_content)
            if match:
                self.offsets["dwLocalPlayerController"] = int(match.group(1), 16)
            else:
                raise ValueError("Offset dwLocalPlayerController not found.")

            pattern = re.compile(r'm_iDesiredFOV\s*=\s*0x([0-9A-Fa-f]+)')
            match = pattern.search(client_content)
            if match:
                self.offsets["m_iDesiredFOV"] = int(match.group(1), 16)
            else:
                raise ValueError("Offset m_iDesiredFOV not found.")
        except Exception as e:
            print(f"Failed to fetch FOV offsets: {e}")
            self.offsets = {}

    def set_fov(self, fov_value):
        if not self.pm or not self.client or not self.offsets:
            return

        try:
            dw_local_player_controller = self.pm.read_longlong(
                self.client.lpBaseOfDll + self.offsets["dwLocalPlayerController"]
            )
            if dw_local_player_controller:
                self.pm.write_int(
                    dw_local_player_controller + self.offsets["m_iDesiredFOV"], fov_value
                )
        except Exception as e:
            print(f"Failed to set FOV: {e}")

    def reset_fov(self):
        self.set_fov(self.default_fov)

    def run(self):
        while not hasattr(self.obsidian, "focused_process"):
            time.sleep(0.1)

        while True:
            time.sleep(0.1)
            if self.obsidian.focused_process != "cs2.exe":
                continue

            if not self.obsidian.config["fov"]["enabled"]:
                self.reset_fov()
                continue

            self.set_fov(self.obsidian.config["fov"]["value"])


class FOV_UI:
    def __init__(self, root, config):
        self.config = config

        self.frame = ttk.LabelFrame(root, text="FOV Controller")
        self.frame.pack(padx=10, pady=10, fill="x")

        self.enable_var = tk.BooleanVar()
        self.enable_check = ttk.Checkbutton(
            self.frame,
            text="FOV aktivieren",
            variable=self.enable_var,
            command=self.toggle_fov
        )
        self.enable_check.pack(anchor="w", padx=10, pady=5)

        self.slider = ttk.Scale(
            self.frame,
            from_=60,
            to=150,
            orient="horizontal",
            command=self.update_slider_value
        )
        self.slider.set(90)
        self.slider.pack(fill="x", padx=10)

        self.value_label = ttk.Label(self.frame, text="Aktueller FOV: 90")
        self.value_label.pack(pady=5)

    def toggle_fov(self):
        self.config.config["fov"]["enabled"] = self.enable_var.get()

    def update_slider_value(self, value):
        val = int(float(value))
        self.value_label.config(text=f"Aktueller FOV: {val}")
        self.config.config["fov"]["value"] = val


def start_fov_thread(fov_instance):
    thread = threading.Thread(target=fov_instance.run, daemon=True)
    thread.start()


if __name__ == "__main__":
    obsidian = Config()
    fov = FOV(obsidian)

    # FOV-Hintergrundprozess starten
    start_fov_thread(fov)

    # GUI starten
    root = tk.Tk()
    root.title("CS2 FOV Tool")
    app = FOV_UI(root, obsidian)
    root.mainloop()