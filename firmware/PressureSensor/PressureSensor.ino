// Maintainer: JGFermart. AMS5915-0100-D acquisition without an additive offset.
#include <Wire.h>
#include "Conversion.h"

constexpr uint8_t SENSOR_ADDRESS = 0x28;
constexpr float PRESSURE_MIN_MBAR = 0.0f;
constexpr float PRESSURE_MAX_MBAR = 100.0f;
constexpr uint32_t SAMPLE_INTERVAL_MS = 100;
uint32_t lastSampleAt = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Wire.setClock(100000);
#if defined(WIRE_HAS_TIMEOUT)
  Wire.setWireTimeout(25000, true);
#endif
  delay(50);
  Serial.println(F("# AMS pressure logger; ms,temperature_c,pressure_mbar; offset=0"));
  lastSampleAt = millis();
}

void loop() {
  const uint32_t now = millis();
  if (static_cast<uint32_t>(now - lastSampleAt) < SAMPLE_INTERVAL_MS) return;
  lastSampleAt = now;
#if defined(WIRE_HAS_TIMEOUT)
  Wire.clearWireTimeoutFlag();
#endif
  const uint8_t received = Wire.requestFrom(SENSOR_ADDRESS, static_cast<uint8_t>(4));
  bool failed = received != 4 || Wire.available() != 4;
#if defined(WIRE_HAS_TIMEOUT)
  failed = failed || Wire.getWireTimeoutFlag();
#endif
  if (failed) {
    while (Wire.available()) Wire.read();
    Serial.println(F("ERR,I2C_READ"));
    return;
  }
  uint8_t data[4];
  for (uint8_t i = 0; i < 4; ++i) data[i] = Wire.read();
  const Reading reading = decodeReading(data, PRESSURE_MIN_MBAR, PRESSURE_MAX_MBAR);
  Serial.print(now);
  Serial.print(',');
  Serial.print(reading.temperatureC, 4);
  Serial.print(',');
  Serial.println(reading.pressureMbar, 4);
}
