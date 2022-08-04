# BREAKING CHANGES COMING UP

>**Warning**
>
> **This integration is about to be completely rewritten.  The next version will *not* be compatible with the original plant integration in HA or with this release.**

## Breaking Changes

Completely new integration.  Please [read this](Version%202.md) carefully before upgrading.

## Changes

## Bugfixes

## Features in v1.0.0

* Compatible with the original integration i Home Assistant
* Can optionally fetch data from [OpenPlantbook](https://open.plantbook.io/)

## Features coming in v2.0.0

* Setup and configuration of plants using the GUI
* Automatically fetch thresholds and plant images from [OpenPlantbook](https://open.plantbook.io/)
  * Requires [this integration] https://github.com/Olen/home-assistant-openplantbook
* Easy modification of thresholds, images, names and species of the plants from GUI
* Easy to replace which sensors are used to monitor the plants
* New daily light integral ("DLI") sensor added automatically to all plants
* Incompatible with the original integration i Home Assistant means you can not use the HA default "plant card" in Lovelace
  * A compatible flower card for Lovelace can be installed [from here](https://github.com/Olen/lovelace-flower-card)
  * Make sure you install version 2.0.0 or higher of that card 

![image](https://user-images.githubusercontent.com/203184/182670259-9abd27c3-8641-444f-9002-4ffc0a80c016.png)



