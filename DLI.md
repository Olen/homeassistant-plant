# Daily Light Integral (DLI) Calculation

This document explains how the Daily Light Integral (DLI) is calculated in this integration.

## What is DLI?

DLI measures the total amount of photosynthetically active radiation (PAR) received by a plant during a 24-hour period. It is expressed in moles of photons per square meter per day (mol/m²/d). DLI is a critical metric for plant growth, as it directly affects photosynthesis rates.

Typical DLI values:
- Low light plants (ferns, some houseplants): 4-6 mol/m²/d
- Medium light plants: 6-12 mol/m²/d
- High light plants (tomatoes, peppers): 12-30 mol/m²/d
- Full sun conditions: 30-60 mol/m²/d

## Calculation Pipeline

The DLI calculation involves three sensor entities working together:

```
Illuminance (lux) → PPFD (mol/m²/s) → Total Integral (mol/m²) → Daily Light Integral (mol/m²/d)
```

### Step 1: Lux to PPFD Conversion

**Sensor:** `PlantCurrentPpfd`

PPFD (Photosynthetic Photon Flux Density) measures the number of photosynthetically active photons hitting a surface per second. The integration converts illuminance (lux) to PPFD using the following formula:

```
PPFD = lux × 0.0185 / 1,000,000
```

Where:
- `0.0185` is the conversion factor from lux to μmol/m²/s for sunlight
- Division by `1,000,000` converts from micromoles (μmol) to moles (mol)

This produces PPFD in mol/m²/s.

#### Conversion Factor

The conversion factor of `0.0185` is an approximation that works well for natural sunlight. The actual conversion varies by light source:

| Light Source | Conversion Factor (μmol/m²/s per lux) |
|--------------|---------------------------------------|
| Sunlight     | ~0.0185                               |
| Metal Halide | ~0.014                                |
| Fluorescent  | ~0.013-0.014                          |
| LED          | Varies by spectrum                    |

References:
- https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
- https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3

### Step 2: Time Integration

**Sensor:** `PlantTotalLightIntegral`

This sensor uses Home Assistant's built-in `IntegrationSensor` to integrate the PPFD value over time using the trapezoidal method:

```
Total Light = ∫ PPFD dt
```

The integration is performed in seconds, so the result is in mol/m² (mol/m²/s × seconds = mol/m²).

This sensor tracks the cumulative light received since the integration was created. It does not reset automatically.

### Step 3: Daily Metering

**Sensor:** `PlantDailyLightIntegral`

This sensor uses Home Assistant's `UtilityMeterSensor` to track the daily accumulation. It:

1. Monitors the Total Light Integral sensor
2. Resets at midnight each day
3. Reports the difference (light accumulated that day)

The result is the DLI in mol/m²/d.

## Daily Reset Behavior

The DLI sensor resets to zero at midnight each day. This is the standard and correct way to measure DLI, as it represents the total light received during a single 24-hour photoperiod. The daily reset allows you to:

- Compare light levels across different days
- Track seasonal changes in light availability
- Ensure plants receive adequate light each day

This behavior matches how DLI is measured in professional horticulture and research settings.

## DLI Alerts and Thresholds

DLI alerts are intentionally based on **yesterday's DLI value**, not today's current accumulation. This prevents false alerts from being triggered when the sensor resets to zero at midnight.

The integration uses the `last_period` attribute from the utility meter sensor, which stores the final DLI value from the previous day. The threshold check in `__init__.py` (around line 740) compares this value against the configured min/max thresholds:

```python
# Check DLI from the previous day against max/min DLI
if float(self.dli.extra_state_attributes["last_period"]) < float(self.min_dli.state):
    self.dli_status = STATE_LOW
elif float(self.dli.extra_state_attributes["last_period"]) > float(self.max_dli.state):
    self.dli_status = STATE_HIGH
```

This means:
- At midnight, the DLI sensor resets to 0, but no alert is triggered
- The alert status reflects whether yesterday's complete DLI was within the acceptable range
- You get a meaningful assessment based on a full day's light, not a partial day

## Example Calculation

For a plant receiving 50,000 lux of sunlight for 10 hours:

1. **PPFD Conversion:**
   ```
   PPFD = 50,000 × 0.0185 / 1,000,000
        = 0.000925 mol/m²/s
   ```

2. **Daily Integration:**
   ```
   DLI = 0.000925 mol/m²/s × 10 hours × 3600 seconds/hour
       = 33.3 mol/m²/d
   ```

This value (33.3 mol/m²/d) represents a bright sunny day, which is appropriate for high-light plants.

## Limitations

1. **Light Source Dependency:** The conversion factor is optimized for sunlight. Indoor plants under artificial lighting may have less accurate DLI readings depending on the light spectrum.

2. **Sensor Accuracy:** The accuracy of the DLI calculation depends on the accuracy of the illuminance sensor being used.

3. **Sampling Rate:** The trapezoidal integration method assumes linear changes between samples. Rapidly changing light conditions with slow sensor updates may introduce small errors.

## Entity Visibility

The intermediate sensors (`PlantCurrentPpfd` and `PlantTotalLightIntegral`) are hidden by default as they are diagnostic entities. Only the final `PlantDailyLightIntegral` sensor is visible by default, as it provides the actionable DLI value for plant care decisions.
