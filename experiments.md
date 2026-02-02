# 🧪 Developer Notes & Experiments

> [!NOTE]
> This file contains developer notes and useful template examples. It is not end-user documentation.

---

## 📝 Useful Templates

### Generate YAML Config from Existing Plants

This template generates YAML config from your current UI-configured plants. Useful for migration testing — remove plants from the UI, then re-add them via the migration tool to pick up all device type changes.

Modify the area names to match your setup:

```jinja2
{% set device_ids = area_devices("are51") + area_devices("livingroom") + area_devices("outside") %}
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

### Average Moisture for Multiple Plants

Template sensor that averages moisture across all plants in an area. Useful for auto-watering setups where you don't want to trigger based on a single plant being slightly low.

Updates automatically when plants are added to the area.

```jinja2
{%- set ns = namespace(m=0, c=0) -%}
{%- for device_id in area_devices("outside") -%}
  {%- for entity_id in device_entities(device_id) -%}
    {%- if entity_id.startswith("sensor.") %}
      {%- if "moisture" in entity_id %}
        {%- set ns.m = ns.m + states(entity_id) | float(default=0) %}
        {%- set ns.c = ns.c + 1 %}
      {%- endif %}
    {%- endif %}
  {%- endfor %}
{%- endfor %}
{%- if ns.c > 0 and ns.m > 0 %}
  {{ (ns.m / ns.c) | round(1) }}
{%- else %}
  0
{% endif %}
```
