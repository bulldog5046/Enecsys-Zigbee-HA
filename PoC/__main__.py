import asyncio
import sys
import struct
import logging
import json
import re
import zigpy.types as t

# There are many different radio libraries but they all have the same API
from zigpy_znp.zigbee.application import ControllerApplication


# logging
logger = logging.getLogger('zigpy')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

class MainListener:
    """
    Contains callbacks that zigpy will call whenever something happens.
    Look for `listener_event` in the Zigpy source or just look at the logged warnings.
    """

    def __init__(self, application):
        self.application = application
        self.data = {}

    def device_joined(self, device):
        print(f"Device joined: {device}")

    def attribute_updated(self, device, cluster, attribute_id, value):
        print(f"Received an attribute update {attribute_id}={value}"
              f" on cluster {cluster} from device {device}")
    
    def handle_message(self, sender, profile, cluster, src_ep, dst_ep, message):
        ## Custom handling of Enecsys messages
        ## Catch and response to the initial message after joining to start telemetry flow
        if b'\x02\x01\x0A\x00\x00\x00'in message:
            asyncio.create_task(ControllerApplication.request(self.application, sender, profile, cluster, src_ep, dst_ep, 180, b'\x57\x01\x95\xb4\x30\x7a\x00\x9a\xc6\x34\x02\x01\x32\x00\x00\x00\x02\x00\x93',expect_reply=False, use_ieee=False))
            
        ## catch telemetry messages, process and write out to file
        if b'\x57\x00' in message and b'\x21\x01\x00\x00' in message:
            try:
                to_hex = {0, 1, 2, 13}
                x = [x.hex() if i in to_hex else x for i, x in enumerate(struct.unpack(">2s8s10sBHHHbHbHHHs", message))]
            except struct.error:
                logger.log(logging.DEBUG, 'This isnt the telemetry we were looking for (%s)', message)
                return

            # map data to dict
            data = {
                x[1]: {
                    "serial": None,
                    "mac": x[1],
                    "state": x[3],
                    "dc_current": x[4],
                    "dc_watts": x[5],
                    "dc_volt": None,
                    "efficiency": x[6],
                    "ac_freq": x[7],
                    "ac_volt": x[8],
                    "ac_watts": None,
                    "temp": x[9],
                    "wh": x[10], #watt hour metric is only incrememted while the inverter is running. ie, it's valid for a single daylight session.
                    "kwh": x[11],
                    "lifetime_wh": None
                }
            }

            # calulated assignments
            data[x[1]]['dc_current'] *= 0.025
            data[x[1]]['efficiency'] *= 0.001
            data[x[1]]['lifetime_wh'] = data[x[1]]['kwh'] * 1000 + data[x[1]]['wh']
            data[x[1]]['ac_watts'] = data[x[1]]['dc_watts'] * data[x[1]]['efficiency']
            data[x[1]]['dc_volt'] = data[x[1]]['dc_watts'] / data[x[1]]['dc_current']
            data[x[1]]['mac'] = re.sub(r'(..)(..)(..)(..)(..)(..)(..)(..)', r'\8\7\6\5\4\3\2\1', data[x[1]]['mac']) # TODO: probably a better way to do this.
            data[x[1]]['serial']  = str(int(data[x[1]]['mac'][8:16], 16))

            # merge to the instance data var
            self.data.update(data)

            # write out to file
            with open("telemetry.json", "w") as file:
                json.dump(self.data, file, indent=4)

async def permit_join(app):
    while True:
        # leaving permit join open is outside of Zigbee 3 spec, this is a workaround.
        logger.log(logging.DEBUG, 'Permitting join requests for 254 seconds')
        await app.permit(254)
        await asyncio.sleep(254)

async def main():
    app = ControllerApplication(ControllerApplication.SCHEMA({
        "database_path": "zigbee.db",
        "device": {
            "path": f"{sys.argv[1]}",
        },
    }))

    listener = MainListener(app)
    app.add_listener(listener)

    await app.startup(auto_form=True)

    # Permit joins for a     
    await asyncio.create_task(permit_join(app))
 
    # Just run forever
    await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())