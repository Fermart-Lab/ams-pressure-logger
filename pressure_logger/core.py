"""Acquisition, baseline measurement and CSV recording. Maintainer: JGFermart."""

import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    device_ms: int
    temperature_c: float
    pressure_mbar: float


def parse_sample(line):
    """Parse the original three-column protocol without inventing error values."""
    if not line.strip() or line.startswith("#"):
        return None
    parts = line.split(",")
    if len(parts) != 3:
        raise ValueError("Invalid sensor record")
    try:
        timestamp = int(parts[0])
        temperature, pressure = map(float, parts[1:])
    except ValueError as exc:
        raise ValueError("Invalid sensor record") from exc
    if not 0 <= timestamp < 2**32:
        raise ValueError("Invalid device timestamp")
    if not (math.isfinite(temperature) and math.isfinite(pressure)):
        raise ValueError("Non-finite sensor value")
    if not -50 <= temperature <= 150 or abs(pressure) > 1_000_000:
        raise ValueError("Sensor value outside supported numerical limits")
    return Sample(timestamp, temperature, pressure)


class LineBuffer:
    """Keep partial serial records until newline; discard oversized records whole."""
    def __init__(self):
        self.pending = bytearray()
        self.discarding = False

    def feed(self, data):
        lines = []
        for byte in data:
            if byte == 10:
                if not self.discarding:
                    try:
                        lines.append(self.pending.decode("ascii").strip())
                    except UnicodeDecodeError:
                        lines.append("ERR,ENCODING")
                self.pending.clear()
                self.discarding = False
            elif not self.discarding:
                self.pending.append(byte)
                if len(self.pending) > 160:
                    self.pending.clear()
                    self.discarding = True
                    lines.append("ERR,RECORD_TOO_LONG")
        return lines


class DeviceClock:
    def __init__(self):
        self.previous = None
        self.elapsed_ms = 0

    def update(self, timestamp):
        if self.previous is not None:
            delta = (timestamp - self.previous) % 2**32
            if delta == 0 or delta >= 2**31:
                raise ValueError("Device clock restarted or record arrived out of order")
            self.elapsed_ms += delta
        self.previous = timestamp
        return self.elapsed_ms / 1000.0


class Recorder:
    COLUMNS = ("source", "device_time_ms", "elapsed_s", "temperature_c",
               "pressure_mbar", "baseline_mbar", "pressure_corrected_mbar")

    def __init__(self, path, baseline, source):
        if not math.isfinite(baseline):
            raise ValueError("A finite baseline is required")
        self.baseline = baseline
        self.source = source
        self.first_time = None
        self.rows = 0
        self.file = Path(path).open("x", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        try:
            self.writer.writerow(self.COLUMNS)
            self.file.flush()
        except OSError:
            self.file.close()
            raise

    def write(self, sample, seconds):
        if self.first_time is None:
            self.first_time = seconds
        self.writer.writerow((self.source, sample.device_ms,
                              f"{seconds - self.first_time:.3f}",
                              f"{sample.temperature_c:.4f}",
                              f"{sample.pressure_mbar:.4f}",
                              f"{self.baseline:.6f}",
                              f"{sample.pressure_mbar - self.baseline:.6f}"))
        self.file.flush()
        self.rows += 1

    def close(self):
        self.file.close()


class Acquisition:
    BACKGROUND_SECONDS = 5.0
    MIN_BACKGROUND_SAMPLES = 10
    STALE_SECONDS = 2.0

    def __init__(self, source="serial"):
        self.source = source
        self.clock = DeviceClock()
        self.latest = None
        self.last_received = None
        self.baseline = None
        self.baseline_count = 0
        self.background_until = None
        self.background_sum = 0.0
        self.background_count = 0
        self.recorder = None
        self.message = "Waiting for sensor data"

    def fresh(self, now):
        return self.last_received is not None and now - self.last_received < self.STALE_SECONDS

    def stop_recording(self):
        recorder, self.recorder = self.recorder, None
        if recorder:
            recorder.close()

    def invalidate(self, reason):
        try:
            self.stop_recording()
        except OSError:
            reason += "; file close failed — check the saved CSV"
        self.latest = None
        self.last_received = None
        self.baseline = None
        self.baseline_count = 0
        self.background_until = None
        self.background_count = 0
        self.message = reason

    def begin_background(self, now):
        if self.recorder:
            raise ValueError("Stop recording before measuring background")
        if not self.fresh(now):
            raise ValueError("Wait for live sensor readings")
        self.baseline = None
        self.baseline_count = 0
        self.background_sum = 0.0
        self.background_count = 0
        self.background_until = now + self.BACKGROUND_SECONDS
        self.message = "Measuring background for five seconds"

    def tick(self, now):
        if self.last_received is not None and not self.fresh(now):
            self.invalidate("No data for two seconds; recording stopped. Measure background again.")
        if self.background_until is not None and now >= self.background_until:
            self.background_until = None
            if self.background_count >= self.MIN_BACKGROUND_SAMPLES:
                self.baseline = self.background_sum / self.background_count
                self.baseline_count = self.background_count
                self.message = f"Background measured from {self.baseline_count} samples"
            else:
                self.message = "Too few samples; measure background again"

    def accept(self, line, now):
        self.tick(now)
        try:
            sample = parse_sample(line)
            if sample is None:
                # The firmware's startup marker explicitly identifies a device reset.
                if line.startswith("# AMS pressure logger") and self.latest is not None:
                    self.invalidate("Device restarted; measure background again")
                    self.clock = DeviceClock()
                return None
            seconds = self.clock.update(sample.device_ms)
        except ValueError as exc:
            self.invalidate(str(exc) + "; recording stopped. Measure background again.")
            self.clock = DeviceClock()
            return None
        self.latest = sample
        self.last_received = now
        if self.background_until is not None:
            self.background_sum += sample.pressure_mbar
            self.background_count += 1
        if self.recorder:
            try:
                self.recorder.write(sample, seconds)
            except OSError:
                self.invalidate("CSV write failed; recording stopped. Check disk space and file permissions.")
                return None
        return seconds, sample

    def start_recording(self, path, now):
        if self.recorder:
            raise ValueError("Already recording")
        if self.baseline is None or self.background_until is not None or not self.fresh(now):
            raise ValueError("Measure background with live data before recording")
        self.recorder = Recorder(path, self.baseline, self.source)
        self.message = "Recording"
