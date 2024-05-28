# custom-cluster-autoscaler

Enabled building an inventory of (bare metal) hosts in a file, and turning them on with a BMC action when they are needed.

Right now this is done using the following (3$) device: https://devices.esphome.io/devices/Sinilink-XY-WPCE

ToDo:
- Define secrets per host
- Support native IPMI
- Better Python organization
