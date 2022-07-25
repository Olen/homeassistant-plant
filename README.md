# Implementation of OpenPlantBook in the plants component

OpenPlantBook: https://open.plantbook.io/docs.html

# BREAKING CHANGES COMING UP

This integration is about to be completely rewritten.  The next version will *not* be compatible with the original plant integration in HA or with the current release in this repository.

This is just a heads up for now, but I want to give everyone fair warning. We are looking into different options to make the transition to the new version as smooth as possible.

![image](https://user-images.githubusercontent.com/203184/180848877-79a91691-5c8a-4eab-ae0e-864780501a0c.png)


## Highlights 
The new integration is fully configureable from the UI.
* Config Flow is used to set up the plants

![image](https://community-assets.home-assistant.io/original/4X/b/d/2/bd23a66ace82209f2030f46ad76c2aa8534cf040.gif)

* All thresholds and plant images are fetched automatically from OpenPlantbook
* Thresholds can be changed from the UI (or by e.g. automations)
* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook
* You can use a service call to replace the different sensors used to monitor the plant
* I have upgraded the Lovelace flower card to make use of the new integration, and made it more flexible.

## Usage

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


