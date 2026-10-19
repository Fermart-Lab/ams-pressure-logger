# AMS pressure logger

Arduino acquisition and a Python desktop application for an **AMS5915-0100-D differential pressure sensor (0–100 mbar)**. Maintained by [JGFermart](https://github.com/JGFermart) for Fermart Lab.

Measure a background, follow pressure changes live, and save both the original readings and the background-corrected values to CSV. The sensor model is taken from the original project configuration; confirm the complete part number and voltage variant on the installed hardware.

## Measure background, then record

1. Connect to the Arduino's serial port. Live pressure and temperature readings appear automatically.
2. Establish the background condition you want to subtract. For a zero differential reference, expose both pressure ports to the same pressure.
3. Click **Measure background (5 s)** and keep the background stable. The application averages the valid readings collected during those five seconds; at least ten are required.
4. The corrected display and graph show **measured pressure − measured background**. There is no fixed additive offset.
5. Click **Start recording…** and choose a new CSV filename. **Stop recording** saves the file while live monitoring continues.

The background is fixed during a recording. To measure it again, stop the recording and press the background button. Reconnecting, a detected board reset, malformed sensor data or a two-second data timeout clears the background and stops recording. Existing files are never overwritten.

## Install the desktop application

Use Python **3.10 or newer** with Tkinter. Tested with Python 3.12 on Windows.

```sh
python -m venv .venv
```

Activate the environment:

```text
Windows PowerShell: .venv\Scripts\Activate.ps1
macOS / Linux:      source .venv/bin/activate
```

Then install and launch:

```sh
python -m pip install -r requirements.txt
python PressureSensorGraph.py
```

Tkinter is included with standard Python installers for Windows. On Linux, install your distribution's Tkinter package if `python -m tkinter` fails. The only external Python dependency is **pySerial 3.5**. Close other serial monitors before connecting.

To try the interface without hardware:

```sh
python PressureSensorGraph.py --demo
```

Demo mode is labelled **SIMULATED DATA** in the window and records `source=simulated` in every CSV row.

## Install the Arduino firmware

1. Check the [wiring and sensor configuration](docs/hardware.md).
2. Open [firmware/PressureSensor/PressureSensor.ino](firmware/PressureSensor/PressureSensor.ino), keeping `Conversion.h` alongside it.
3. Select **Arduino Uno** with **Arduino AVR Boards 1.8.6**, compile and upload.
4. Close Arduino Serial Monitor, launch the desktop application and connect at the configured **9600 baud**.

The firmware reads pressure and temperature through Arduino's bundled `Wire` library. It does not require the old missing `AMS5915.h` library. Upload this firmware to remove the former `+0.71 mbar` correction; changing only the desktop application does not remove an offset already added on the board.

## Files and documentation

| File | Purpose |
| --- | --- |
| `PressureSensorGraph.py` | Desktop launcher |
| `pressure_logger/app.py` | Interface, live graph and serial connection |
| `pressure_logger/core.py` | Parsing, time conversion, background and recording |
| `firmware/PressureSensor/` | Arduino firmware and sensor conversion |
| [docs/hardware.md](docs/hardware.md) | Wiring and firmware settings |
| [docs/data-format.md](docs/data-format.md) | Serial records, CSV columns and baseline semantics |
| [docs/validation.md](docs/validation.md) | Test results and bench checks |
| [docs/provenance.md](docs/provenance.md) | Original source and repairs |
| [examples/synthetic.csv](examples/synthetic.csv) | Clearly identified synthetic recording |

## Validation and license

The regression suite checks background subtraction, serial framing, recording, reconnects, clock rollover and error handling. Sensor conversions have synthetic checks against the manufacturer's formulas, and the firmware compiles for Arduino UNO. **Physical sensor operation and measurement accuracy still require bench validation.** See [validation](docs/validation.md).

Code and original documentation use the [MIT license](LICENSE). Linked manufacturer materials and external dependencies retain their own licenses.
