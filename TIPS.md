# 💡 Tips & Tricks

Practical tips, template examples, and workarounds for common situations with the Plant Monitor integration.

---

## 📑 Table of Contents

- [💡 Tips & Tricks](#-tips--tricks)
  - [🔍 A sensor is missing from the dropdown? → MISSING_SENSORS.md](MISSING_SENSORS.md)
  - [💧 Auto-Watering with Averaged Moisture](#-auto-watering-with-averaged-moisture)
  - [🚨 Problem Notification Automation](#-problem-notification-automation)
  - [🌤️ Weather Forecast Warnings for Outdoor Plants](#️-weather-forecast-warnings-for-outdoor-plants)
  - [🌡️ Combining Multiple Temperature Sources](#️-combining-multiple-temperature-sources)
  - [🔋 Battery Monitoring & Stuck Sensors](#-battery-monitoring--stuck-sensors)
  - [📊 Export Plant Config as YAML](#-export-plant-config-as-yaml)

---

## 🔍 A Sensor Is Missing From the Dropdown? (Wrong/Missing `device_class`)

The most common issue: a sensor exists but isn't listed in a config-flow dropdown because the source integration (often Zigbee2MQTT or a BLE sensor) didn't set its `device_class`. **The permanent fix is to report it to that integration**; several local workarounds are also available.

➡️ Full explanation and workarounds: **[MISSING_SENSORS.md](MISSING_SENSORS.md)**

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

> [!TIP]
> The integration includes built-in [hysteresis](README.md#hysteresis) on all thresholds, so plants won't flap between OK and PROBLEM when a sensor value hovers near a boundary. This significantly reduces duplicate notifications without any extra configuration.

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

To include which specific sensor(s) triggered the issue, iterate over the plant's **`problems`** attribute. It is a list of exactly the sensors that are currently out of range *and* have their problem trigger enabled — each entry has `sensor_type`, `status` (`Low`/`High`), `current`, `min`, and `max`:

```yaml
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has a problem.
            {% for p in trigger.to_state.attributes.get('problems', []) %}
            - {{ p.sensor_type | replace('_', ' ') | title }}: {{ p.status }} (current {{ p.current }}, range {{ p.min }}–{{ p.max }})
            {% endfor %}
```

> [!TIP]
> Use `problems` rather than the individual `*_status` attributes here. A `*_status` can read `Low`/`High` even when that sensor's trigger is disabled, so looping over the status attributes would report sensors you've intentionally chosen not to treat as problems. See [Problem Reports](README.md#️-problem-reports).

---

## 🌤️ Weather Forecast Warnings for Outdoor Plants

Get warned the evening before when tomorrow's forecast shows temperatures outside your outdoor plants' configured thresholds — giving you time to move them indoors or cover them.

This automation combines two things you already have: your weather integration's forecast and the per-plant threshold entities created by Plant Monitor (`number.<plant>_min_temperature`, etc.).

```yaml
automation:
  - alias: "Plant weather warning"
    description: >
      Compares tomorrow's weather forecast against outdoor plants'
      temperature thresholds. Notifies if any plant may be at risk.

    trigger:
      # ── When to check ─────────────────────────────────────────
      # Evening gives you time to act before overnight lows.
      # Adjust the time to fit your routine.
      - platform: time
        at: "18:00:00"

    action:
      # ── Step 1: Fetch the daily forecast ───────────────────────
      # Replace "weather.home" with your weather entity.
      # You can test what your integration returns in
      # Developer Tools → Actions → weather.get_forecasts.
      - action: weather.get_forecasts
        target:
          entity_id: weather.home
        data:
          type: daily
        response_variable: forecast

      # ── Step 2: Extract tomorrow's temperatures ────────────────
      - variables:
          # Daily forecasts typically list today as [0] and tomorrow
          # as [1]. Check the "datetime" field in the response from
          # Developer Tools to verify this for your weather integration.
          tomorrow: "{{ forecast['weather.home'].forecast[1] }}"
          forecast_high: "{{ tomorrow.temperature | float }}"
          forecast_low: "{{ tomorrow.templow | float }}"

          # ── Your outdoor plants ────────────────────────────────
          # List only plants that are actually outdoors. Indoor
          # plants aren't affected by weather and don't need this.
          outdoor_plants:
            - plant.rose
            - plant.tomato
            - plant.basil

          # ── Step 3: Check each plant's thresholds ──────────────
          # For each plant, we look up its min/max temperature
          # threshold entities. These follow the naming pattern:
          #
          #   number.<plant_slug>_max_temperature
          #   number.<plant_slug>_min_temperature
          #
          # where <plant_slug> is the part after "plant." in the
          # entity ID (e.g. plant.rose → number.rose_min_temperature).
          #
          # The default values (-999 / 999) ensure that a missing
          # threshold entity never triggers a false warning.
          warnings: >
            {% set ns = namespace(items=[]) %}
            {% for plant_id in outdoor_plants %}
              {% set name = state_attr(plant_id, 'friendly_name') %}
              {% set slug = plant_id | replace('plant.', '') %}
              {% set min_t = states('number.' ~ slug ~ '_min_temperature') | float(-999) %}
              {% set max_t = states('number.' ~ slug ~ '_max_temperature') | float(999) %}
              {% if forecast_low < min_t %}
                {% set ns.items = ns.items + [
                  name ~ ' — forecast low ' ~ forecast_low ~ '° is below min threshold ' ~ min_t ~ '°'
                ] %}
              {% endif %}
              {% if forecast_high > max_t %}
                {% set ns.items = ns.items + [
                  name ~ ' — forecast high ' ~ forecast_high ~ '° exceeds max threshold ' ~ max_t ~ '°'
                ] %}
              {% endif %}
            {% endfor %}
            {{ ns.items }}

      # ── Step 4: Only notify when there's something to report ───
      - condition: template
        value_template: "{{ warnings | length > 0 }}"

      # ── Step 5: Send the notification ──────────────────────────
      # Replace with your preferred notify service.
      - action: notify.mobile_app
        data:
          title: "Plant weather warning"
          message: >
            Tomorrow's forecast ({{ forecast_low }}°–{{ forecast_high }}°)
            may affect these plants:
            {% for w in warnings %}
            - {{ w }}
            {% endfor %}
```

### Customizing

**Use an area instead of a manual list.** If all your outdoor plants are in the same area, replace the `outdoor_plants` variable with:

```yaml
          outdoor_plants: >
            {{ area_entities("garden") | select("match", "^plant\\.") | list }}
```

This picks up new plants automatically when they're added to the area.

**Add humidity checks.** If your weather integration includes humidity in its daily forecast, extend the comparison inside the `{% for plant_id ... %}` loop:

```yaml
              {% set min_h = states('number.' ~ slug ~ '_min_humidity') | float(-999) %}
              {% set max_h = states('number.' ~ slug ~ '_max_humidity') | float(999) %}
              {% if tomorrow.humidity is defined %}
                {% if tomorrow.humidity | float < min_h %}
                  {% set ns.items = ns.items + [name ~ ' — humidity ' ~ tomorrow.humidity ~ '% below min ' ~ min_h ~ '%'] %}
                {% endif %}
                {% if tomorrow.humidity | float > max_h %}
                  {% set ns.items = ns.items + [name ~ ' — humidity ' ~ tomorrow.humidity ~ '% above max ' ~ max_h ~ '%'] %}
                {% endif %}
              {% endif %}
```

> [!NOTE]
> Not all weather integrations include humidity in their daily forecast. Check what fields your integration provides in **Developer Tools** → **Actions** → `weather.get_forecasts`.

---

## 🌡️ Combining Multiple Temperature Sources

> [!TIP]
> Home Assistant has an official tutorial on averaging sensor values: [Show the average home temperature on your dashboard](https://www.home-assistant.io/docs/templating/tutorial-average-temperature/). The same approach works for averaging moisture, conductivity, or any other numeric sensor across your plants.

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

## 🔋 Battery Monitoring & Stuck Sensors

Plant sensors (especially BLE and Zigbee) are battery-powered and will eventually stop updating when the battery dies. This integration does not monitor battery levels directly — it monitors the *readings* from your sensors. A dead battery typically shows up as a sensor stuck on its last value or going unavailable.

Home Assistant has an official tutorial that walks you through building a daily low-battery notification: **[Get notified when a device needs a new battery](https://www.home-assistant.io/docs/templating/tutorial-battery-alerts/)**. This covers all your HA devices, including plant sensors.

If you want to detect **stuck sensors** (battery not yet reported as low, but readings stopped changing), you can use a `last_changed` check:

```yaml
automation:
  - alias: "Plant sensor stuck warning"
    description: >
      Warns when a plant sensor hasn't changed value in 24 hours,
      which may indicate a dead battery or connectivity issue.
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - variables:
          stale_sensors: >
            {% set ns = namespace(items=[]) %}
            {% for state in states.sensor %}
              {% if 'external_sensor' in state.attributes
                 and (now() - state.last_changed).total_seconds() > 86400 %}
                {% set ns.items = ns.items + [
                  state.attributes.friendly_name ~ ' (last changed '
                  ~ relative_time(state.last_changed) ~ ' ago)'
                ] %}
              {% endif %}
            {% endfor %}
            {{ ns.items }}
      - condition: template
        value_template: "{{ stale_sensors | length > 0 }}"
      - action: notify.mobile_app
        data:
          title: "Plant sensor may be stuck"
          message: >
            These plant sensors haven't updated in 24 hours:
            {% for s in stale_sensors %}
            - {{ s }}
            {% endfor %}
```

> [!NOTE]
> The `external_sensor` attribute is present on plant-owned sensor entities, so this filters specifically for plant sensors rather than all sensors in your system.

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
