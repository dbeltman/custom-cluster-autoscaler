# custom-cluster-autoscaler

Enabled building an inventory of (bare metal) hosts in a file, and turning them on with a BMC action when they are needed.

Right now this is done using the following (3$) device: https://devices.esphome.io/devices/Sinilink-XY-WPCE

How it works:
- Detects pending pod
- Tries to find reason (GPU requirement, nodeSelector supported for now) in reasons.yaml
- If valid reason is found, it will try to get a node from the inventory which has that capability
- Find the BMC method, and turns on the BMC with an API call
- If node is configured to auto-join cluster, it will automatically pick up workload after boot

ToDo:
MustHave:
- Downscaling support
- Define secrets per host
ShouldHave:
- Detailed Deployment instructions (configmap, secret)
- ESPHome example config with added power-on logic to avoid looping nodes
- Add waiting logic while node is powering up (partly mitigated by added ESPHome logic)
- Support native IPMI
CouldHave:
- Better Python organization
- Hardware (flasing) instructions
