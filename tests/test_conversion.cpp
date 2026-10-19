// Synthetic datasheet conversion checks. Maintainer: JGFermart.
#include <assert.h>
#include <math.h>
#include "../firmware/PressureSensor/Conversion.h"

int main() {
  const uint8_t minimum[] = {0x06, 0x66, 0, 0};
  const uint8_t maximum[] = {0x39, 0x99, 0xff, 0xe0};
  const uint8_t example[] = {0x2c, 0xcd, 0x5c, 0xe0};
  Reading r = decodeReading(minimum, 0, 100);
  assert(fabs(r.pressureMbar) < 0.0001f);
  assert(fabs(r.temperatureC + 50) < 0.0001f);
  r = decodeReading(maximum, 0, 100);
  assert(fabs(r.pressureMbar - 100) < 0.0001f);
  assert(fabs(r.temperatureC - 149.90234375f) < 0.0001f);
  r = decodeReading(example, -5, 5);
  assert(fabs(r.pressureMbar - 2.500572f) < 0.0001f);
  assert(fabs(r.temperatureC - 22.558594f) < 0.0001f);
  const uint8_t unusedBits[] = {0xec, 0xcd, 0x5c, 0xff};
  Reading masked = decodeReading(unusedBits, -5, 5);
  assert(masked.pressureMbar == r.pressureMbar);
  assert(masked.temperatureC == r.temperatureC);
}
