import threading
import time
import packets

# seeing as this will only be used to genearte qos 2 handshake packets we dont
# need the reference to the client packet generator as we dont need the
# incrementing packet id
from packet_generator import PacketGenerator as pg

SEND_PUBLISH = 'SEND_PUBLISH'
SEND_PUBREC = 'SEND_PUBREC'
SEND_PUBREL = 'SEND_PUBREL'
SEND_PUBCOMP = 'SEND_PUBCOMP'
DONE = 'DONE'


class QOS1Message:
    def __init__(self, packet):
        self.packet = packet
        self.retries = 0
        self.max_retries = 5
        self.retry_interval = 2  # seconds
        self.retry_backoff = 2  # seconds
        self.next_retry_time = time.time() + self.retry_interval + 5

    @property
    def due_to_retry(self):
        return time.time() >= self.next_retry_time

    @property
    def retries_exceeded(self):
        return self.retries >= self.max_retries

    def resend(self):
        # here we need to set the DUP bit and resend the packet
        self.packet.set_dup_bit()
        self.packet.send()

        self.increase_retries()
        if self.retries >= self.max_retries:
            print(
                f'Max retries reached for packet {self.packet.packet_id}. Giving up.')
            self.next_retry_time = 9999999999  # disable further retries

    def increase_retries(self):
        self.retries += 1
        self.retry_interval *= self.retry_backoff  # double the retry interval
        self.next_retry_time = time.time() + self.retry_interval

    def increment_retry(self):
        self.retries += 1


class MQTTClientQoS1Messages:
    # TODO retry stale messages with increasing timeout
    def __init__(self):
        self.messages = {}

    def add(self, packet):
        """ Takes packet info from 

        Args:
            message (_type_): _description_
        """
        print(f'adding {packet}')
        message = QOS1Message(packet)
        self.messages[packet.packet_id] = message

    def acknowledge(self, packet):
        print(f'acknowledging qos 1 {packet.packet_id}: ', end='')

        try:
            del self.messages[packet.packet_id]
            print('acknowledged')
        except KeyError:
            print("couldn't find pid")

    def manage_retries(self):
        """ Loop through messages and resend if not acknowledged """
        for pid, message in list(self.messages.items()):
            if message.due_to_retry:
                print(f'Retrying QoS 1 message {pid}')
                message.resend()
                if message.retries_exceeded:
                    print(
                        f'Max retries exceeded for QoS 1 message {pid}. Removing from queue.')
                    del self.messages[pid]


class QoS2Message(QOS1Message):
    """ State machine for controlling QoS 2 messages.
    The state machine transmits a message for the first time on state transitions
    allowing for easier retransmission in the current state.

    Args:
        QOS1Message (_type_): Base class that contains most of the retry logic
        packet (_type_): The packet of the PUBLISH message we are doing the 
        handshake for. Can be sent or received packet.
    """

    def __init__(self, packet, state):
        super().__init__(packet)
        self.state = state

    def acknowledge(self, incoming_packet):
        if self.state == SEND_PUBLISH:
            # we are sending a PUBLISH packet, so we expect a PUBREC packet
            if incoming_packet.command_type == packets.PUBREC_BYTE:
                print(f'Received PUBREC for {self.packet.packet_id}')
                # send a PUBREL packet
                pg(self.packet.send_func).create_pubrel_packet(
                    self.packet.packet_id, dup=True).send()
                self.advance_state()
                return

        if self.state == SEND_PUBREL:
            # we are sending a PUBREL packet, so we expect a PUBCOMP packet
            if incoming_packet.command_type == packets.PUBCOMP_BYTE:
                print(f'Received PUBCOMP for {self.packet.packet_id}')
                self.advance_state()
                return
            # we could also receive a PUBREC packet here, which means we need to
            # resend the PUBREL packet with the dup bit set
            if incoming_packet.command_type == packets.PUBREC_BYTE:
                # TODO do we check for a dup bit?
                self.resend()
                return

        if self.state == SEND_PUBREC:
            # we are expecting a PUBREL packet, so we send a PUBCOMP packet
            if incoming_packet.command_type == packets.PUBREL_BYTE:
                print(f'Received PUBREL for {self.packet.packet_id}')
                pg(self.packet.send_func).create_pubcomp_packet(
                    self.packet.packet_id).send()
                self.advance_state()
                return
            # we can also receive the publish packet here, which means we need to
            # resend the PUBREC packet with the dup bit set
            if incoming_packet.command_type == packets.PUBLISH_BYTE:
                print(f'Received PUBLISH for {self.packet.packet_id}')
                self.resend()
                return

    def advance_state(self):
        if self.state == SEND_PUBLISH:
            # first state for messages we are sending
            # we change state when we receive a PUBREC packet and send a pubrel
            pg(self.packet.send_func).create_pubrel_packet(
                self.packet.packet_id).send()
            self.state = SEND_PUBREL
            return

        if self.state == SEND_PUBREL:
            # we change state when we receive a PUBCOMP packet
            # at which point we are done with the message
            # we wait in this state so we can resend the PUBREL packet with the dup bit set
            self.state = DONE
            return

        if self.state == SEND_PUBREC:
            # first state for messages we are receiving
            # we change state when we receive a PUBREL packet after which we
            # process the message
            # any further PUBREL packets will be responeded to with PUBCOMP
            pg(self.packet.send_func).create_pubcomp_packet(
                self.packet.packet_id).send()
            self.state = DONE
            return

    def resend(self):
        # depends on what state we're in
        if self.state == SEND_PUBLISH:
            # resend the publish packet with dup bit set
            print(f'Resending PUBLISH for {self.packet.packet_id}')
            self.packet.set_dup_bit(True)
            self.packet.send()

        if self.state == SEND_PUBREC:
            # resend the PUBREC packet with dup bit set
            print(f'Resending PUBREC for {self.packet.packet_id}')
            pg(self.packet.send_func).create_pubrec_packet(
                self.packet.packet_id, dup=True).send()

        if self.state == SEND_PUBREL:
            # resend the PUBREL packet with dup bit set
            print(f'Resending PUBREL for {self.packet.packet_id}')
            pg(self.packet.send_func).create_pubrel_packet(
                self.packet.packet_id, dup=True).send()

    def reset_retry(self):
        # reset retry counters and timers when state advances
        self.retries = 0
        self.retry_interval = 2
        self.next_retry_time = time.time() + self.retry_interval
        self.dup = False


