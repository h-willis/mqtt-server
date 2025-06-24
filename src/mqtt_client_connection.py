import socket
import random
import string
from time import sleep

# packet stuff
from packet_validator import PacketValidator, PacketValidatorError
from packet_generator import PacketGenerator
import packets

from mqtt_client_messages import MQTTClientMessages
from logging_setup import LoggerSetup
logger = LoggerSetup.get_logger(__name__)


class MQTTClientConnection:
    def __init__(self, address, port, client_id=None, keep_alive=60, clean_session=True):
        self.address = address
        self.port = port
        self.keep_alive = keep_alive
        self.clean_session = clean_session
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_id = client_id if client_id else self.generate_random_client_id()

        self.connected = False

        self.on_connect = lambda: None
        self.on_disconnect = lambda: None
        self.on_message = lambda topic, payload: None

        # lwt
        self.will_topic = None
        self.will_payload = None
        self.will_qos = 0
        self.will_retain = False
        #
        self.username = None
        self.password = None

        # needs to be instance to handle increasing packet ids
        # send is attached to packets so we need to pass it here
        self.pg = PacketGenerator(self.send)
        self.validator = PacketValidator(self.send)

        # pg is used to create and resend dup packets in qos handshakes
        self.messages = MQTTClientMessages()

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def set_will(self, topic, payload, qos=0, retain=False):
        self.will_topic = topic
        self.will_payload = payload
        self.will_qos = qos
        self.will_retain = retain

    def connect(self, timeout):
        logger.info('Attempting to connect to MQTT server')

        if not self.connect_socket_to_server(timeout):
            self.connected = False
            logger.error('Failed to connect to server')
            return

        logger.info(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        # TODO this could be better
        server_response = self.negotiate_connection_to_server(timeout)

        try:
            # TODO actually check this is a connack packet
            packet = self.validator.validate_packet(server_response)
        except PacketValidatorError as e:
            # invalid packet for some reason
            logger.error(e.message)
            logger.error('Offending data: %s',
                         '\\x'.join(f"{byte:02x}" for byte in server_response))
            self.connected = False
            return

        logger.info('We connected!')
        self.connected = True
        self.call_on_connect()

        # TODO ping threading as optional start
        # self.ping_thread = threading.Thread(target=self.ping_manager)
        # self.ping_thread.start()

    def call_on_connect(self):
        self.messages.start_retry_thread()

        try:
            self.on_connect()
        except Exception as e:
            logger.error('Error while calling on_connect callback:')
            logger.exception(e)

    def call_on_disconnect(self):
        self.messages.stop_retry_thread()

        try:
            self.on_disconnect()
        except Exception as e:
            logger.error('Error while calling on_disconnect callback:')
            logger.exception(e)

    def call_on_message(self, topic=None, payload=None):
        try:
            self.on_message(topic, payload)
        except Exception as e:
            logger.error('Error while calling on_message callback:')
            logger.exception(e)

    def socket_connected(self):
        try:
            self.send(b'')
            return True
        except (OSError, BrokenPipeError):
            return False

    def connect_socket_to_server(self, timeout):
        attempts = 0
        while True:
            if self.socket_connected():
                return True
            try:
                self.conn.settimeout(1)
                self.conn.connect((self.address, self.port))
                return True
            except (ConnectionRefusedError, ConnectionAbortedError):
                attempts += 1
                if attempts > timeout:
                    # TODO more information about failure here
                    return False
                sleep(1)
            finally:
                self.conn.settimeout(None)

    def negotiate_connection_to_server(self, timeout):
        connect_packet = self.pg.create_connect_packet(
            client_id=self.client_id, will_topic=self.will_topic,
            will_message=self.will_payload, will_qos=self.will_qos,
            will_retain=self.will_retain, username=self.username,
            password=self.password, keep_alive=self.keep_alive,
            clean_session=self.clean_session)
        data = None

        try:
            self.conn.settimeout(timeout)
            connect_packet.send()
            logger.debug('Connection packet sent, waiting for response...')
            data = self.conn.recv(4)
        except TimeoutError:
            logger.warning('No response from server.')
            return None
        finally:
            self.conn.settimeout(None)

        return data

    def publish(self, topic, payload, qos, retain):
        # TODO dup might not be needed here
        if not self.connected:
            logger.warning(f'Cant publish to {topic}, not connected to server')
            return

        pub_packet = self.pg.create_publish_packet(topic, payload, qos, retain)
        if qos > 0:
            self.messages.add(pub_packet)
        pub_packet.send()

    def subscribe(self, topic, qos):
        if not self.connected:
            logger.warning(
                f'Cant subscribe to {topic}, not connected to server')
            return

        sub_packet = self.pg.create_subscribe_packet(topic, qos)
        sub_packet.send()

    def loop(self):
        logger.info('Entering loop')
        while True:
            # TODO read more data if this isnt long enough
            # read a bunch more until no more data, or construct the bytes-left
            # of the packet and read that much more?
            # TODO read only one byte, then construct length from next bytes as
            # server batch sends data
            data = self.conn.recv(1024)
            if not data:
                self.connected = False
                self.call_on_disconnect()
            if not self.connected:
                logger.info(f'{self.client_id} Disconnected')
                return

            try:
                packet = self.validator.validate_packet(data)
                logger.debug(packet)
                self.handle_packet(packet)
            except PacketValidatorError as e:
                logger.error(e)
                logger.error('Offending data: %s', '\\x'.join(
                    f"{byte:02x}" for byte in data))

    def handle_packet(self, packet):
        # TODO break this up
        if packet.command_type == packets.CONNACK_BYTE:
            # TODO This should only be in the initial handshake, move from here?
            self.call_on_connect()

        if packet.command_type == packets.PUBLISH_BYTE:
            # qos 2 first because we dont call on message until the handshake
            # is complete
            if packet.qos == 2:
                received = True
                self.messages.add(packet, received)
                return

            # messages received
            self.call_on_message(packet.topic, packet.payload)

            # if qos 1 send puback regardless, no dup bit required
            if packet.qos == 1:
                puback_packet = self.pg.create_puback_packet(packet.packet_id)
                self.send(puback_packet.raw_bytes)

        if packet.command_type == packets.PUBACK_BYTE:
            # qos 1 acknowledgement
            self.messages.acknowledge(packet)

        if packet.command_type == packets.PUBREC_BYTE:
            # qos 2 acknowledgement
            self.messages.acknowledge(packet)

        if packet.command_type == packets.PUBREL_BYTE:
            # qos 2 acknowledgement
            message = self.messages.acknowledge(packet)

            # here the handshake is complete for qos 2 messages so we can
            # process it
            self.call_on_message(message.packet.topic, message.packet.payload)

        if packet.command_type == packets.PUBCOMP_BYTE:
            # qos 2 acknowledgement
            # nothing to send
            self.messages.acknowledge(packet)

        if packet.command_type == packets.DISCONNECT_BYTE:
            self.connected = False
            self.call_on_disconnect()

    def send(self, data):
        # TODO is this thread safe?
        logger.debug('Sending %s', '\\x'.join(f"{byte:02x}" for byte in data))
        self.conn.sendall(data)

        # def ping_manager(self):
    #     if not self.connected:
    #         return
    #     # TODO make this timer based which resets on every comms with server
    #     # (publishing or acknowloging)
    #     # TODO make this config option
    #     while True:
    #         self.ping_server()
    #         sleep(self.keep_alive - 1)

    # def ping_server(self):
    #     ping_packet = b'\xc0\x00'  # MQTT PINGREQ
    #     self.conn.sendall(ping_packet)
