# 🔍 A Sensor Is Missing From the Dropdown (Wrong or Missing `device_class`)

This is the most common issue users run into.

The sensor dropdowns in the config flow filter by Home Assistant **`device_class`**. Many integrations — especially **Zigbee2MQTT** and some BLE sensors — create the entity with the correct *unit* (e.g. `µS/cm`) but **without** a `device_class` (e.g. `conductivity`) or `state_class`. Home Assistant still creates the entity, but Plant Monitor — and any selector that filters by device class — won't list it. A humidity sensor reporting soil moisture, or a soil sensor with no `device_class` at all, hits the same problem.

> [!IMPORTANT]
> **The real fix is upstream — please report it there first.**
> Plant Monitor intentionally does **not** work around missing device classes; doing so would mask a metadata bug in the integration that owns the hardware. If a sensor is missing its `device_class`/`state_class`, **open an issue with that integration** (e.g. Zigbee2MQTT, the BLE integration, the device's quirk/converter). Once they publish the correct metadata the sensor appears automatically — for you **and** for everyone else with that device. The workarounds below are personal stopgaps until that fix lands; they are not a substitute for the upstream report.

---

## Workarounds (until the upstream fix lands)

### Zigbee2MQTT: override in `devices.yaml` *(recommended for Z2M)*

Fixes the entity at the source — no extra entity, and it mirrors what the proper upstream fix will do. Add `device_class`/`state_class` under the device's `homeassistant:` block:

```yaml
# /config/zigbee2mqtt/devices.yaml
'0xa4c138b46e1ffa5b':        # your device's IEEE address
  friendly_name: Flamingo Lily Sensor
  homeassistant:
    soil_fertility:           # the exposed property (e.g. soil_fertility -> conductivity)
      device_class: conductivity
      state_class: measurement
```

Restart/reload Zigbee2MQTT. The entity gets the correct `device_class` and appears in the dropdown.

### Option: `customize.yaml` *(simplest, any integration)*

Override the device class directly in your HA configuration. No new entities created.

```yaml
# In customize.yaml
sensor.my_zigbee_soil_sensor:
  device_class: moisture
```

Restart Home Assistant after editing.

### Option: Create a Template Sensor

Create a new sensor with the correct `device_class`. Useful when you also want to rename the sensor or add processing.

```yaml
# In configuration.yaml (or a templates/ file)
template:
  - sensor:
      - name: "Garden Soil Moisture"
        unique_id: "garden_soil_moisture_fixed"
        state: "{{ states('sensor.zigbee_soil_sensor_humidity') }}"
        unit_of_measurement: "%"
        device_class: moisture
        state_class: measurement
```

### Option: Use `replace_sensor` After Setup

The `plant.replace_sensor` action has **more relaxed** validation than the setup flow and the **Configure** → **Replace sensors** UI — it does not filter by `device_class`, so it accepts any `sensor.*` entity. You can:

1. Set up the plant **without** the problematic sensor
2. Use **Developer Tools** → **Actions** → `plant.replace_sensor` to assign it

```yaml
action: plant.replace_sensor
data:
  meter_entity: sensor.my_plant_soil_moisture
  new_sensor: sensor.zigbee_sensor_with_wrong_device_class
```

> [!NOTE]
> If the plant sensor entity is disabled (because no source was configured during setup), you must **enable** it first on the device page before it appears in the entity picker. See [Adding a sensor to an existing plant](README.md#adding-a-sensor-to-an-existing-plant).

---

## Which Workaround to Choose?

| Workaround | Pros | Cons |
|--------|------|------|
| Z2M `devices.yaml` | Fixes at source, no extra entity, mirrors the real fix | Zigbee2MQTT only |
| `customize.yaml` | Simple, any integration, no extra entities | Affects the sensor globally |
| Template sensor | Full control, can rename/process | Extra entity to maintain |
| `replace_sensor` | No config changes, available from the UI | Sensor must be enabled first |

> [!TIP]
> Whichever you pick, it only fixes *your* setup. Reporting the missing `device_class` to the upstream integration is the only thing that fixes it permanently for everyone.
