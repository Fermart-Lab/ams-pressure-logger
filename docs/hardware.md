# Hardware and firmware

Maintained by JGFermart.

## Sensor wiring

For the bare AMS5915 package, use the manufacturer's [datasheet, revision 4.1](https://www.analog-micro.com/products/pressure-sensors/board-mount-pressure-sensors/ams5915/ams5915-datasheet.pdf), especially pages 7 and 12–14. Verify the package orientation and the full ordering code before wiring.

| Sensor pin | Function | Connection |
| --- | --- | --- |
| 1 | GND | Common ground |
| 2 | VCC | Supply appropriate to the voltage variant |
| 3 | SDA | Arduino UNO SDA/A4, through level translation where needed |
| 4 | SCL | Arduino UNO SCL/A5, through level translation where needed |
| 5–8 | Unconnected | Leave unconnected |

The 3.3 V and 5 V variants have different supply requirements. A bare 3.3 V sensor should use a bidirectional I²C level shifter with a 5 V UNO; pull-ups on each side must match that side's voltage. The datasheet recommends 4.7 kΩ pull-ups. A breakout may already provide translation and pull-ups: check its schematic.

The configured `0100-D` model measures 0–100 mbar differential pressure. Follow the datasheet's port orientation, rated range and media-compatibility requirements. Its temperature channel measures sensor temperature.

## Firmware configuration

Defaults in `PressureSensor.ino`:

| Constant | Value |
| --- | --- |
| `SENSOR_ADDRESS` | `0x28` |
| `PRESSURE_MIN_MBAR` | `0.0` |
| `PRESSURE_MAX_MBAR` | `100.0` |
| `SAMPLE_INTERVAL_MS` | `100` |
| Serial speed | `9600` baud |
| I²C clock | `100000` Hz |

These are software settings, not an automatic identification of the connected sensor. Edit the pressure limits if using a different range. `D` and `D-B` are different variants.

The firmware requests four bytes directly, without a channel-selection write. `Conversion.h` uses the pressure word's lower 14 bits and the temperature word's upper 11 bits. Conversion follows datasheet page 11:

```text
pressure_mbar = (pressure_counts - 1638) * (maximum - minimum) / 13107 + minimum
temperature_c = temperature_counts * 200 / 2048 - 50
```

No user offset is added. The desktop application performs measured-background subtraction. Values near the range boundaries are not clipped; inspect raw readings when validating zero and span.

Incomplete reads emit an error record instead of a numeric zero. On the tested AVR core, an I²C timeout is enabled at 25 ms with bus reset. Other board cores may not implement `WIRE_HAS_TIMEOUT`; they have not been validated.
