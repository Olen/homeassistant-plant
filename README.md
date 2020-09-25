# Implementation of OpenPlantBook in the plants component

OpenPlantBook: https://open.plantbook.io/docs.html

## Done
* Added some new attributes to the Plant entity (name, species and a "limits"-dict)
* Added new entry for "openplantbook" in the plant-config
* Added functionality for fetching data from the OpenPlantBook API

## TODO
* Better exception-handling

## Long term
* Update various plant-related frontends to pull data from the plant entity
  An updated example of the custom flower-card is here: https://github.com/Olen/lovelace-flower-card
* Use config-flow and allow searching the API for plants when adding a new plant


## Usage
* Copy the files to <config>/custom_components/plant/
* Restart HA

The plant-component can now be configured as follows:

```
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

You can also add parameters that will override the ones you receive from the API

```
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
```

The `species` must be written exactly as i appears in the "pid" in Openplantbook - including quotation marks etc.:
```
  my_plant:
    species: coleus 'marble'
```
If the species is not found, or no `species` is defined in the config, default values will be provided by the component

## Attributes
The component sets some attributes to each plant that is accessible in the "limits"-dictionary:
```
{{ state_attr('plant.my_plant', 'limits') }}

{% set limits = state_attr('plant.my_plant', 'limits') %}
{{ limits['min_moisture'] }}
```

