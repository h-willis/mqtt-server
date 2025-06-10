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

    def add(self, packet, pid, state):
        self.messages[pid] = QoS2Message(packet, state)

    def acknowledge(self, pid):
        print(f'acknowledging qos 2 {pid}: ', end='')

        message = None
        try:
            if self.messages[pid].state == STATE_PUBREC:
                # store message for returning for calling on_message
                message = self.messages[pid]

            self.messages[pid].advance_state()

            if self.messages[pid].state == STATE_DONE:
                print(f'Handshake complete for {pid}')
                del self.messages[pid]

        except KeyError:
            print("Couldn't find pid")

        return message


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    """

    def __init__(self):
        self.qos_1_messages = MQTTClientQoS1Messages()
        self.qos_2_messages = MQTTClientQoS2Messages()

    def add_qos_1(self, packet):
        self.qos_1_messages.add(packet)

    def add_qos_2(self, packet, pid, state=STATE_PUBLISH):
        self.qos_2_messages.add(packet, pid, state)

    def acknowledge(self, qos, pid):
        if qos == 1:
            return self.qos_1_messages.acknowledge(pid)
        return self.qos_2_messages.acknowledge(pid)
