# Implementation of OpenPlantBook in the plants component

OpenPlantBook: https://open.plantbook.io/docs.html

# BREAKING CHANGES COMING UP

This integration is about to be completely rewritten.  The next version will *not* be compatible with the original plant integration in HA or with the current release in this repository.

This is just a heads up for now, but I want to give everyone fair warning. We are looking into different options to make the transition to the new version as smooth as possible.

![image](https://user-images.githubusercontent.com/203184/180956019-2733ad82-3be2-47cb-bdbf-3f5db2127a96.png)


## Highlights 

### Use the UI to set up plant devices
* Config Flow is used to set up the plants

![image](https://community-assets.home-assistant.io/original/4X/b/d/2/bd23a66ace82209f2030f46ad76c2aa8534cf040.gif)

* This works both with and without OpenPlantbook

### Better handling of thresholds

* All thresholds and plant images are fetched automatically from OpenPlantbook
* All thresholds now are their own entities and their values can be changed from the UI or by scripts and automations

![image](https://user-images.githubusercontent.com/203184/180942669-016e2552-6694-4c37-95e2-2a5a8204b148.png)

* Max and min temperature is now dependent on the unit of measurement - currently °C and °F is supported.
  * The values will be updated if you change your units in the Home Assistant settings

### Better handling of species

* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook

![Image](change_plant.gif)

### Easier to replace sensors

* You can use a service call to replace the different sensors used to monitor the plant

![image](https://user-images.githubusercontent.com/203184/180942138-d77cbad4-8e06-448c-bd1a-4e2b8f12a951.png)


### Service to replace image

* You can use a service call to replace the plant image

![image](https://user-images.githubusercontent.com/203184/181352702-260774a0-4f5b-4387-a1cb-7dd7c3aa4698.png)



### More flexible lovelace card

* I have upgraded the Lovelace flower card to make use of the new integration, and made it more flexible.

![image](https://user-images.githubusercontent.com/203184/181259328-f5d386bf-3dce-4ed2-b683-882f2d4b0c66.png)

* The flower card also handles both °C and °F

![image](https://user-images.githubusercontent.com/203184/181259071-58622446-3e24-4f93-8334-293748958bd2.png)




## Dependencies

Add the OpenPlantbook integration: https://github.com/Olen/home-assistant-openplantbook

Add the updated Lovelace Flower Card: https://github.com/Olen/lovelace-flower-card/tree/new_plant


### Installation
This can be installed manually or through HACS
#### Via HACS
* Add this repo as a "Custom repository" with type "Integration"
* Click "Install" in the new "Home Assistant Plant" card in HACS
#### Manual Installation
* Copy the `plant` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant

## Problem reports
By default, all problems (e.g. every time a sensor reports a value that is above or below the threshold set in "limits"), the plant state will be set to "problem".

The exception is the Brightness sensors which will be ignored for now


