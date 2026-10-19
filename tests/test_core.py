"""Regression checks maintained by JGFermart; all inputs are synthetic."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from pressure_logger.core import Acquisition, DeviceClock, LineBuffer, Recorder, Sample, parse_sample


class ProtocolTests(unittest.TestCase):
    def test_parse_and_reject_bad_records(self):
        self.assertEqual(parse_sample("100, 23.5, -0.2"), Sample(100, 23.5, -0.2))
        self.assertIsNone(parse_sample("# header"))
        self.assertIsNone(parse_sample(""))
        for line in ["ERR,I2C_READ", "Disconnected!", "1,2", "1,2,3,4", "x,2,3",
                     "-1,2,3", "4294967296,2,3", "1,nan,3", "1,2,inf", "1,200,3"]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_sample(line)

    def test_fragmented_lines_and_recovery(self):
        buf = LineBuffer()
        self.assertEqual(buf.feed(b"100,2"), [])
        self.assertEqual(buf.feed(b"3,10\r\n200,23,12\n"), ["100,23,10", "200,23,12"])
        self.assertEqual(buf.feed(b"\xff\n"), ["ERR,ENCODING"])
        self.assertEqual(buf.feed(b"x" * 161), ["ERR,RECORD_TOO_LONG"])
        self.assertEqual(buf.feed(b"1,23,99\n300,23,14\n"), ["300,23,14"])

    def test_milliseconds_seconds_rollover_and_restart(self):
        clock = DeviceClock()
        self.assertEqual(clock.update(2**32 - 100), 0)
        self.assertAlmostEqual(clock.update(0), 0.1)
        self.assertAlmostEqual(clock.update(1000), 1.1)
        with self.assertRaises(ValueError):
            clock.update(10)
        with self.assertRaises(ValueError):
            clock.update(1000)


class SessionTests(unittest.TestCase):
    def background(self, value=10):
        session = Acquisition("simulated")
        session.accept(f"0,23,{value}", 0)
        session.begin_background(0)
        for i in range(1, 50):
            session.accept(f"{i * 100},23,{value}", i / 10)
        session.tick(5)
        return session

    def test_mean_background_and_csv_regression(self):
        session = Acquisition("simulated")
        session.accept("0,23,1000", 0)  # The pre-button sample must not enter the mean.
        session.begin_background(0)
        for i in range(1, 50):
            session.accept(f"{i * 100},23,{9 if i % 2 else 11}", i / 10)
        session.tick(5)
        self.assertEqual(session.baseline_count, 49)
        self.assertAlmostEqual(session.baseline, (25 * 9 + 24 * 11) / 49)
        session = self.background(10)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.csv"
            session.start_recording(path, 5)
            session.accept("5000,24,12", 5)
            session.accept("5100,25,9", 5.1)
            with self.assertRaises(ValueError):
                session.begin_background(5.1)
            session.stop_recording()
            with path.open(encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([float(r["pressure_corrected_mbar"]) for r in rows], [2, -1])
            self.assertEqual([float(r["elapsed_s"]) for r in rows], [0, 0.1])
            self.assertEqual(float(rows[0]["pressure_mbar"]), 12)
            self.assertEqual(float(rows[0]["baseline_mbar"]), 10)
            self.assertEqual(rows[0]["source"], "simulated")
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                session.start_recording(path, 5.1)
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(session.fresh(5.2))
            session.start_recording(Path(directory) / "second.csv", 5.2)
            session.accept("5200,24,14", 5.2)
            session.stop_recording()

    def test_zero_baseline_and_rollover_during_recording(self):
        session = self.background(0)
        self.assertEqual(session.baseline, 0)
        self.assertIsNotNone(session.baseline)
        with tempfile.TemporaryDirectory() as directory:
            recorder = Recorder(Path(directory) / "wrap.csv", 0, "simulated")
            clock = DeviceClock()
            for stamp in (2**32 - 100, 0, 100):
                recorder.write(Sample(stamp, 23, 2), clock.update(stamp))
            recorder.close()
            with (Path(directory) / "wrap.csv").open() as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([float(r["elapsed_s"]) for r in rows], [0, 0.1, 0.2])

    def test_error_records_invalidate_baseline_and_stop_recording(self):
        for error in ("ERR,I2C_READ", "1,nan,2", "# AMS pressure logger; startup", "100,23,12"):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                session = self.background()
                session.start_recording(Path(directory) / "run.csv", 5)
                session.accept(error, 5)
                self.assertIsNone(session.baseline)
                self.assertIsNone(session.recorder)
                self.assertIsNone(session.latest)

    def test_silence_and_short_background_never_become_valid(self):
        session = self.background()
        session.tick(7)
        self.assertIsNone(session.baseline)
        session = Acquisition()
        with self.assertRaises(ValueError):
            session.begin_background(0)
        session.accept("0,23,10", 0)
        session.begin_background(0)
        for i in range(1, 5):
            session.accept(f"{i*1000},23,10", i)
        session.tick(5)
        self.assertIsNone(session.baseline)
        self.assertIn("Too few", session.message)

    def test_disk_failure_stops_recording(self):
        session = self.background()
        recorder = Mock()
        recorder.write.side_effect = OSError("Disk full")
        session.recorder = recorder
        self.assertIsNone(session.accept("5100,23,12", 5.1))
        self.assertIsNone(session.recorder)
        self.assertIn("CSV write failed", session.message)
        recorder.close.assert_called_once()

    def test_new_session_requires_new_background(self):
        session = Acquisition()
        session.accept("0,23,10", 0)
        with self.assertRaises(ValueError):
            session.start_recording("must-not-be-created.csv", 0)
        self.assertFalse(Path("must-not-be-created.csv").exists())


if __name__ == "__main__":
    unittest.main()
