# 💡 Tips & Tricks

Practical tips, template examples, and workarounds for common situations with the Plant Monitor integration.

---

## 📑 Table of Contents

- [💡 Tips & Tricks](#-tips--tricks)
  - [🔧 Fixing Sensors with Wrong or Missing Device Class](#-fixing-sensors-with-wrong-or-missing-device-class)
  - [💧 Auto-Watering with Averaged Moisture](#-auto-watering-with-averaged-moisture)
  - [🚨 Problem Notification Automation](#-problem-notification-automation)
  - [🌡️ Combining Multiple Temperature Sources](#️-combining-multiple-temperature-sources)
  - [📊 Export Plant Config as YAML](#-export-plant-config-as-yaml)

---

## 🔧 Fixing Sensors with Wrong or Missing Device Class

This is the most common issue users run into. The sensor dropdowns in the config flow filter by `device_class`, and many integrations (especially Zigbee and BLE sensors) don't set it correctly. A humidity sensor might report soil moisture, or a soil sensor might have no `device_class` at all.

There are three ways to work around this:

### Option 1: Use `customize.yaml` *(simplest)*

Override the device class directly in your HA configuration. No new entities created.

```yaml
# In customize.yaml
sensor.my_zigbee_soil_sensor:
  device_class: moisture

sensor.my_humidity_sensor_used_for_soil:
  device_class: moisture
```

Restart Home Assistant after editing. The sensor will now appear in the correct dropdown.

### Option 2: Create a Template Sensor

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

### Option 3: Use `replace_sensor` After Setup

The `replace_sensor` action has **more relaxed** validation than the initial setup. You can:

1. Set up the plant **without** the problematic sensor
2. Use **Developer Tools** → **Actions** → `plant.replace_sensor` to assign it afterward

```yaml
action: plant.replace_sensor
data:
  meter_entity: sensor.my_plant_soil_moisture
  new_sensor: sensor.zigbee_sensor_with_wrong_device_class
```

> [!NOTE]
> If the plant sensor entity is disabled (because no source was configured during setup), you must **enable** it first on the device page before it appears in the entity picker. See [Adding a sensor to an existing plant](README.md#adding-a-sensor-to-an-existing-plant).

### Which Option to Choose?

| Option | Pros | Cons |
|--------|------|------|
| `customize.yaml` | Simple, no extra entities | Affects the sensor globally |
| Template sensor | Full control, can rename/process | Extra entity to maintain |
| `replace_sensor` | No config changes needed | Slightly less convenient |

> [!TIP]
> Regardless of the workaround, **report the missing `device_class` to the integration that owns the physical sensor**. That's the only way to fix it permanently for everyone.

---

## 💧 Auto-Watering with Averaged Moisture

If you have an auto-watering system serving multiple plants, you probably don't want it to trigger just because one plant is slightly dry. This template sensor averages the soil moisture across all plants in an area:

```yaml
template:
  - sensor:
      - name: "Average Soil Moisture Outside"
        unique_id: "average_soil_moisture_outside"
        unit_of_measurement: "%"
        device_class: moisture
        state_class: measurement
        state: >
          {%- set ns = namespace(total=0, count=0) -%}
          {%- for device_id in area_devices("outside") -%}
            {%- for entity_id in device_entities(device_id) -%}
              {%- if entity_id.startswith("sensor.") and "moisture" in entity_id -%}
                {%- set val = states(entity_id) | float(default=-1) -%}
                {%- if val >= 0 -%}
                  {%- set ns.total = ns.total + val -%}
                  {%- set ns.count = ns.count + 1 -%}
                {%- endif -%}
              {%- endfor -%}
            {%- endfor -%}
          {%- endfor -%}
          {{ (ns.total / ns.count) | round(1) if ns.count > 0 else 0 }}
```

This updates automatically when plants are added to or removed from the area.

You can then use this as a trigger for your watering automation:

```yaml
automation:
  - alias: "Water outdoor plants"
    trigger:
      - platform: numeric_state
        entity_id: sensor.average_soil_moisture_outside
        below: 30
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.garden_irrigation
```

---

## 🚨 Problem Notification Automation

Get notified when any plant has a problem:

```yaml
automation:
  - alias: "Plant problem notification"
    trigger:
      - platform: state
        entity_id:
          - plant.rose
          - plant.tomato
          - plant.basil
        to: "problem"
    action:
      - service: notify.mobile_app
        data:
          title: "🌱 Plant needs attention"
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has a problem!
```

To include which specific sensor triggered the issue, check the plant's attributes:

```yaml
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has a problem.
            {% for attr in ['moisture_status', 'temperature_status', 'conductivity_status', 'illuminance_status', 'humidity_status', 'dli_status'] %}
              {% if trigger.to_state.attributes.get(attr) in ['Low', 'High'] %}
              - {{ attr | replace('_status', '') | title }}: {{ trigger.to_state.attributes[attr] }}
              {% endif %}
            {% endfor %}
```

---

## 🌡️ Combining Multiple Temperature Sources

If you have multiple temperature sensors near a plant and want to use the average:

```yaml
template:
  - sensor:
      - name: "Greenhouse Average Temperature"
        unique_id: "greenhouse_avg_temp"
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement
        state: >
          {% set sensors = [
            states('sensor.greenhouse_temp_1') | float(0),
            states('sensor.greenhouse_temp_2') | float(0)
          ] %}
          {% set valid = sensors | select('greaterthan', -40) | list %}
          {{ (valid | sum / valid | count) | round(1) if valid else 'unavailable' }}
```

---

## 📊 Export Plant Config as YAML

This template generates YAML config from your current UI-configured plants. Useful for backup or migration purposes.

Modify the area names to match your setup:

```jinja2
{% set device_ids = area_devices("living_room") + area_devices("garden") %}
{% set ns = namespace(is_plant=False) %}
{%- for device_id in device_ids %}
  {%- set ns.is_plant = False %}
  {%- for entity_id in device_entities(device_id) -%}
    {%- if entity_id.startswith("plant.") %}
    {%- set ns.is_plant = True %}
{{ entity_id.replace(".", "_") }}:
  species: {{ state_attr(entity_id, "species_original") }}
  name: {{ state_attr(entity_id, "friendly_name") }}
  image: {{ state_attr(entity_id, "entity_picture") }}
  sensors:
    {%- endif %}
  {%- endfor %}
  {%- if ns.is_plant == True %}
    {%- for entity_id in device_entities(device_id) -%}
      {%- if entity_id.startswith("sensor.") and state_attr(entity_id, "external_sensor") %}
        {%- if "illuminance" in entity_id %}
    brightness: {{ state_attr(entity_id, "external_sensor") }}
        {%- endif %}
        {%- if "conduct" in entity_id %}
    conductivity: {{ state_attr(entity_id, "external_sensor") }}
        {%- endif %}
        {%- if "moist" in entity_id %}
    moisture: {{ state_attr(entity_id, "external_sensor") }}
        {%- endif %}
        {%- if "temp" in entity_id %}
    temperature: {{ state_attr(entity_id, "external_sensor") }}
        {%- endif %}
      {%- endif %}
    {%- endfor %}
  {%- endif %}
{%- endfor %}
```

Use this in **Developer Tools** → **Template** to generate the output.
