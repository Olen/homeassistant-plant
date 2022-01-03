# Implementation of OpenPlantBook in the plants component

OpenPlantBook: https://open.plantbook.io/docs.html

## Done
* Added some new attributes to the Plant entity (name, species and a "limits"-dict)
* Added "image" and an option not to warn about brightness issues (default is to warn)
* Added new entry for "openplantbook" in the plant-config
* Added functionality for fetching data from the OpenPlantBook API

## TODO
* Better exception-handling

## Long term
* Modify the plant integration to create plants as "Devices" and the various sensors, config etc. as device attributes
  https://community.home-assistant.io/t/re-re-cloud-plant-db-with-api-for-plantcard/326105/5
* Update various plant-related frontends to pull data from the plant entity
  An updated example of the custom flower-card is here: https://github.com/Olen/lovelace-flower-card
* Use config-flow and allow searching the API for plants when adding a new plant


## Usage

### Installation
This can be installed manually or through HACS
#### Via HACS
* Add this repo as a "Custom repository" with type "Integration"
* Click "Install" in the new "Home Assistant Plant" card in HACS
* Restart Home Assistant
#### Manual Installation
* Copy the `plant` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant

### Configuration
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
    image: https://path.to/image.jpg
```

The `species` must be written exactly as i appears in the "pid" in Openplantbook - including quotation marks etc.:
```
  my_plant:
    species: coleus 'marble'
```
If the species is not found, or no `species` is defined in the config, default values for max/min will be provided by the component

If `image` is not set, but species is set, the "image" attribute defaults to `/local/images/plants/<species>.jpg`
If `image` attribute set to "openplantbook" then an image is dynamically being assigned image_url from API.
```
plant:
  Hydrangea:
    species: hydrangea chinensis
    image: openplantbook
    sensors:
      moisture: sensor.miflora_moi
      temperature: sensor.miflora_tem
      conductivity: sensor.miflora_fer
      brightness: sensor.miflora_lux
```

## Problem reports
By default, all problems (e.g. every time a sensor reports a value that is above or below the threshold set in "limits"), the plant state will be set to "problem".
Because not all problems are easily solvable, there is an option to disable warnings for the brightness sensor.

```
  plant_2:
    warn_low_brightness: false
```
With this setting, brightness below the set threshold will not result in a "problem" state.  Especially in some environments, there is not really much you can do about the brightness level, so there is no reason to be notified about it.

## Attributes
The component sets some attributes to each plant that is accessible in the "limits"-dictionary:
```
{{ state_attr('plant.my_plant', 'limits') }}

{% set limits = state_attr('plant.my_plant', 'limits') %}
{{ limits['min_moisture'] }}
```

These attributes can be used in e.g. automations, plant cards in lovelace etc.

