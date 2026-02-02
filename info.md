# 🌱 Plant Monitor for Home Assistant

A comprehensive plant monitoring integration that treats each plant as a **device** with its own sensors, thresholds, and health tracking. Automatically fetches species data from [OpenPlantbook](https://open.plantbook.io/docs.html).

> [!WARNING]
> This integration is **not** compatible with the original built-in plant integration in Home Assistant.

## ✨ Features

- 🖥️ **UI-based setup** — guided multi-step config flow with optional OpenPlantbook species search
- 📊 **Per-plant thresholds** — each threshold is its own entity, adjustable from the UI or via automations
- 🌤️ **Daily Light Integral** — automatic DLI calculation from illuminance sensors
- 🔄 **Live updates** — change sensors, thresholds, species, or images without restarting HA
- 🚨 **Configurable problem triggers** — enable/disable per sensor type
- 🔌 **Auto-disable** — sensors without a source entity are automatically disabled
- 🖼️ **Flexible images** — HTTP URLs, local `/www/` files, or media source URLs

## 📦 Dependencies

- **[OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook)** *(optional but recommended)* — automatically fetches thresholds and images for your plant species
- **[Lovelace Flower Card](https://github.com/Olen/lovelace-flower-card/)** *(optional)* — the recommended card for displaying plant data

## 📖 Documentation

See the [README](https://github.com/Olen/homeassistant-plant/) for full installation instructions, configuration details, and FAQ.
