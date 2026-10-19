# Changelog

## 1.0.0 — 19 October 2026

Repairs and documentation by JGFermart.

- Remove the fixed pressure offset from firmware.
- Add a five-second measured background and apply subtraction consistently to display, plot and CSV.
- Preserve original readings and baseline alongside corrected values.
- Use one nonblocking serial reader in the Tk event loop.
- Keep monitoring connected when recording stops; reset background on reconnect and acquisition faults.
- Convert milliseconds to seconds and handle normal device-clock rollover.
- Replace the unavailable sensor library with explicit four-byte reads and documented conversion.
- Add error handling, protected file creation, a labelled demo and regression tests.
