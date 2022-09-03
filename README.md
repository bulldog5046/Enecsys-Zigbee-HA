# Enecsys Zigbee
Reverse engineering the Enecsys Solar Inverter zigbee protocol to integrate into HomeAssistant.

Enecsys Inverters typically use a propritary gateway device to collect and forward telemetry data. Enecsys went into administration in 2015 and the used market now has an abundance of cheap micro inverters but a destinct lack of any of the gateway devices.

This project is to attempt to reverse engineer the Zigbee protocol Enecsys used to directly collect telemetry from inverters and ultimately integrate into HomeAssistant.


## Basic Requirements
Enecsys's implementation of zigbee requires 3 paramenters to match to establish a network.

1. Trust-Center Link Key = "ENCSYS-SOLAR-NET"
2. PAN id = 0x02aa
3. Stack Profile = 0x00

Most Zigbee network parameters are configurable at runtime, however according the Zigbee 3 spec the TC-Link Key can only be set at complilation. It was therefore required to recompile the Z-Stack firmware for the Sonoff Zigbee Dongle Plus I was using. [Z-Stack 3.x.0 recompiled](firmware/znp_CC1352P_2_LAUNCHXL_tirtos_ccs.hex)

The PAN id and Stack Profile can be configred either in Zigpy configuration before the network is formed or by modifying the NVRAM with Zigpy_ZNP.Tools after the network has been formed.

## Zigbee Commands

Once a basic zigbee network has been formed with the required settings the inverters will begin to associate with the network. After successful association and key exchange there is a brief exchange between the inverter and the gateway before telemetry is transmitted periodically.

Inverter Request:

```5701ef55f705009ac63405ef55f705009ac63402010a00000097```

Gateway Response:

```570195b4307a009ac634020132000000020093```


## Data Payload
Example data payload extracted from sniffing the traffic between the inverters and a genuine gateway device.

![](images/enecsys_payload_data.png)

Wireshark attempts to decode this as a ZCL (Zigbee Cluster Library) frame. This causes some oddities as it's not intended to be a ZCL frame, however this could come in useful further along when attempting to get integration into HomeAssistant as we will probably need to make the messages appear to be standard zigbee frames. ie. part of the mac address becomes the 'command'.

![](images/wireshark_zcl_frame.png)

Code snippet to test unpacking and processing:
(With thanks to [Omoerbeek](https://github.com/omoerbeek/e2pv) for previous work done on similar data)
```
<?php
$str = "57002991f605009ac6342101000000be1430038800003b0031033e3100f42303a905430000e6";
$data = hex2bin($str);
$v = unpack("H4cmd/H16mac/H20ukn/CState/nDCCurrent/nDCPower/nEfficiency/cACFreq/nACvolt/cTemp/nWh/nkWh/n/H2CRC",$data);
print_r($v);
```
Result:
```
Array ( 
    [cmd] => 5700 
    [mac] => 2991f605009ac634 
    [ukn] => 2101000000be14300388 
    [State] => 0 
    [DCCurrent] => 59 
    [DCPower] => 49 
    [Efficiency] => 830 
    [ACFreq] => 49 
    [ACvolt] => 244 
    [Temp] => 35 
    [Wh] => 937 
    [kWh] => 1347 
    [1] => 0 
    [CRC] => e6 )
```

