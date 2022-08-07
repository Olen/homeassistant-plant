# Alternative plants component for Home Assistant

This integration can automatically fetch data from [OpenPlantBook](https://open.plantbook.io/docs.html) if you are a registered user. Registration is free.

# BREAKING CHANGES

>**Warning**
>
> **This integration is about to be completely rewritten.  Versions > 2.0.0 will *not* be compatible with the original plant integration in HA or with earlier releases of this integration.**

> **Note** 
>
> Version 2 of this integration will try to convert all `plant:` entries from `configuration.yaml` to the new format.  After migration, you can (and should) remove your `plant:` entries from your YAML-configuration.   

> **Warning**
> Please notice that the `entity_id` of the plants will **NOT** be preserved during auto-migration.  Also, since the "layout" of the new integration is completely different from the old one, you probably have to update and modify any automations, scripts, blueprints etc. you have made based on the old version.
>
> Make sure you check you plant settings after the first restart. You can find the configuration options in the Integrations page under Settings in Home Assistant.


# Version 1

This is the "old" version.  Requiring `plant`-entries in `configuration.yaml` and manual setup.

This version will no longer be maintained, and I strongly urge everyone to test out the new version and report any issues.

[Read more and see installation instructions](https://github.com/Olen/homeassistant-plant/blob/master/Version%201.md)

The rest of this file will describe the upcoming version - 2.0.0.

# Version 2

This is the new and upcoming version.  It is set up in the UI and all configuration of your plants can be managed there or by automations and scripts.

All existing entries in `configuration.yaml` from version 1 will be migrated to the new format automatically.  Notice that some options (like `warn_low_brightness`) will not be migrated over, but can be easily changed in the UI configuration after migration. 

Version 2 is available as a beta release in HACS. 

>**Note**
>
>**HACS releases are coming soon**

## Plants are now treated as _devices_

This means that the main plant entity references other entities, and they are grouped togheter in the GUI as a single device.

![image](https://user-images.githubusercontent.com/203184/183286104-4849fcd5-20eb-488d-9a7d-433e365f9657.png)


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

![image](https://user-images.githubusercontent.com/203184/183286156-d8c250ab-e54c-4983-9c1b-c709875d6be1.png)


* Max and min temperature is now dependent on the unit of measurement - currently °C and °F is supported.
  * The values will be updated if you change your units in the Home Assistant settings

### Easier to replace sensors

* You can use a service call to replace the different sensors used to monitor the plant

![image](https://user-images.githubusercontent.com/203184/183286188-174dc709-173f-42fb-9d66-678d0c1f62e4.png)

* The new sensor values are immediately picked up by the plant integration without any need to restart

### Better handling of species, image and problem triggers

* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook
* Image can also be updated from the UI
* These updates are immediately reflected in HA without restarting anything.

![image](https://user-images.githubusercontent.com/203184/183286212-000391c2-9c5d-4c1a-a166-a27e1bf0d3ed.png)

* Illuminance warnings are now also triggered by calculating the "Daily Light Integral" - DLI.
* You can chose to disable problem triggers on all sensors.


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

OpenPlantbook integration: https://github.com/Olen/home-assistant-openplantbook

Updated Lovelace Flower Card: https://github.com/Olen/lovelace-flower-card/tree/new_plant


# Installation

Until the branch is merged, only manual installation is possible.

### Install and set up OpenPlantbook

* Upgrade to the latest version of the OpenPlantbook integration: https://github.com/Olen/home-assistant-openplantbook
* Set it up, and add your client_id and secret, and test it by using e.g. the `openplantbook.search` service call to search for something.   

### Install new flower-card for Lovelace

* Copy the latest flower-card.json from https://github.com/Olen/lovelace-flower-card/tree/new_plant to somewhere under /config/www/ in your HA installation, and add it as a lovelace resource.

### Install this integration

* Move your old `custom_components/plant/` out of the way.  
* Copy all the content from this branchs custom_components/plant/ to custom_components/plant/ in you HA installation

* Restart HA

The first restart might take some time, as it tries to convert all your plants from your configuration.yaml to the new format.  You can follow this process in the log-file.

After HA is restarted, you will find all your plants under "Setting" - "Devices and Services" - "Devices".  It will take a minute or two before the current values start to update.

> **Warning**
> The `entity_id` of your plants will probably have changed from the old integration to the new one.  This means that any automations, scripts etc. that use the entity_id or reacts to changes in your plants status will need to be updated.  You probably also need to change the way you read data from the plant device in any such components.

> **Warning**
> This integration is NOT compatible with the built in original plant component.  This means that e.g. the plant cards etc. in the UI, and any blueprints etc. that are built for the original plant intergation wil NOT work with this version.


# Info kept until this version is released in HACS. Ignore for now.

This can be installed manually or through HACS

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

#### Via HACS
* Add this repo as a "Custom repository" with type "Integration"
* Click "Install" in the new "Home Assistant Plant" card in HACS
#### Manual Installation
* Copy the `plant` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant

## Problem reports
By default, all problems (e.g. every time a sensor reports a value that is above or below the threshold set in "limits"), the plant state will be set to "problem".



