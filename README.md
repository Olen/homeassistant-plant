# Implementation of OpenPlantBook in the plants component

OpenPlantBook: https://open.plantbook.io/docs.html

# BREAKING CHANGES COMING UP

This integration is about to be completely rewritten.  The next version will *not* be compatible with the original plant integration in HA or with the current release in this repository.

This is just a heads up for now, but I want to give everyone fair warning. We are looking into different options to make the transition to the new version as smooth as possible.

![image](https://user-images.githubusercontent.com/203184/181916412-dfeab387-083b-4260-8ca9-c91983ac7247.png)


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

### Better handling of species and image

* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook
* Image can also be updated from the UI

![image](https://user-images.githubusercontent.com/203184/181916091-db7de9ca-d120-4614-a83e-d93a5dad9183.png)

* You can chose to disable warnings on high/low illuminance.
  * Illuminance warnings are now triggered by calculating the "Daily Light Integral" - DLI.

### Easier to replace sensors

* You can use a service call to replace the different sensors used to monitor the plant

![image](https://user-images.githubusercontent.com/203184/181916318-67bddc07-0e32-477d-bc15-3f32bbc4768b.png)

* A new Daily Light Integral - DLI - sensor is created for all plants. 

![image](https://user-images.githubusercontent.com/203184/181916359-65d34768-96b9-4ef3-8432-4a65836ed6cc.png)

See https://en.wikipedia.org/wiki/Daily_light_integral for what DLI means

### More flexible lovelace card

* I have upgraded the Lovelace flower card to make use of the new integration, and made it more flexible.

![image](https://user-images.githubusercontent.com/203184/181916249-bd32478f-888f-40e0-b000-572f062aadc6.png)

![image](https://user-images.githubusercontent.com/203184/181916283-6263cb3f-1903-4538-a9a1-3e33d102ec88.png)


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


