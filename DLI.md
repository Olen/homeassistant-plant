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

The default conversion factor of `0.0185` is an approximation that works well for natural sunlight. The actual conversion varies by light source:

| Light Source | Conversion Factor (μmol/m²/s per lux) |
|--------------|---------------------------------------|
| Sunlight     | ~0.0185                               |
| Metal Halide | ~0.014                                |
| HPS          | ~0.013                                |
| Fluorescent  | ~0.013-0.014                          |
| LED          | ~0.014-0.020 (varies by spectrum)     |

#### Configuring the Conversion Factor

Since the conversion factor varies significantly depending on your light source, you can adjust it per plant using the **Lux to PPFD factor** entity. This is particularly useful for:

- Indoor plants under grow lights
- Plants in greenhouses with artificial supplemental lighting
- Any situation where the default sunlight factor doesn't match your light source

To adjust the factor:
1. Go to your plant's device page
2. Find the "Lux to PPFD factor" number entity under Configuration
3. Adjust the value based on your light source (see table above)

The factor can be set between 0.001 and 0.1, with a default of 0.0185.

**Example:** If you're using LED grow lights with a conversion factor of 0.017, set the "Lux to PPFD factor" to `0.017` for more accurate DLI readings.

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

### Why Midnight Reset (Not Rolling 24-Hour Window)

Some users have asked whether DLI should be a rolling 24-hour window instead of resetting at midnight. Based on research of scientific and horticultural sources, **the standard approach is midnight reset (calendar day)**.

#### Official Sources Supporting Midnight Reset

1. **ZENTRA Cloud** (METER Group environmental monitoring):
   > "The time period resets daily at midnight."

   Source: https://docs.zentracloud.com/l/en/article/0fnw0xwzwh-daily-light-integral

2. **LI-COR** (scientific instrumentation standard):
   > "In the Logging Setup, set your start and stop time to 00:00 and set the Logging Period to 24 Hours."

   > "If you capture measurements for more than one day, the DLI value will reset to zero and start again at the next configured start time."

   Source: https://www.licor.com/support/LI-1500/topics/calculating-DLI.html

3. **MSU Extension** uses the rain gauge analogy:
   > "The DLI concept is like a rain gauge. Just as a rain gauge collects the total rain in a particular location over a period of time, so DLI measures the total amount of PAR received in a day."

   Rain gauges are read and reset daily at a fixed time, not as rolling totals.

   Source: https://www.canr.msu.edu/resources/daily_light_integral_defined

#### Why Midnight Reset Makes Sense

1. **Comparability**: DLI values are often reported as monthly/seasonal averages in literature. This requires consistent daily boundaries.

2. **Photoperiod alignment**: Plants respond to the light/dark cycle within a calendar day. A rolling window would blur the distinction between days.

3. **Practical use**: Growers make decisions based on "did the plant get enough light today?" not "in the last 24 hours from this moment."

4. **Research standards**: Scientific studies define photoperiods within discrete daily windows (e.g., "7 to 22 hours of light"), implying fixed daily boundaries.

#### Scientific Literature Uses Midnight Reset

We could not find any scientific, horticultural, or equipment manufacturer documentation that recommends or uses a rolling 24-hour window for DLI measurement. This is why the primary DLI sensor uses midnight reset.

