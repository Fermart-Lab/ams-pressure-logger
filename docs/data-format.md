# Background and data formats

Maintained by JGFermart.

## Background measurement

**Measure background (5 s)** clears buffered pre-button serial data and averages the valid pressure readings received during the next five seconds. It requires at least ten samples and current incoming data. The window remains responsive. A failed measurement leaves no usable background; it never silently restores an older one.

This is a **tare/background subtraction**, not a traceable pressure calibration or span correction. Keep the reference condition stable. The background can represent zero differential pressure or another experimental starting condition; record that condition in your experiment notes.

The original pressure is the reading received from the firmware. The correction is:

```text
corrected pressure = original pressure - mean background
```

For background 10 mbar and reading 12 mbar, the corrected value is 2 mbar. Negative corrected values are allowed. The same baseline is used for the live corrected display, graph and every row in a recording. A new recording starts its elapsed time at its first saved sample.

## Serial protocol

ASCII at 9600 baud, one newline-terminated record:

```text
device_time_ms,temperature_c,pressure_mbar
5000,23.5000,12.0000
```

`device_time_ms` is the Arduino's unsigned 32-bit `millis()` value. The desktop converts differences to seconds and handles its normal rollover. Backward jumps or duplicate timestamps are rejected. The revised firmware's startup line begins `# AMS pressure logger`; seeing it during acquisition invalidates the session background. Older firmware without that marker cannot reliably identify every possible reset; use the revised firmware for new recordings.

`ERR,I2C_READ` reports an incomplete/failed read. Error messages and malformed, non-finite or unsupported numeric values stop recording and clear the background; they are not written as measurements. Partial lines are buffered until newline. The desktop limits lines to 160 bytes and discards an oversized line through its next newline. The parser accepts temperature from −50 to 150 °C and pressure magnitude up to 1,000,000 mbar as numerical limits, not physical operating limits.

## CSV columns

| Column | Meaning |
| --- | --- |
| `source` | `serial` or `simulated` |
| `device_time_ms` | Original Arduino timestamp |
| `elapsed_s` | Seconds since the first saved sample in this file |
| `temperature_c` | Sensor temperature |
| `pressure_mbar` | Original firmware pressure, before background subtraction |
| `baseline_mbar` | Measured background held constant throughout this file |
| `pressure_corrected_mbar` | Original pressure minus baseline |

Each row is flushed to the file. Existing files are protected by exclusive creation. A disk write error stops recording and is shown in the interface; the final row may be incomplete and should be checked. Stopping recording leaves monitoring connected. Disconnecting closes the recording and requires a new background after reconnecting.

The plot shows at most 600 received samples against actual device elapsed seconds. It displays raw pressure until a background is measured, then corrected pressure. Its time axis is relative to the first valid sample in the connection, while each CSV has its own recording origin. Serial timing gaps remain gaps rather than being replaced with synthetic measurements.
