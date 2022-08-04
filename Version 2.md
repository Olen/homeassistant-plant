# News in version 2.0.0

## Plants are now treated as _devices_

This means that the main plant entity references other entities, and they are grouped togheter in the GUI as a single device.

![image](https://user-images.githubusercontent.com/203184/181916412-dfeab387-083b-4260-8ca9-c91983ac7247.png)

This also means that this version is _not_ compatible with earlier releases from this repository, or with the "plant" integration that is part of your default Home Assistant installation 

## Highlights 

### Use the UI to set up plant devices
* Config Flow is used to set up the plants

![image](https://community-assets.home-assistant.io/original/4X/b/d/2/bd23a66ace82209f2030f46ad76c2aa8534cf040.gif)

* This works both with and without OpenPlantbook

### Better handling of thresholds

* All thresholds and plant images are fetched automatically from OpenPlantbook if available
* All thresholds now are their own entities and their values can be changed from the UI or by scripts and automations.
* These changes are instantly reflected in HA. No need to restart to change the thresholds.

![image](https://user-images.githubusercontent.com/203184/180942669-016e2552-6694-4c37-95e2-2a5a8204b148.png)

* Max and min temperature is now dependent on the unit of measurement - currently °C and °F is supported.
  * The values will be updated if you change your units in the Home Assistant settings

### Easier to replace sensors

* You can use a service call to replace the different sensors used to monitor the plant

![image](https://user-images.githubusercontent.com/203184/182139407-895b011b-6841-4bf4-ad01-ea6a1bb76500.png)

* The new sensor values are immediately picked up by the plant integration without any need to restart

### Better handling of species and image

* If you change the species of a plant in the UI, new data are fetched from OpenPlantbook
* Image can also be updated from the UI
* These updates are immediately reflected in HA without restarting anything.

![image](https://user-images.githubusercontent.com/203184/182644580-e3c50a82-f548-4c7e-8826-7e27389cd145.png)

* Illuminance warnings are now triggered by calculating the "Daily Light Integral" - DLI.
* You can chose to disable warnings on high/low temperature, humidity and illuminance/DLI.


### Daily Light Integral

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

OpenPlantbook integration: https://github.com/Olen/home-assistant-openplantbook

Updated Lovelace Flower Card: https://github.com/Olen/lovelace-flower-card/tree/new_plant