class MQTTClientQoS2Messages:
    # Handshake looks like this
    # PUBLISH ->
    # PUBREC  <-
    # PUBREL  ->
    # PUBCOMP <-
    def __init__(self):
        self.messages = {}

    def add(self, packet, received):
        # packet should only be a publish packet
        # we could already have it if it's a retransmission
        # assume we've sent the message
        state = SEND_PUBLISH

        if received:
            state = SEND_PUBREC
            if packet.dup:
                self.messages[packet.packet_id].resend()
                return
            # send the PUBREC packet
            pg(packet.send_func).create_pubrec_packet(
                packet.packet_id, dup=False).send()
        self.messages[packet.packet_id] = QoS2Message(packet, state)
        print(f'Adding QoS 2 message {packet.packet_id} with state {state}')

    def acknowledge(self, packet):
        # here we either advance state or send the packet with the dup bit set
        print(f'acknowledging qos 2 id:{packet.packet_id} ', end='')

        message = None
        try:
            self.messages[packet.packet_id].advance_state()
            print('State advanced')

            if self.messages[packet.packet_id].state == DONE:
                # store message for returning it for processing
                message = self.messages[packet.packet_id]
                print(f'Handshake complete for {packet.packet_id}')
                del self.messages[packet.packet_id]

        except KeyError:
            print("Couldn't find pid")
            # if this is a PUBREL we need to send the PUBCOMP regardless
            if packet.command_type == packets.PUBREL_BYTE:
                print(f'Sending PUBCOMP for {packet.packet_id}')
                pg(packet.send_func).create_pubcomp_packet(
                    packet.packet_id).send()

        return message

    def manage_retries(self):
        """ Loop through messages and resend if not acknowledged """
        for pid, message in list(self.messages.items()):
            if message.due_to_retry:
                print(f'Retrying QoS 2 message {pid} in state {message.state}')
                message.resend()
                if message.retries_exceeded:
                    print(
                        f'Max retries exceeded for QoS 2 message {pid}. Removing from queue.')
                    del self.messages[pid]


class MQTTClientMessages:
    """ When a message that requires acknowledgement is sent it's added to the
    list and a timer started for a reattempt at sending 
    """

    def __init__(self):
        self.qos_1_messages = MQTTClientQoS1Messages()
        self.qos_2_messages = MQTTClientQoS2Messages()

        # TODO handle this thread better
        self.background_thread = None

    def start_retry_thread(self):
        print("Starting retry thread...")
        if self.background_thread is None:
            self.background_thread = threading.Thread(
                target=self.message_retry_thread)
            self.background_thread.start()
        else:
            print("Retry thread is already running.")

    def stop_retry_thread(self):
        print("Stopping retry thread...")
        if self.background_thread.is_alive():
            self.background_thread.join(timeout=1)
            print("Retry thread stopped.")
        else:
            print("Retry thread is not running.")
        self.background_thread = None

    def add(self, packet, received=False):
        """ Add a packet to the appropriate QoS message list """
        if packet.qos == 1:
            self.qos_1_messages.add(packet)
        elif packet.qos == 2:
            self.qos_2_messages.add(packet, received)
        else:
            print(f'Unknown QoS {packet.qos} for {packet}')

    def acknowledge(self, packet):
        if packet.qos == 1:
            return self.qos_1_messages.acknowledge(packet)
        return self.qos_2_messages.acknowledge(packet)

    def message_retry_thread(self):
        # Loop through messages and resend if not acknowledged
        # Do qos 1 first as it is simpler
        print('RETRY THREAD SKIPPED')
        return
        while True:
            # TODO configure this
            time.sleep(1)
            self.qos_1_messages.manage_retries()
            self.qos_2_messages.manage_retries()
