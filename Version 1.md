# 📜 Version 1 (Legacy — YAML Configuration)

> [!CAUTION]
> Version 1 is **no longer maintained**. This document is kept for historical reference only.
> Please use the current version which is set up entirely through the UI.
> See the [README](README.md) for installation and setup instructions.

---

## Overview

Version 1 required `plant:` entries in `configuration.yaml` for manual setup. It supported fetching data from [OpenPlantbook](https://open.plantbook.io/docs.html) via YAML configuration.

## Configuration Example

```yaml
plant:
  openplantbook:
    client_id: !secret plantbook_client_id
    secret: !secret plantbook_secret

  plant_1:
    species: champagne mini rose
    sensors:
      moisture: sensor.mi_m_80eaca88xxxx
      conductivity: sensor.mi_c_80eaca88xxxx
      temperature: sensor.mi_t_80eaca88xxxx
      brightness: sensor.mi_l_80eaca88xxxx
```

You could override OpenPlantbook values:

```yaml
  plant_2:
    species: champagne mini rose
    name: Little Rose
    sensors:
      moisture: sensor.mi_m_80eaca88xxxx
      conductivity: sensor.mi_c_80eaca88xxxx
      temperature: sensor.mi_t_80eaca88xxxx
      brightness: sensor.mi_l_80eaca88xxxx
    min_temperature: 25
    max_moisture: 100
    image: https://path.to/image.jpg
```

The `species` had to match exactly the "pid" in OpenPlantbook, including punctuation:

```yaml
  my_plant:
    species: coleus 'marble'
```

## Problem Reports

Brightness warnings could be disabled per plant:

```yaml
  plant_2:
    warn_low_brightness: false
```

## Attributes

Limits were accessible as attributes:

```jinja2
{{ state_attr('plant.my_plant', 'limits') }}

{% set limits = state_attr('plant.my_plant', 'limits') %}
{{ limits['min_moisture'] }}
```
