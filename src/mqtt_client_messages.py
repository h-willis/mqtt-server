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

    def acknowledge(self, pid):
        print(f'acknowledging qos 1 {pid}: ', end='')

        try:
            del self.packets[pid]
            print('acknowledged')
        except KeyError:
            print("Couldn't find pid")


class QoS2Message:
    def __init__(self, packet, state):
        self.packet = packet
        self.state = state

    def advance_state(self):
        # this is tracking the last message sent rather than what is expected
        # TODO define these strings
        if self.state == 'PUBLISH':
            self.state = 'PUBREL'
            return

        if self.state == 'PUBREC':
            self.state = 'DONE'
            return

        if self.state == 'PUBREL':
            self.state = 'DONE'
            return


class MQTTClientQoS2Messages:
    # Handshake looks like this
    # PUBLISH ->
    # PUBREC  <-
    # PUBREL  ->
    # PUBCOMP <-
    def __init__(self):
        self.messages = {}

    def add(self, packet, pid, state):
        self.messages[pid] = QoS2Message(packet, state)

    def acknowledge(self, pid):
        print(f'acknowledging qos 2 {pid}: ', end='')

        try:
            self.messages[pid].advance_state()
            print(self.messages[pid].state)

            if self.messages[pid].state == 'DONE':
                print(f'Handshake complete for {pid}')
                del self.messages[pid]

        except KeyError:
            print("Couldn't find pid")


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    """

    def __init__(self):
        self.qos_1_messages = MQTTClientQoS1Messages()
        self.qos_2_messages = MQTTClientQoS2Messages()

    def add_qos_1(self, packet):
        self.qos_1_messages.add(packet)

    def add_qos_2(self, packet, pid, state='PUBLISH'):
        self.qos_2_messages.add(packet, pid, state)

    def acknowledge(self, qos, pid):
        if qos == 1:
            self.qos_1_messages.acknowledge(pid)
            return
        self.qos_2_messages.acknowledge(pid)
