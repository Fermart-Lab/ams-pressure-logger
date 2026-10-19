"""Tk integration checks with an injected serial source. Maintainer: JGFermart."""
import csv
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from pressure_logger.app import PressureApp


class FakeSource:
    def __init__(self):
        self.payload = b""
        self.closed = False
    def read(self):
        result, self.payload = self.payload, b""
        return result
    def clear(self):
        self.payload = b""
    def close(self):
        self.closed = True


class AppTests(unittest.TestCase):
    def test_background_record_stop_reconnect_and_partial_data(self):
        root = tk.Tk()
        root.withdraw()
        sources = []
        def factory(port):
            sources.append(FakeSource())
            return sources[-1]
        app = PressureApp(root, demo=True, source_factory=factory)
        try:
            with patch("pressure_logger.app.time.monotonic") as now:
                now.return_value = 0
                app.connect()
                sources[-1].payload = b"0,23,10\n"
                app.poll()
                app.background()
                for i in range(1, 51):
                    now.return_value = i / 10
                    sources[-1].payload = f"{i*100},23,10\n".encode()
                    app.poll()
                self.assertEqual(app.session.baseline, 10)
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "test.csv"
                    with patch("pressure_logger.app.filedialog.asksaveasfilename", return_value=str(output)):
                        app.record()
                    now.return_value = 5.1
                    sources[-1].payload = b"5100,23,"
                    app.poll()
                    self.assertEqual(app.session.recorder.rows, 0)
                    sources[-1].payload = b"12\n"
                    app.poll()
                    self.assertIn("2.000 mbar", app.reading.cget("text"))
                    app.record()
                    self.assertFalse(sources[-1].closed)
                    self.assertIsNone(app.session.recorder)
                    with output.open() as file:
                        row = next(csv.DictReader(file))
                    self.assertEqual(float(row["pressure_corrected_mbar"]), 2)
                app.connect()  # Disconnect via the same UI control.
                self.assertTrue(sources[-1].closed)
                app.connect()
                self.assertEqual(len(sources), 2)
                self.assertIsNone(app.session.baseline)
                self.assertEqual(str(app.record_button["state"]), "disabled")
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
