from dataclasses import dataclass

import packets

STATE_PUBLISH = 'PUBLISH'
STATE_PUBREC = 'PUBREC'
STATE_PUBREL = 'PUBREL'
STATE_DONE = 'DONE'


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

    def acknowledge(self, packet):
        print(f'acknowledging qos 1 {packet.packet_id}: ', end='')

        try:
            del self.packets[packet.packet_id]
            print('acknowledged')
        except KeyError:
            print("couldn't find pid")


class QoS2Message:
    def __init__(self, packet, state):
        self.packet = packet
        self.state = state

    def advance_state(self):
        # this is tracking the last message sent rather than what is expected
        if self.state == STATE_PUBLISH:
            self.state = STATE_PUBREL
            return

        if self.state == STATE_PUBREC:
            self.state = STATE_DONE
            return

        if self.state == STATE_PUBREL:
            self.state = STATE_DONE
            return


class MQTTClientQoS2Messages:
    # Handshake looks like this
    # PUBLISH ->
    # PUBREC  <-
    # PUBREL  ->
    # PUBCOMP <-
    def __init__(self):
        self.messages = {}

    def add(self, packet, state):
        self.messages[packet.packet_id] = QoS2Message(packet, state)

    def acknowledge(self, packet):
        print(f'acknowledging qos 2 {packet.packet_id}: ', end='')

        message = None
        try:
            if self.messages[packet.packet_id].state == STATE_PUBREC:
                # store message for returning for calling on_message
                message = self.messages[packet.packet_id]

            self.messages[packet.packet_id].advance_state()

            if self.messages[packet.packet_id].state == STATE_DONE:
                print(f'Handshake complete for {packet.packet_id}')
                del self.messages[packet.packet_id]

        except KeyError:
            print("Couldn't find pid")

        return message


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    """

    def __init__(self, pg):
        self.qos_1_messages = MQTTClientQoS1Messages()
        self.qos_2_messages = MQTTClientQoS2Messages()

        self.pg = pg

    def add(self, packet, state=STATE_PUBLISH):
        """ Add a packet to the appropriate QoS message list """
        if packet.qos == 1:
            self.qos_1_messages.add(packet)
        elif packet.qos == 2:
            self.qos_2_messages.add(packet, state)
        else:
            print(f'Unknown QoS {packet.qos} for {packet}')

    def acknowledge(self, packet):
        if packet.qos == 1:
            return self.qos_1_messages.acknowledge(packet)
        return self.qos_2_messages.acknowledge(packet)
