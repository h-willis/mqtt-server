from dataclasses import dataclass


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    """

    def __init__(self):
        self.packets = []

    def add(self, packet):
        """ Takes packet info from 

        Args:
            message (_type_): _description_
        """
        print(f'adding {packet}')
        self.packets.append(packet)

    def acknowledge(self, command, pid):
        print(f'acknowledging {command} | {pid}')

        for packet in self.packets:
            if packet.pid == pid:
                print('acknowledged')
                self.packets.remove(packet)
