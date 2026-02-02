# ☀️ Daily Light Integral (DLI) — Technical Details

This document explains how the Daily Light Integral (DLI) is calculated in the Plant Monitor integration.

---

## 📑 Table of Contents

- [☀️ Daily Light Integral (DLI) — Technical Details](#️-daily-light-integral-dli--technical-details)
  - [🌱 What is DLI?](#-what-is-dli)
  - [🔬 Calculation Pipeline](#-calculation-pipeline)
  - [🔧 Configuring the Conversion Factor](#-configuring-the-conversion-factor)
  - [🕛 Daily Reset Behavior](#-daily-reset-behavior)
  - [🚨 DLI Alerts and Thresholds](#-dli-alerts-and-thresholds)
  - [📐 Example Calculation](#-example-calculation)
  - [🔍 Troubleshooting Low DLI Values](#-troubleshooting-low-dli-values)
  - [⚠️ Limitations](#️-limitations)
  - [👁️ Entity Visibility](#️-entity-visibility)
  - [🔄 Rolling 24-Hour DLI (Alternative)](#-rolling-24-hour-dli-alternative)

---

## 🌱 What is DLI?

DLI measures the total amount of photosynthetically active radiation (PAR) received by a plant during a 24-hour period. It is expressed in **moles of photons per square meter per day** (mol/m²/d). DLI is a critical metric for plant growth, as it directly affects photosynthesis rates.

| Category | Typical DLI (mol/m²/d) | Examples |
|----------|----------------------|----------|
| 🌿 Low light | 4–6 | Ferns, some houseplants |
| 🪴 Medium light | 6–12 | Most tropical houseplants |
| 🌶️ High light | 12–30 | Tomatoes, peppers |
| ☀️ Full sun | 30–60 | Outdoor crops in summer |

---

## 🔬 Calculation Pipeline

The DLI calculation involves three sensor entities working together:

```
Illuminance (lux) → PPFD (mol/m²/s) → Total Integral (mol/m²) → Daily Light Integral (mol/m²/d)
```

### Step 1: Lux to PPFD Conversion

**Sensor:** `PlantCurrentPpfd`

PPFD (Photosynthetic Photon Flux Density) measures the number of photosynthetically active photons hitting a surface per second. The conversion formula:

```
PPFD = lux × factor / 1,000,000
```

Where:
- `factor` is the conversion factor (default `0.0185` for sunlight)
- Division by `1,000,000` converts from micromoles (μmol) to moles (mol)

### Step 2: Time Integration

**Sensor:** `PlantTotalLightIntegral`

Uses Home Assistant's built-in `IntegrationSensor` to integrate PPFD over time (trapezoidal method):

```
Total Light = ∫ PPFD dt
```

The result is in mol/m² (cumulative, does not reset automatically).

### Step 3: Daily Metering

**Sensor:** `PlantDailyLightIntegral`

Uses Home Assistant's `UtilityMeterSensor` to track daily accumulation:

1. Monitors the Total Light Integral sensor
2. Resets at midnight each day
3. Reports the light accumulated that day

The result is the **DLI in mol/m²/d**.

---

## 🔧 Configuring the Conversion Factor

The default factor (`0.0185`) is an approximation for natural sunlight. The actual conversion varies by light source:

| Light Source | Factor (μmol/m²/s per lux) |
|--------------|---------------------------|
| ☀️ Sunlight | ~0.0185 |
| 🔶 Metal Halide | ~0.014 |
| 🟡 HPS | ~0.013 |
| 💡 Fluorescent | ~0.013–0.014 |
| 💜 LED | ~0.014–0.020 (varies by spectrum) |

**To adjust:**
1. Go to your plant's device page
2. Find **Lux to PPFD factor** under Configuration
3. Set the value based on your light source (range: 0.001–0.1)

> [!TIP]
> If your plant is under LED grow lights, try a factor of `0.017` for more accurate readings.

**References:**
- [Apogee Instruments: PPFD to Lux Conversion](https://www.apogeeinstruments.com/conversion-ppfd-to-lux/)
- [HA Community: Light Accumulation](https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3)

---

## 🕛 Daily Reset Behavior

The DLI sensor **resets to zero at midnight** each day. This is the standard way to measure DLI in professional horticulture and research.

### Why Midnight Reset (Not Rolling 24-Hour)?

Based on scientific and horticultural sources, **midnight reset (calendar day)** is the standard approach:

<details>
<summary><strong>Official sources supporting midnight reset</strong></summary>

1. **ZENTRA Cloud** (METER Group):
   > "The time period resets daily at midnight."
   >
   > Source: https://docs.zentracloud.com/l/en/article/0fnw0xwzwh-daily-light-integral

2. **LI-COR** (scientific instrumentation):
   > "Set your start and stop time to 00:00 and set the Logging Period to 24 Hours."
   >
   > Source: https://www.licor.com/support/LI-1500/topics/calculating-DLI.html

3. **MSU Extension** (rain gauge analogy):
   > "The DLI concept is like a rain gauge — just as a rain gauge collects total rain over a period of time, so DLI measures the total amount of PAR received in a day."
   >
   > Source: https://www.canr.msu.edu/resources/daily_light_integral_defined
</details>

**Reasons:**
- 📊 **Comparability** — consistent daily boundaries for averages and trends
- 🌗 **Photoperiod alignment** — plants respond to the light/dark cycle within a calendar day
- 🧑‍🌾 **Practical use** — growers ask "did the plant get enough light today?"
- 🔬 **Research standards** — scientific studies use discrete daily windows

For a rolling alternative, see [Rolling 24-Hour DLI](#-rolling-24-hour-dli-alternative).

---

## 🚨 DLI Alerts and Thresholds

DLI alerts are based on **yesterday's DLI value**, not today's accumulation. This prevents false alerts when the sensor resets to zero at midnight.

The integration uses the `last_period` attribute from the utility meter sensor:

```python
# Check DLI from the previous day against max/min DLI
if float(self.dli.extra_state_attributes["last_period"]) < float(self.min_dli.state):
    self.dli_status = STATE_LOW
elif float(self.dli.extra_state_attributes["last_period"]) > float(self.max_dli.state):
    self.dli_status = STATE_HIGH
```

This means:
- At midnight, the DLI resets to 0 but **no alert is triggered**
- Alert status reflects whether yesterday's **complete** DLI was within range
- You get a meaningful assessment based on a full day's light

---

## 📐 Example Calculation

A plant receiving **50,000 lux** of sunlight for **10 hours**:

1. **PPFD:**
   ```
   PPFD = 50,000 × 0.0185 / 1,000,000 = 0.000925 mol/m²/s
   ```

2. **DLI:**
   ```
   DLI = 0.000925 × 10 × 3,600 = 33.3 mol/m²/d
   ```

This represents a bright sunny day — appropriate for high-light plants like tomatoes.

---

## 🔍 Troubleshooting Low DLI Values

Many users report DLI values that seem too low. Before assuming a calculation error, consider these common causes:

### 📍 Sensor Placement

The most common issue. A sensor at soil level or under the canopy receives far less light than the top of the plant.

> [!TIP]
> Temporarily move the sensor to the top of the plant to compare readings.

### 📏 Sensor Accuracy and Range

Many inexpensive sensors (Xiaomi Mi Flora, etc.) have limited accuracy:
- May max out at 10,000 lux (full sunlight is 50,000–100,000+ lux)
- May underreport at high levels
- Calibration varies between units

### 🏠 Indoor Light Levels Are Lower Than Expected

Even a "bright" indoor spot receives far less light than outdoors:

| Location | Typical Lux |
|----------|-------------|
| ☀️ Direct summer sunlight | 50,000–100,000+ |
| ☁️ Overcast day outdoors | 10,000–25,000 |
| 🪟 Bright window (direct sun) | 10,000–25,000 |
| 🪟 Bright window (indirect) | 2,000–5,000 |
| 💡 Well-lit room | 300–500 |
| 🏠 Typical indoor ambient | 50–200 |

**Example:** 5,000 lux for 10 hours = **3.33 mol/m²/d** — far below what most plants need.

### 🪟 Windows Filter Light

Glass blocks 20–50% of light. UV-filtering or tinted windows block even more.

### 📅 Day Length and Weather

- Winter days are shorter with a lower sun angle
- Cloudy periods reduce light significantly
- The sensor integrates *all* light, including low-light periods

### 💡 Lux-to-PPFD Factor

If using LED grow lights, adjust the **Lux to PPFD factor** entity. See [Configuring the Conversion Factor](#-configuring-the-conversion-factor).

### Debugging Steps

1. **Check illuminance sensor history** — reporting throughout the day, or gaps?
2. **Enable the PPFD sensor** — verify it shows reasonable values
3. **Check Total Light Integral** — is it accumulating?
4. **Compare sensor placement** — move to where the plant actually receives light
5. **Verify sensor range** — if maxing at 10,000 lux, that's a sensor limitation

### Reality Check

Most indoor plants without grow lights receive **1–5 DLI**, even in "bright" locations. This is why plants grow slowly indoors, lean toward windows, and supplemental grow lights make such a difference.

If your DLI seems low, it may simply be accurate.

---

## ⚠️ Limitations

1. **Light Source Dependency** — The default conversion factor is for sunlight. Adjust the [Lux to PPFD factor](#-configuring-the-conversion-factor) for artificial lighting.

2. **Sensor Accuracy** — DLI accuracy depends on the illuminance sensor. Consumer-grade sensors have limited range.

3. **Sampling Rate** — The trapezoidal integration assumes linear changes between samples. For typical sensors reporting every 10–15 minutes, this is negligible.

---

## 👁️ Entity Visibility

| Entity | Default | Purpose |
|--------|---------|---------|
| PPFD | Hidden (diagnostic) | Intermediate calculation |
| Total Light Integral | Hidden (diagnostic) | Cumulative light sum |
| **Daily Light Integral** | **Visible** | The actionable DLI value |
| DLI (24h rolling) | Hidden | Alternative rolling window |

Hidden entities can be enabled in the entity settings on the device page.

---

## 🔄 Rolling 24-Hour DLI (Alternative)

For users who prefer a rolling window instead of midnight reset, an additional sensor is available: **DLI (24h rolling)**.

This sensor:
- Shows total light accumulated in the **last 24 hours** from any point in time
- Does **not** reset at midnight
- Uses Home Assistant's statistics sensor with the "change" characteristic
- Is **hidden** by default

### When to Use Each Sensor

| Sensor | Best For |
|--------|----------|
| **Daily Light Integral** (midnight reset) | Standard DLI tracking, comparing days, matching literature |
| **DLI (24h rolling)** | Real-time monitoring, immediate impact of light changes |

### Enabling the Rolling Sensor

1. Go to **Settings** → **Devices & Services** → **Plant Monitor**
2. Click on your plant device
3. Find "DLI (24h rolling)" in the disabled entities
4. Enable it

> [!NOTE]
> This sensor requires 24 hours of data collection before showing meaningful values.