However, for users who prefer a rolling window for real-time monitoring, see [Rolling 24-Hour DLI (Alternative)](#rolling-24-hour-dli-alternative).

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

## Troubleshooting Low DLI Values

Many users report DLI values that seem too low compared to their expectations. Before assuming there's a calculation error, consider these common causes:

### 1. Sensor Placement

The most common issue. Light sensors placed at soil level or under the plant canopy receive significantly less light than the top of the plant. A sensor in the shade of leaves might read 500-2,000 lux while the top of the plant receives 10,000+ lux.

**Tip:** Temporarily move the sensor to the top of the plant to compare readings.

### 2. Sensor Accuracy and Range

Many inexpensive plant sensors (Xiaomi Mi Flora, etc.) have limited accuracy and range:
- May max out at 10,000 lux (but full sunlight is 50,000-100,000+ lux)
- May underreport, especially at high light levels
- Calibration varies between individual sensors

If your sensor reports 10,000 lux as a maximum, it may be clipping the actual light level.

### 3. Indoor Light Levels Are Lower Than Expected

This surprises many users. Even a "bright" indoor location receives far less light than outdoors:

| Location | Typical Lux |
|----------|-------------|
| Direct summer sunlight | 50,000 - 100,000+ |
| Overcast day outdoors | 10,000 - 25,000 |
| Bright window (direct sun) | 10,000 - 25,000 |
| Bright window (indirect) | 2,000 - 5,000 |
| Well-lit room | 300 - 500 |
| Typical indoor ambient | 50 - 200 |

**Example calculation:** A plant receiving 5,000 lux for 10 hours:
```
DLI = 5,000 × 0.0185 / 1,000,000 × 10 × 3600 = 3.33 mol/m²/d
```

This is far below what most plants need, yet 5,000 lux feels "bright" to humans.

### 4. Windows Filter Light

Glass windows block a significant portion of light (20-50% depending on type). UV-filtering or tinted windows block even more. Plants on windowsills receive less light than the outdoor reading would suggest.

### 5. Day Length and Weather

- Winter days are shorter and the sun is lower
- Cloudy periods significantly reduce light, even if some sunny periods feel bright
- The sensor integrates the *actual* light received, including all the low-light periods

### 6. Lux-to-PPFD Conversion Factor

The default factor (0.0185) is for sunlight. If your plant is under LED grow lights, the factor might be different (typically 0.014-0.020). Adjust the "Lux to PPFD factor" entity if needed.

### Debugging Steps

1. **Check the illuminance sensor history** - Is it reporting values throughout the day, or are there gaps?
2. **Check the PPFD sensor** - Enable the hidden `PPFD` sensor and verify it shows reasonable values
3. **Check the Total Light Integral sensor** - Is it accumulating throughout the day?
4. **Compare sensor placement** - Move the sensor to where the plant actually receives light
5. **Verify sensor range** - If your sensor maxes out at 10,000 lux, that's a sensor limitation, not a calculation error

### Reality Check

Most indoor plants without dedicated grow lights receive 1-5 DLI, even in "bright" locations. This is often below the plant's optimal range (many houseplants need 4-12 DLI). This is why:
- Plants grow slowly indoors
- Plants lean toward windows
- Supplemental grow lights make a significant difference

If your DLI seems low, it may simply be accurate - indoor light levels are genuinely much lower than outdoor levels.

## Limitations

1. **Light Source Dependency:** The default conversion factor is optimized for sunlight. Indoor plants under artificial lighting may have less accurate DLI readings depending on the light spectrum. You can adjust the "Lux to PPFD factor" per plant to compensate for different light sources (see [Configuring the Conversion Factor](#configuring-the-conversion-factor)).

2. **Sensor Accuracy:** The accuracy of the DLI calculation depends on the accuracy of the illuminance sensor being used. Many consumer-grade sensors have limited range or accuracy.

3. **Sampling Rate:** The trapezoidal integration method assumes linear changes between samples. Rapidly changing light conditions with slow sensor updates may introduce small errors. However, for typical plant sensors reporting every 10-15 minutes, this is negligible.

## Entity Visibility

The intermediate sensors (`PlantCurrentPpfd` and `PlantTotalLightIntegral`) are hidden by default as they are diagnostic entities. Only the final `PlantDailyLightIntegral` sensor is visible by default, as it provides the actionable DLI value for plant care decisions.

## Rolling 24-Hour DLI (Alternative)

For users who prefer a rolling 24-hour window instead of the midnight-reset behavior, an additional sensor is available: **DLI (24h rolling)**.

This sensor:
- Shows the total light accumulated in the **last 24 hours** from any point in time
- Does NOT reset at midnight
- Uses Home Assistant's statistics sensor with the "change" characteristic
- Is hidden by default (can be enabled in the entity settings)

### When to Use Each Sensor

| Sensor | Best For |
|--------|----------|
| **Daily Light Integral** (midnight reset) | Standard DLI tracking, comparing days, matching scientific literature |
| **DLI (24h rolling)** | Real-time monitoring, seeing immediate impact of light changes |

### How It Works

The rolling 24-hour sensor tracks the `PlantTotalLightIntegral` sensor and computes the difference between the current value and the value from 24 hours ago. This gives a continuous view of accumulated light without the discontinuity at midnight.

### Enabling the Rolling Sensor

1. Go to **Settings** → **Devices & Services** → **Plant Monitor**
2. Click on your plant device
3. Find "DLI (24h rolling)" in the disabled entities
4. Click on it and enable it

Note: This sensor requires 24 hours of data collection before it shows meaningful values.
