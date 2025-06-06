from dataclasses import dataclass

import packets


class MQTTClientQoS1Messages:
    # TODO retry stale messages with increasing timeout
    def __init__(self):
        self.packets = {}

    def add(self, packet):
        """ Takes packet info from 

        Args:
            message (_type_): _description_
        """
        print(f'adding {packet}')
        self.packets[packet.pid] = packet

    def acknowledge(self, command, pid):
        print(f'acknowledging {command} | {pid}: ', end='')

        try:
            del self.packets[pid]
            print('acknowledged')
        except KeyError:
            print("Couldn't find pid")


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    TODO this needs two separate lists for qos 1 and qos 2 messages
    """

    def __init__(self):
        self.qos_1_messages = MQTTClientQoS1Messages()

    def add(self, packet, qos):
        """ Takes packet info from 

        Args:
            message (_type_): _description_
        """
        print(f'adding {packet}, {qos}')
        if qos == 1:
            self.qos_1_messages.add(packet)

    def acknowledge(self, command, pid):
        print(f'acknowledging {command} | {pid}: ', end='')

        if command == packets.PUBACK_BYTE:
            self.qos_1_messages.acknowledge(command, pid)
