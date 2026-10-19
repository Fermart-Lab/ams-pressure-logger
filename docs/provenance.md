# Source and repair history

Maintained by [JGFermart](https://github.com/JGFermart).

This release repairs the original PressureSensor desktop logger and Arduino sketch. Original project files remain unchanged in the local source collection. The release contains the maintained implementation, documentation, tests and synthetic examples; experimental recordings, CAD files, executables, archives and local IDE settings are excluded.

## Original source fingerprints

SHA-256 identifies the source files inspected before repair:

| Source file | SHA-256 |
| --- | --- |
| `PressureSensorGraph.py` | `9497fab5ffb00d06e2eb66efc6c0f330ffd373f9e0bd56510f4b07dd84f5c91f` |
| `PressureSensor.py` | `580ba33fe5062b967722cacd858207563ead216e888fe82449dbf008833a788b` |
| `PressureSensor.ino` | `5e675151cfd6dbeb8cbc0f99a30447e24690c07e172cea055a47729b0e558600` |

## Repairs

The original graphing logger measured a baseline but wrote uncorrected pressure under a difference header. It read the same serial stream from multiple functions, updated Tk widgets from a worker thread, plotted sample indices as time, and closed the serial connection when recording stopped. The maintained application routes all serial data through one nonblocking Tk event-loop reader and explicitly records both original and corrected measurements.

The original firmware added a fixed 0.71 mbar. That correction is removed. The desktop now measures a five-second background and subtracts it; this is a background reference, not a replacement for sensor accuracy validation.

The missing `AMS5915.h` API corresponds to the [ControlEverything AMS5915 example](https://github.com/ControlEverythingCommunity/CE_ARDUINO_LIB/blob/master/AMS5915/Examples/AMS5915_0100_D/AMS5915_0100_D.ino). The bundled `AMS.h` is a different interface. Neither library is redistributed or required by this release: the firmware uses Arduino Wire and conversion formulas from the linked [manufacturer datasheet](hardware.md).

The separate SD-card prototype is not part of this release. The maintained scope is one sensor connected over I²C to an Arduino, streaming to a desktop CSV logger.

Changes and documentation by JGFermart, 19 October 2026. See [CHANGELOG.md](../CHANGELOG.md) and [validation](validation.md).
