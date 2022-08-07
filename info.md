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

