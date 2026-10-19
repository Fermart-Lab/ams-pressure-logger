// Maintainer: JGFermart. Conversion follows AMS5915 datasheet rev. 4.1.
#ifndef PRESSURE_CONVERSION_H
#define PRESSURE_CONVERSION_H
#include <stdint.h>

struct Reading { float pressureMbar; float temperatureC; };

inline Reading decodeReading(const uint8_t data[4], float minimum, float maximum) {
  const uint16_t pressure = (static_cast<uint16_t>(data[0] & 0x3f) << 8) | data[1];
  const uint16_t temperature = (static_cast<uint16_t>(data[2]) << 3) | (data[3] >> 5);
  Reading result;
  result.pressureMbar = (static_cast<float>(pressure) - 1638.0f) *
                       (maximum - minimum) / 13107.0f + minimum;
  result.temperatureC = temperature * 200.0f / 2048.0f - 50.0f;
  return result;
}
#endif
