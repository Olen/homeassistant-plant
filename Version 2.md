# News in version 2.0.0

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



