# This file is just some notes I want to share whle developing

## Templates


### Generate yaml-config
This template will create yaml-config from your current plants, ignoring any thresholds.
It allows you to quickly remove all your plants from the UI, and have them added back using the migration tool.  this might be needed to pick up all changes to the device types and other settings that HA will restore after restart.

I just pick all the devices from certain areas, and loop through them to find all the plants.

Please modify it to suit your needs.

```
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

### Average moisture for multiple plants

I have an auto-watering setup, that will water multiple plants, and I don't want it to run just because one single plant might be slightly low on soil moisture.
So I have this template sensor that averages out all the "moisture" sensors, and trigger the watering automation based on that instead.

This is just an example, and ymml.

``` 
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
