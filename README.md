# Alternative plants component for Home Assistant

This integration can automatically fetch data from [OpenPlantBook](https://open.plantbook.io/docs.html) if you are a registered user. Registration is free.

# BREAKING CHANGES

>**Warning**
>
> **This integration is *not* compatible with the original plant integration in HA.**

> **Note** 
>
> This integration will try to convert all `plant:` entries from `configuration.yaml` to the new format.  After migration, you can (and should) remove your `plant:` entries from your YAML-configuration.   
> If something goes wrong during migration, delete all the plants from the UI, and correct any problems in your yaml config.  Then they will be migrated again at next restart.  Auto migration will not be done if there are existing plants of the new format already registered in HA.

> **Warning**
> 
> Please notice that the `entity_id` of the plants will **NOT** be preserved during auto-migration.  Also, since the "layout" of the new integration is completely different from the old one, you probably have to update and modify any automations, scripts, blueprints etc. you have made based on the old version.
>
> Make sure you check you plant settings after the first restart. You can find the configuration options in the Integrations page under Settings in Home Assistant.

Plants are set up in the UI and all configuration of your plants can be managed there or by automations and scripts.

All existing entries in `configuration.yaml` from version 1 will be migrated to the new format automatically.  Notice that some options (like `warn_low_brightness`) will not be migrated over, but can be easily changed in the UI configuration after migration. 

## Plants are now treated as _devices_

This means that the main plant entity references other entities, and they are grouped together in the GUI as a single device.

![image](https://user-images.githubusercontent.com/203184/184302443-9d9fb1f2-4b2a-48bb-a479-1cd3a6e634af.png)

This also means that this version is _not_ compatible with earlier releases from this repository, or with the "plant" integration that is part of your default Home Assistant installation 

## Highlights 

### Use the UI to set up plant devices
* Config Flow is used to set up the plants

![PlantConfigFlow](https://user-images.githubusercontent.com/203184/183286111-9b0e64ff-3972-40ad-80ea-d7a5186e933c.gif)

* This works both with and without OpenPlantbook

### Better handling of thresholds

* All thresholds and plant images are fetched automatically from OpenPlantbook if available
* All thresholds now are their own entities and their values can be changed from the UI or by scripts and automations.
* These changes are instantly reflected in HA. No need to restart to change the thresholds.

![image](https://user-images.githubusercontent.com/203184/184302654-dd1f46ec-d645-4d95-b25d-7202faa944cc.png) ![image](https://user-images.githubusercontent.com/203184/184302847-8e593300-2c68-49f3-803c-8a3f5323f7f8.png)




* Max and min temperature is now dependent on the unit of measurement - currently °C and °F is supported.
  * The values will be updated if you change your units in the Home Assistant settings

### Easier to replace sensors

* You can use an Action (previously "service call") to replace the different sensors used to monitor the plant

![image](https://user-images.githubusercontent.com/203184/183286188-174dc709-173f-42fb-9d66-678d0c1f62e4.png)

What I personally do, to make a clearer separation between the physical sensor and the sensor that is part of the plant, is that all my _physical_ sensors (e.g BLE-devices) have generic entity_ids like `sensor.ble_sensor_1_moisture`, `sensor.ble_sensor_1_illumination`, `sensor.ble_sensor_2_conductivity` etc.
And all my plants sensors have entity_ids like `sensor.rose_moisture`, `sensor.chili_conductivity` etc.

That way, if I need to replace a (physical) sensor for e.g. my "Rose" plant, it is very easy to grasp the concept and use
```
service: plant.replace_sensor
data:
  meter_entity: sensor.rose_illumination
  new_sensor: sensor.ble_sensor_12_illumination
```



* The new sensor values are immediately picked up by the plant integration without any need to restart

### Better handling of species, image and problem triggers

* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook
* You can optionally select to force a refresh of plant data from OpenPlantbook, even if you do not change the species.  
* Image can also be updated from the UI
* You can chose to disable problem triggers on all sensors.

![image](https://user-images.githubusercontent.com/203184/184301674-0461813a-a665-4e93-b5a8-7c9575fe4782.png)

These updates are immediately reflected in HA without restarting anything.




### Daily Light Integral

* A new Daily Light Integral - DLI - sensor is created for all plants. 

![image](https://user-images.githubusercontent.com/203184/183286314-91382bf5-7767-4f50-bf58-673c63282c1c.png)

See https://en.wikipedia.org/wiki/Daily_light_integral for what DLI means

### More flexible lovelace card

* I have upgraded the Lovelace flower card to make use of the new integration, and made it more flexible.

![image](https://user-images.githubusercontent.com/203184/183286657-824a0e7f-a140-4d8e-8d6a-387070419dfd.png)

![image](https://user-images.githubusercontent.com/203184/183286691-02294d6b-84cf-46e6-9070-845d00f24a14.png)

* The flower card also handles both °C and °F

![image](https://user-images.githubusercontent.com/203184/181259071-58622446-3e24-4f93-8334-293748958bd2.png)


## Dependencies

* [Updated Lovelace Flower Card](https://github.com/Olen/lovelace-flower-card/tree/new_plant)

* [OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook)

OpenPlantbook is not a strict requirement, but a strong recommendation. Without the OpenPlantbook integration, you need to set and adjust all the thresholds for every plant manually.  With the OpenPlantbook integration added, all data is fetched from OpenPlanbook automatically, and it makes setting up and maintaining plants much, much easier.   

# Installation

### Install and set up OpenPlantbook

_Not required, but strongly recommended_

* Upgrade to the latest version of the OpenPlantbook integration: https://github.com/Olen/home-assistant-openplantbook 
* Set it up, and add your client_id and secret, and test it by using e.g. the `openplantbook.search` service call to search for something.   

### Install new flower-card for Lovelace

_Currently this is the only card in lovelace that support this integration.  Feel free to fork and update - or create PRs - for other lovelace cards._ 

* Install verson 2 of the Flower Card from https://github.com/Olen/lovelace-flower-card/


### Install this integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

#### Via HACS
* Add this repo as a ["Custom repository"](https://hacs.xyz/docs/faq/custom_repositories/) with type "Integration"
* Click "Install" in the new "Home Assistant Plant" card in HACS.
* Install
* Restart Home Assistant

#### Manual Installation
* Copy the entire `custom_components/plant/` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant


The first restart might take some time, as it tries to convert all your plants from your configuration.yaml to the new format.  You can follow this process in the log-file.

After Home Assistant is restarted, you will find all your plants under "Settings" - "Devices and Services" - "Devices".  It will take a minute or two before the current values start to update.

> **Warning**
> The `entity_id` of your plants will probably have changed from the old integration to the new one.  This means that any automations, scripts etc. that use the entity_id or reacts to changes in your plants status will need to be updated.  You probably also need to change the way you read data from the plant device in any such components.

> **Warning**
> This integration is NOT compatible with the built in original plant component.  This means that e.g. the plant cards etc. in the UI, and any blueprints etc. that are built for the original plant intergation wil NOT work with this version.


## Migration from yaml-config
When the integration is first installed, and HomeAssistant is restarted for the first time, all old `plant:` entries will be migrated.
The migration will set up all sensors, thresholds etc. from your yaml-config, and if species is set and OpenPlantbook is set up, it will fill in missing data with data from Openplantbook, or from default values if OpenPlantbook is not set up.

## Problem reports
By default, all problems (e.g. every time a sensor reports a value that is above or below the threshold set in "limits"), the plant state will be set to "problem".

This can be adjusted under "Settings" -> "Devices and Services" -> "Plant Monitor" -> "Your Plant Name" and "Configure".

![image](https://user-images.githubusercontent.com/203184/183286212-000391c2-9c5d-4c1a-a166-a27e1bf0d3ed.png)

Here you can select what kind of threshold violations should trigger a "problem" state of the plant entity.


## Fetching data from OpenPlantbook

_This requires the [OpenPlantbook integration](https://github.com/Olen/home-assistant-openplantbook) to be installed._

When you set up a new plant, the configuration flow will search OpenPlantbook for the species you enter.  If any matches are found, you are presented with a list of exact species to choose from.  Be aware that the OpenPlantbook API does currently not include any of your private user defined species, so you will not find them in the list.  See below for how to refresh data from OpenPlantbook.
If no matches are found, the configuration flow will continue directly to the next step.

In the following step, the threshold values from OpenPlantbook for the chosen species is pre filled and the image from OpenPlantbook is also displayed.  If you chose the incorrect species, you can uncheck the _"This is the plant I was looking for"_ checkbox, and you will be directed back to the dropdown of species to select another one.
If no match is found in OpenPlantbook, the thresholds are pre filled with some default values that you probably want to adjust.

If the species is found in OpenPlantbook, the image link is pre filled with the URL to the image there.  You may overrride this with your own links.  Both linkst starting with `http` and local images in your "www"-folder, e.g. `/local/...` are supported.

### Changing the species / refreshing data

If you later want to change the species of a plant, you do that under "Configuration" of the selected device.

"Settings" -> "Devices and Services" -> "Plant Monitor" -> "Your Plant Name" and "Configure".

![image](https://user-images.githubusercontent.com/203184/184328930-8be5fc06-1761-4067-a785-7c46c0b73162.png)

From there, you have the option to set a new species. If you change the species, data for the new species will be automatically fetched from OpenPlantbook.  The species will have to be entered **exactly** as the "pid" in OpenPlantbook (including any punctations etc.).  If the species is found in OpenPlantbook, the thresholds are updated to the new values.  Also, if the current image links to OpenPlantbook or the image link is empty, the URL to the image in OpenPlanbook is added.  If the current image points to a local file, or a different URL, the image is **not** replaced unless "Force refresh" is checked.  The "Species to display" is not changed if you change the species unless "Force refresh" is checked.
If no species are found in OpenPlantbook, the thresholds and image will be retained with their current values. 

If you just want to refresh the data from OpenPlantbook, without changing the species - for instance if you have private species defined in OpenPlantbook that are not found during setup, you check the "Force refresh" checkbox, and data will be fetched from OpenPlantbook without needing to change the species.  If this checkbox is checked, both the image and the "Species to display" is updated if the species is found in OpenPlantbook.
If no species is found in OpenPlantbook, nothing is changed. 

## FAQ

### I added the wrong sensors, and after removing and adding the plant again with the correct sensor, I can still see the wrong values from the old sensor.

Home Assistant is _very_ good at remembering old configuration of entities if new entities with the same name as the old ones are added again.  This means that if you first create e.g. a moisture-sensor for your plant that reads the data from `sensor.bluetooth_temperature_xxxx`, and the remove the plant and add it back again with the same name, but with moisture-sensor set to `sensor.xiaomi_moisture_yyyy` you might experience that the plant will still show data from the old sensor.  Instead of removing and re-adding a plant, you should just use the `replace_sensor` service call to add the new sensor.

### I can add new plants, but the I can't select the correct sensor (typically "Moisture" or "Humidity") from the list of physical sensors

The dropdowns of available sensors are based on the `Device Class` of the originating (physical) sensor.  Quite some integrations in Home Assistant do NOT report the correct `Device Class` for their sensors.  

E.g. A humidity sensor should have Device Class `SensorDeviceClass.HUMIDITY` and a moisture sensor should use the device class `SensorDeviceClass.MOISTURE`  
A list of the supported Device Classes is available [here](https://developers.home-assistant.io/docs/core/entity/sensor/#available-device-classes)

If the wrong device class is used for a sensor, it will not show up in the list of available sensors.

So what you need to do is:
1) Report the issue to the owner of the integration your phsyical sensor belongs to. They are the only ones who can fix this permanently.
2) You can create the plant without the sensor in question, and then use the Action (Service Call) ["Replace Sensor"](https://github.com/Olen/homeassistant-plant/?tab=readme-ov-file#easier-to-replace-sensors) to add the physical sensor after the plant is set up.  The checks for replacing a sensor are slightly more relaxed than the initial setup.
3) Another option is to create template-sensors that incorporate the correct Device Class.  Add something like this to your `configuration.yaml`:

```
template:
  - sensor:
      - name: "Soil Moisture"                                       # Choose your desired friendly name
        unique_id: "soil_sensor_moisture"                           # Make this unique
        state: "{{ states('sensor.soil_sensor_soil_moisture') }}"   # Get the state from your zigbee sensor
        unit_of_measurement: "%"                                    # Or your desired unit
        device_class: "moisture"                                    # This will give it the appropriate icon and state representation
```


<a href="https://www.buymeacoffee.com/olatho" target="_blank">
<img src="https://user-images.githubusercontent.com/203184/184674974-db7b9e53-8c5a-40a0-bf71-c01311b36b0a.png" style="height: 50px !important;"> 
</a>

