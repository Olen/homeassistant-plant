# 🌱 Plant Monitor for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Olen/homeassistant-plant?style=for-the-badge)](https://github.com/Olen/homeassistant-plant/releases)

A comprehensive plant monitoring integration for Home Assistant that treats each plant as a **device** with its own sensors, thresholds, and health tracking. Automatically fetches species data from [OpenPlantbook](https://open.plantbook.io/docs.html) to configure optimal growing conditions.

> [!WARNING]
> This integration is **not** compatible with the original built-in plant integration in Home Assistant.

---

## 📑 Table of Contents

- [🌱 Plant Monitor for Home Assistant](#-plant-monitor-for-home-assistant)
  - [🌿 Overview](#-overview)
  - [📦 Installation](#-installation)
  - [🔧 Setup \& Configuration](#-setup--configuration)
  - [🌡️ Sensors \& Thresholds](#️-sensors--thresholds)
  - [☀️ Daily Light Integral (DLI)](#️-daily-light-integral-dli)
  - [🖼️ Plant Images](#️-plant-images)
  - [⚠️ Problem Reports](#️-problem-reports)
  - [🔄 Replacing Sensors](#-replacing-sensors)
  - [🌻 OpenPlantbook Integration](#-openplantbook-integration)
  - [🃏 Lovelace Card](#-lovelace-card)
  - [💡 Tips & Tricks](TIPS.md)
  - [❓ FAQ](#-faq)
  - [☕ Support](#-support)

---

## 🌿 Overview

Each plant is a **device** in Home Assistant, grouping all its related entities together:

![Plant device overview](https://user-images.githubusercontent.com/203184/184302443-9d9fb1f2-4b2a-48bb-a479-1cd3a6e634af.png)

**Key features:**

- 🖥️ **UI-based setup** — guided multi-step config flow with optional OpenPlantbook search
- 📊 **Per-plant thresholds** — each threshold is its own entity, adjustable from the UI or via automations
- 🌤️ **Daily Light Integral** — automatic DLI calculation from illuminance sensors
- 🔄 **Live updates** — change sensors, thresholds, species, or images without restarting HA
- 🚨 **Problem detection** — configurable per-sensor problem triggers
- 🔌 **Auto-disable** — sensors without a source entity are automatically disabled

---

## 📦 Installation

### 1. Install OpenPlantbook *(optional but recommended)*

The [OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook) automatically fetches species data, thresholds, and images. Without it, you must set all thresholds manually.

- Install from HACS or manually
- Register at [open.plantbook.io](https://open.plantbook.io/) (free)
- Add your `client_id` and `secret` in the integration config
- Test with the `openplantbook.search` action

### 2. Install the Flower Card *(optional)*

[Lovelace Flower Card v2](https://github.com/Olen/lovelace-flower-card/) is the recommended card for displaying plant data. Install via HACS or manually.

### 3. Install Plant Monitor

#### Via HACS

1. Add this repo as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/) with type **Integration**
2. Click **Install** in the "Plant Monitor" card
3. Restart Home Assistant

#### Manual Installation

1. Copy `custom_components/plant/` to your `<config>/custom_components/` directory
2. Restart Home Assistant

After restart, add plants via **Settings** → **Devices & Services** → **Add Integration** → **Plant Monitor**.

---

## 🔧 Setup & Configuration

The config flow guides you through plant setup in four steps:

### Step 1: Name & Species

Enter a name for your plant. Optionally enter a species to search OpenPlantbook.

- If OpenPlantbook is installed and a species is entered, the flow proceeds to species selection
- If no species is entered (or OpenPlantbook is not installed), the flow skips to sensor selection

### Step 2: Select Species *(OpenPlantbook only)*

If OpenPlantbook found matches, select the correct species from a dropdown list. You can also re-search with a different term if the initial results aren't right.

If the wrong species was selected, you can go back and search again.

### Step 3: Select Sensors

Choose which physical sensors to associate with your plant. All sensors are optional and can be added or changed later. Available sensor types:

| Sensor | Device Class | Description |
|--------|-------------|-------------|
| 🌡️ Temperature | `temperature` | Air temperature |
| 💧 Soil moisture | `moisture` | Soil water content |
| ⚡ Conductivity | `conductivity` | Soil nutrient level |
| ☀️ Illuminance | `illuminance` | Light level |
| 💨 Air humidity | `humidity` | Air moisture |
| 🫧 CO2 | `carbon_dioxide` | CO2 concentration |
| 🌡️ Soil temperature | `temperature` | Soil temperature |

> [!TIP]
> Sensors without a source entity are automatically disabled. You can add or replace sensors at any time after setup.

### Step 4: Set Limits

Configure min/max thresholds for each sensor type. If OpenPlantbook data is available, thresholds are pre-filled automatically. Only thresholds for sensor types selected in the previous step are shown (if no sensors were selected, all thresholds are displayed).

You can also set a custom image URL and display species name on this page.

---

## 🌡️ Sensors & Thresholds

All thresholds are their own entities and can be changed from the UI or by automations and scripts. Changes take effect immediately — no restart needed.

![Threshold entities](https://user-images.githubusercontent.com/203184/184302654-dd1f46ec-d645-4d95-b25d-7202faa944cc.png) ![Threshold config](https://user-images.githubusercontent.com/203184/184302847-8e593300-2c68-49f3-803c-8a3f5323f7f8.png)

- 🌡️ Max/min temperature adapts to your HA unit of measurement (°C or °F)
- Threshold values update automatically if you change your HA temperature units

---

## ☀️ Daily Light Integral (DLI)

A **Daily Light Integral** sensor is automatically created for each plant, measuring the total photosynthetically active light received per day.

![DLI sensor](https://user-images.githubusercontent.com/203184/183286314-91382bf5-7767-4f50-bf58-673c63282c1c.png)

See [Wikipedia: Daily Light Integral](https://en.wikipedia.org/wiki/Daily_light_integral) for background.

### Configurable Lux-to-PPFD Conversion

The DLI calculation converts illuminance (lux) to PPFD. The default factor (`0.0185`) is optimized for sunlight, but different light sources need different factors. Adjust it per plant using the **Lux to PPFD factor** entity.

For technical details on the DLI calculation pipeline, conversion factors, troubleshooting low readings, and the optional rolling 24-hour sensor, see **[DLI.md](DLI.md)**.

---

## 🖼️ Plant Images

The plant image can be set in several ways:

### From OpenPlantbook *(automatic)*

If the species is found in OpenPlantbook, the image URL is fetched automatically. The integration validates that the URL is accessible before using it. If the OpenPlantbook integration is configured to download images, the downloaded files are stored in `config/www/images/plants/` by default and referenced as `/local/images/plants/`.

### Custom Images

You can override the image with your own. Supported formats:

| Format | Example |
|--------|---------|
| **HTTP/HTTPS URL** | `https://example.com/my-plant.jpg` |
| **Local `/www/` folder** | `/local/images/plants/my-plant.jpg` (file at `config/www/images/plants/my-plant.jpg`) |
| **Media Source** | `media-source://media_source/local/plants/my-plant.jpg` |

> [!NOTE]
> - Paths are **case-sensitive** — the filename must match exactly
> - Only `media_source/local/` is supported for media source URLs
> - Media source URLs require a compatible Lovelace card (like the [Flower Card](https://github.com/Olen/lovelace-flower-card/))

---

## ⚠️ Problem Reports

By default, any sensor reading outside its configured threshold triggers a **"problem"** state on the plant. You can enable or disable problem triggers per sensor type.

Configure via **Settings** → **Devices & Services** → **Plant Monitor** → *Your Plant* → **Configure**.

![Problem trigger options](https://user-images.githubusercontent.com/203184/184301674-0461813a-a665-4e93-b5a8-7c9575fe4782.png)

---

## 🔄 Replacing Sensors

Use the `plant.replace_sensor` action to swap the physical sensor backing a plant measurement — no restart needed.

![Replace sensor](https://user-images.githubusercontent.com/203184/183286188-174dc709-173f-42fb-9d66-678d0c1f62e4.png)

```yaml
action: plant.replace_sensor
data:
  meter_entity: sensor.rose_illumination
  new_sensor: sensor.ble_sensor_12_illumination
```

> [!TIP]
> Use generic entity IDs for physical sensors (e.g. `sensor.ble_sensor_1_moisture`) and descriptive IDs for plant sensors (e.g. `sensor.rose_moisture`). This makes it easy to swap hardware without confusion.

To remove a sensor, call the action with an empty `new_sensor`.

### Adding a sensor to an existing plant

If you set up a plant without a particular sensor (e.g. you didn't have a CO2 or humidity sensor at the time), that plant sensor entity is **automatically disabled**. To add the sensor later:

1. Go to your plant's device page
2. Find the disabled sensor entity (e.g. "CO2") and **enable** it
3. Use the `plant.replace_sensor` action to assign your physical sensor to it

> [!IMPORTANT]
> You must enable the plant sensor entity **before** using `replace_sensor` — Home Assistant hides disabled entities from the entity picker in the UI, so you won't be able to select it as the `meter_entity` target otherwise.

---

## 🌻 OpenPlantbook Integration

*Requires the [OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook) to be installed.*

### During Setup

When adding a new plant, the config flow searches OpenPlantbook for the species you enter. Matching species are displayed in a dropdown. The selected species' thresholds and image are pre-filled in the limits step.

> [!NOTE]
> The OpenPlantbook API does not include your private user-defined species in search results. See "Force Refresh" below for how to fetch data for private species.

### Changing Species / Refreshing Data

Go to **Settings** → **Devices & Services** → **Plant Monitor** → *Your Plant* → **Configure**.

![Options flow](https://user-images.githubusercontent.com/203184/184328930-8be5fc06-1761-4067-a785-7c46c0b73162.png)

- **Change species:** Enter the new species exactly as the `pid` in OpenPlantbook (including punctuation). New thresholds and image are fetched automatically.
- **Force refresh:** Check this box to re-fetch data from OpenPlantbook without changing the species. Useful for private species not found during initial search. When checked, both the image and display species name are updated.

> [!NOTE]
> If the current image points to a local file or non-OpenPlantbook URL, it is **not** replaced unless "Force refresh" is checked.

---

## 🃏 Lovelace Card

The [Lovelace Flower Card](https://github.com/Olen/lovelace-flower-card/) is designed to work with this integration.

![Flower card light](https://user-images.githubusercontent.com/203184/183286657-824a0e7f-a140-4d8e-8d6a-387070419dfd.png)
![Flower card dark](https://user-images.githubusercontent.com/203184/183286691-02294d6b-84cf-46e6-9070-845d00f24a14.png)

The card supports both °C and °F:

![Temperature units](https://user-images.githubusercontent.com/203184/181259071-58622446-3e24-4f93-8334-293748958bd2.png)

---

## 💡 Tips & Tricks

For practical tips, template examples, and workarounds — including fixing sensors with wrong `device_class`, auto-watering automations, and problem notifications — see **[TIPS.md](TIPS.md)**.

---

## ❓ FAQ

<details>
<summary><strong>I added the wrong sensors — after removing and re-adding the plant, old values still show</strong></summary>

Home Assistant remembers old entity configurations. Instead of removing and re-adding a plant, use the `plant.replace_sensor` action to swap sensors. See [Replacing Sensors](#-replacing-sensors).
</details>

<details>
<summary><strong>I can't select the correct sensor type (e.g. Moisture, Humidity) from the dropdown</strong></summary>

The sensor dropdowns filter by `device_class`. Some integrations don't set the correct device class on their sensors.

**Solutions:**
1. Report the issue to the physical sensor's integration maintainer
2. Add the plant without that sensor, then use the `plant.replace_sensor` action (its checks are more relaxed)
3. Create a template sensor with the correct device class:

```yaml
template:
  - sensor:
      - name: "Soil Moisture"
        unique_id: "soil_sensor_moisture"
        state: "{{ states('sensor.soil_sensor_soil_moisture') }}"
        unit_of_measurement: "%"
        device_class: "moisture"
```
</details>

<details>
<summary><strong>My local image path doesn't work</strong></summary>

Local images must be in your HA `www` folder, referenced with the `/local/` prefix. The path is **case-sensitive**.

| Path | Works? |
|------|--------|
| `/local/images/plants/my-plant.jpg` | ✅ (file at `config/www/images/plants/my-plant.jpg`) |
| `/local/images/plants/My-Plant.jpg` (wrong case) | ❌ |
| `/mnt/nas/photos/plant.jpg` (filesystem path) | ❌ |
| `file:///config/www/images/plants/my-plant.jpg` (file URI) | ❌ |

You can also use `media-source://` URLs. See [Plant Images](#️-plant-images).
</details>

<details>
<summary><strong>I removed a sensor but it comes back after restart</strong></summary>

When you remove a sensor using `plant.replace_sensor` (with an empty `new_sensor`), the change is persisted to the configuration. If sensors reappear, update to the latest release.
</details>

---

## ☕ Support

If you find this integration useful, consider buying me a coffee:

<a href="https://www.buymeacoffee.com/olatho" target="_blank">
<img src="https://user-images.githubusercontent.com/203184/184674974-db7b9e53-8c5a-40a0-bf71-c01311b36b0a.png" style="height: 50px !important;">
</a>
