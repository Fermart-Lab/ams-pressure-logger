"""Desktop pressure logger. Maintainer: JGFermart."""

import argparse
from collections import deque
import math
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial
from serial.tools import list_ports

from .core import Acquisition, LineBuffer


class SerialSource:
    """The Tk event loop is the sole owner of this nonblocking connection."""
    def __init__(self, port):
        self.port = serial.Serial(port, baudrate=9600, timeout=0)

    def read(self):
        return self.port.read(min(self.port.in_waiting, 4096))

    def clear(self):
        self.port.reset_input_buffer()

    def close(self):
        self.port.close()


class DemoSource:
    def __init__(self):
        self.started = self.last = time.monotonic()

    def read(self):
        now = time.monotonic()
        if now - self.last < 0.1:
            return b""
        self.last = now
        elapsed = now - self.started
        pressure = 10 + 0.2 * math.sin(elapsed * 2) + max(0, elapsed - 8) % 10 * 0.2
        return f"{int(elapsed * 1000) % 2**32},23.5000,{pressure:.4f}\n".encode("ascii")

    def clear(self):
        pass

    def close(self):
        pass


class PressureApp:
    def __init__(self, root, demo=False, source_factory=None):
        self.root = root
        self.demo = demo
        self.source_factory = source_factory or (lambda port: DemoSource() if demo else SerialSource(port))
        self.source = None
        self.buffer = LineBuffer()
        self.session = Acquisition("simulated" if demo else "serial")
        self.points = deque(maxlen=600)
        self.after_id = None
        self.closed = False
        root.title("AMS Pressure Logger — JGFermart" + (" — SIMULATED DATA" if demo else ""))
        root.geometry("900x620")
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AMS Pressure Logger", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text="SIMULATED DATA — no sensor connected" if demo else
                  "AMS5915 • pressure in mbar • temperature in °C").pack(anchor="w", pady=(0, 14))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x")
        self.port = ttk.Combobox(toolbar, state="readonly", width=26)
        self.port.pack(side="left")
        self.refresh_button = ttk.Button(toolbar, text="Refresh ports", command=self.refresh)
        self.refresh_button.pack(side="left", padx=6)
        self.connect_button = ttk.Button(toolbar, text="Connect", command=self.connect)
        self.connect_button.pack(side="left")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=12)
        self.background_button = ttk.Button(actions, text="Measure background (5 s)", command=self.background)
        self.background_button.pack(side="left")
        self.record_button = ttk.Button(actions, text="Start recording…", command=self.record)
        self.record_button.pack(side="left", padx=6)
        self.reading = ttk.Label(frame, text="Waiting for data", font=("Segoe UI", 15))
        self.reading.pack(anchor="w")
        self.baseline_label = ttk.Label(frame, text="Background: not measured")
        self.baseline_label.pack(anchor="w", pady=5)
        self.canvas = tk.Canvas(frame, background="white", highlightthickness=1, highlightbackground="#cbd5e1")
        self.canvas.pack(fill="both", expand=True, pady=10)
        self.status = ttk.Label(frame, text="Select a port and connect", wraplength=840)
        self.status.pack(anchor="w")
        self.refresh()
        self.update_controls()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.after_id = root.after(50, self.poll)

    def refresh(self):
        ports = ["Demo"] if self.demo else [p.device for p in list_ports.comports()]
        self.port["values"] = ports
        if self.port.get() not in ports:
            self.port.set(ports[0] if ports else "")

    def connect(self):
        if self.source:
            self.disconnect("Disconnected; recording stopped")
            return
        if not self.port.get():
            messagebox.showerror("Connection", "Select an available port first.")
            return
        try:
            self.source = self.source_factory(self.port.get())
        except (serial.SerialException, OSError) as exc:
            messagebox.showerror("Connection", str(exc))
            return
        self.session = Acquisition("simulated" if self.demo else "serial")
        self.buffer = LineBuffer()
        self.points.clear()
        self.status.config(text="Connected; waiting for data. The board may restart on connection.")
        self.update_controls()

    def disconnect(self, reason):
        self.session.invalidate(reason)
        if self.source:
            try:
                self.source.close()
            except (serial.SerialException, OSError):
                pass
        self.source = None
        self.buffer = LineBuffer()
        self.points.clear()
        self.render()

    def background(self):
        try:
            if not self.source:
                raise ValueError("Connect first")
            self.source.clear()
            self.buffer = LineBuffer()
            self.session.begin_background(time.monotonic())
            self.points.clear()
        except (serial.SerialException, OSError) as exc:
            self.disconnect("Connection lost")
            messagebox.showerror("Background", str(exc))
        except ValueError as exc:
            messagebox.showerror("Background", str(exc))
        self.render()

    def record(self):
        if self.session.recorder:
            try:
                self.session.stop_recording()
                self.session.message = "Recording saved; live monitoring continues"
            except OSError as exc:
                self.session.message = "File close failed; check the CSV"
                messagebox.showerror("Recording", str(exc))
        else:
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
                                               initialfile=time.strftime("pressure_%Y%m%d_%H%M%S.csv"))
            if path:
                try:
                    self.session.start_recording(path, time.monotonic())
                except FileExistsError:
                    messagebox.showerror("Recording", "Choose a new filename. Existing files are never overwritten.")
                except (ValueError, OSError) as exc:
                    messagebox.showerror("Recording", str(exc))
        self.render()

    def poll(self):
        if self.closed:
            return
        now = time.monotonic()
        if self.source:
            try:
                lines = self.buffer.feed(self.source.read())
                for line in lines:
                    old_baseline = self.session.baseline
                    result = self.session.accept(line, now)
                    if self.session.baseline != old_baseline or result is None and self.session.latest is None:
                        self.points.clear()
                    if result:
                        seconds, sample = result
                        self.points.append((seconds, sample.pressure_mbar))
                self.session.tick(now)
                if self.session.latest is None:
                    self.points.clear()
            except (serial.SerialException, OSError):
                self.disconnect("Serial connection lost; recording stopped. Reconnect and measure background again.")
        self.render()
        self.after_id = self.root.after(50, self.poll)

    def update_controls(self):
        connected = self.source is not None
        session = self.session
        fresh = connected and session.fresh(time.monotonic())
        busy = session.background_until is not None
        self.connect_button.config(text="Disconnect" if connected else "Connect")
        self.port.config(state="disabled" if connected else "readonly")
        self.refresh_button.config(state="disabled" if connected else "normal")
        self.background_button.config(state="normal" if fresh and not busy and not session.recorder else "disabled")
        self.record_button.config(text="Stop recording" if session.recorder else "Start recording…",
                                  state="normal" if session.recorder or fresh and session.baseline is not None and not busy else "disabled")

    def render(self):
        self.update_controls()
        session = self.session
        if session.latest:
            sample = session.latest
            corrected = "—" if session.baseline is None else f"{sample.pressure_mbar - session.baseline:.3f} mbar"
            self.reading.config(text=f"Corrected: {corrected}    Raw: {sample.pressure_mbar:.3f} mbar    {sample.temperature_c:.2f} °C")
        else:
            self.reading.config(text="Waiting for valid live data")
        if session.background_until is not None:
            remaining = max(0, session.background_until - time.monotonic())
            self.baseline_label.config(text=f"Measuring background: {remaining:.1f} s remaining • {session.background_count} samples")
        else:
            self.baseline_label.config(text="Background: not measured" if session.baseline is None else
                                       f"Background: {session.baseline:.6f} mbar • {session.baseline_count} samples")
        self.status.config(text=session.message)
        self.draw_plot()

    def draw_plot(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 120)
        left, right, top, bottom = 72, width - 20, 28, height - 42
        baseline = self.session.baseline
        canvas.create_text(left, 14, anchor="w", text="Raw pressure (mbar)" if baseline is None else "Background-corrected pressure (mbar)")
        canvas.create_line(left, top, left, bottom, right, bottom, fill="#64748b")
        canvas.create_text((left + right) / 2, height - 12, text="Time since first valid sample (s)")
        if not self.points or self.session.latest is None:
            return
        points = [(t, p - (baseline or 0)) for t, p in self.points]
        t0, t1 = points[0][0], max(points[-1][0], points[0][0] + 0.1)
        low, high = min(p for _, p in points), max(p for _, p in points)
        margin = max(0.1, (high - low) * 0.1)
        low, high = low - margin, high + margin
        for i in range(5):
            value = low + (high - low) * i / 4
            y = bottom - (bottom - top) * i / 4
            canvas.create_line(left, y, right, y, fill="#e2e8f0")
            canvas.create_text(left - 8, y, text=f"{value:.2f}", anchor="e")
        for i in range(5):
            x = left + (right - left) * i / 4
            canvas.create_text(x, bottom + 14, text=f"{t0 + (t1 - t0) * i / 4:.1f}")
        coords = []
        for t, value in points:
            coords.extend((left + (t - t0) / (t1 - t0) * (right - left),
                           bottom - (value - low) / (high - low) * (bottom - top)))
        if len(coords) >= 4:
            canvas.create_line(*coords, fill="#0369a1", width=2)

    def close(self):
        self.closed = True
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.disconnect("Closed")
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="AMS5915 pressure and temperature logger")
    parser.add_argument("--demo", action="store_true", help="Use explicitly labelled synthetic readings")
    args = parser.parse_args()
    root = tk.Tk()
    PressureApp(root, demo=args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
