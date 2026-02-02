# 📋 Version 2 Changelog

> [!NOTE]
> This document describes the changes introduced in version 2.0.0. For current documentation, see the [README](README.md).

---

## 🌿 Plants Are Now Devices

The main plant entity references other entities, grouped together in the UI as a single device.

![Plant device](https://user-images.githubusercontent.com/203184/183286104-4849fcd5-20eb-488d-9a7d-433e365f9657.png)

> [!WARNING]
> Version 2 is **not** compatible with earlier releases or with the built-in `plant` integration in Home Assistant.

---

## ✨ Highlights

### 🖥️ UI-Based Setup
- Config flow used to set up plants (no more YAML configuration)
- Works with and without OpenPlantbook

### 📊 Better Threshold Handling
- All thresholds are their own entities — adjustable from the UI or via automations
- Changes take effect immediately (no restart needed)
- Temperature thresholds adapt to °C / °F unit settings

### 🔄 Easier Sensor Replacement
- Use the `plant.replace_sensor` action to swap sensors without restarting

### 🌻 Better Species & Image Management
- Changing species in the UI automatically fetches new data from OpenPlantbook
- Images can be updated from the UI
- All updates are immediate

### ☀️ Daily Light Integral
- DLI sensor automatically created for all plants
- Illuminance warnings can be based on DLI instead of raw lux values
- Problem triggers can be disabled per sensor type

### 🃏 Updated Lovelace Card
- [Flower Card](https://github.com/Olen/lovelace-flower-card/) upgraded for the new integration
- Supports both °C and °F

---

## 📦 Dependencies

- [OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook) *(optional but recommended)*
- [Lovelace Flower Card](https://github.com/Olen/lovelace-flower-card/)
