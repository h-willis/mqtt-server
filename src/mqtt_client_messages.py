import threading
import time

WAIT_FOR_PUBREC = 'WAIT_FOR_PUBREC'
WAIT_FOR_PUBREL = 'WAIT_FOR_PUBREL'
WAIT_FOR_PUBCOMP = 'WAIT_FOR_PUBCOMP'
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
    def __init__(self, packet, state):
        super().__init__(packet)
        self.state = state
        self.dup = False

    def advance_state(self):
        if self.state == WAIT_FOR_PUBREC:
            # we have sent the PUBLISH packet and are waiting for PUBREC
            self.state = WAIT_FOR_PUBCOMP
            self.reset_retry()
            return

        if self.state == WAIT_FOR_PUBCOMP:
            # we have sent the PUBREL packet and are waiting for PUBCOMP
            self.state = DONE
            return

        if self.state == WAIT_FOR_PUBREL:
            # we have sent the PUBREC packet and are waiting for PUBREL
            self.state = DONE
            self.reset_retry()
            return

    def resend(self):
        # resend here is a matter of which state we're in
        if self.state == WAIT_FOR_PUBREC:
            print(f'Resending PUBLISH packet {self.packet.packet_id}')
            self.packet.set_dup_bit()
            self.packet.send()
            self.increase_retries()
        elif self.state == WAIT_FOR_PUBREL:
            print(f'Resending PUBREC packet {self.packet.packet_id}')
            self.packet.set_dup_bit()
            self.packet.send()
            self.increase_retries()
        elif self.state == WAIT_FOR_PUBCOMP:
            print(f'Resending PUBREL packet {self.packet.packet_id}')
            self.packet.set_dup_bit()
            self.packet.send()
            self.increase_retries()
        elif self.state == DONE:
            return

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

    def add(self, packet, state):
        self.messages[packet.packet_id] = QoS2Message(packet, state)

    def acknowledge(self, packet):
        print(f'acknowledging qos 2 id:{packet.packet_id} : ', end='')

        message = None
        try:
            if self.messages[packet.packet_id].state == STATE_PUBREC:
                # store message for returning for calling on_message
                message = self.messages[packet.packet_id]

            self.messages[packet.packet_id].advance_state()
            print('State advanced')

            if self.messages[packet.packet_id].state == STATE_DONE:
                print(f'Handshake complete for {packet.packet_id}')
                del self.messages[packet.packet_id]

        except KeyError:
            print("Couldn't find pid")

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
        self.background_thread = threading.Thread(
            target=self.message_retry_thread)

    def start_retry_thread(self):
        print("Starting retry thread...")
        if not self.background_thread.is_alive():
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

    def add(self, packet, state=WAIT_FOR_PUBREC):
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
