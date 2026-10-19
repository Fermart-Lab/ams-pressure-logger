# Validation

Maintained by JGFermart. All automated test inputs are synthetic.

## Automated checks

From the repository root, after installing `requirements.txt`:

```sh
python -m unittest discover -s tests -v
```

The Tk integration test requires a graphical session. For a headless host, run the core suite separately:

```sh
python -m unittest discover -s tests -p test_core.py -v
```

Firmware conversion checks with a C++11 compiler:

```sh
c++ -std=c++11 -Wall -Wextra -Werror tests/test_conversion.cpp -o conversion-tests
./conversion-tests
```

On Windows, name the executable `conversion-tests.exe` and run it. Assertions must remain enabled.

Compile the firmware with Arduino CLI:

```sh
arduino-cli core install arduino:avr@1.8.6
arduino-cli compile --fqbn arduino:avr:uno --warnings all firmware/PressureSensor
```

## Results — 19 October 2026

- Ten Python tests passed on Python 3.12 / Windows with pySerial 3.5, including a Tk interface test with an injected serial source.
- Baseline 10 / reading 12 yields corrected pressure 2 in the interface and CSV; the original reading and baseline remain in separate columns.
- Partial and invalid records, non-finite values, clock rollover/reset, insufficient background samples, silence, disk failure, filename protection, stop/start recording and reconnect behavior are covered.
- C++ conversion checks passed for both pressure endpoints, temperature endpoints, unused bits and the manufacturer's numerical example.
- Arduino UNO compilation passed with AVR Boards 1.8.6: 5,716 bytes flash, 386 bytes static RAM. Warnings were confined to unused parameters in the Arduino core.

No physical sensor was connected, no firmware was flashed during these checks, and no measurement accuracy is claimed from software tests.

## Bench acceptance

1. Verify the exact sensor model, voltage, wiring, pressure-port orientation and range.
2. Upload the repaired firmware and confirm stable live pressure/temperature readings.
3. Equalize the pressure ports, measure background, and confirm corrected pressure is close to zero within the sensor's observed noise.
4. Apply several known differential pressures within range using a suitable reference. Compare the raw and corrected readings; record zero/span error and repeatability.
5. Save a short CSV and compare its corrected values with the display. Stop and start a new recording without reconnecting.
6. Unplug/reconnect and reset the board. Confirm that recording stops, no error is saved as zero pressure, and background must be measured again.

Keep the bench results with the instrument's calibration records.
