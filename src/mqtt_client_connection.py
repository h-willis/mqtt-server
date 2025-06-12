import socket
import random
import string
from time import sleep

# packet stuff
from packet_validator import PacketValidator, PacketValidatorError
from packet_generator import PacketGenerator
import packets

from mqtt_client_messages import MQTTClientMessages


class MQTTClientConnection:
    def __init__(self, address, port, client_id=None, keep_alive=60):
        self.address = address
        self.port = port
        self.keep_alive = keep_alive
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_id = client_id if client_id else self.generate_random_client_id()

        self.connected = False

        self.on_connect = lambda: None
        self.on_disconnect = lambda: None
        self.on_message = lambda topic, payload: None

        # needs to be instance to handle increasing packet ids
        self.pg = PacketGenerator(self.send)
        self.validator = PacketValidator(self.send)

        self.messages = MQTTClientMessages()

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def connect(self, timeout):
        print('Attempting to connect to MQTT server')

        if not self.connect_socket_to_server(timeout):
            self.connected = False
            print('Failed to connect to server')
            return

        print(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        # TODO this could be better
        server_response = self.negotiate_connection_to_server(timeout)

        try:
            # TODO actually check this is a connack packet
            packet = self.validator.validate_packet(server_response)
        except PacketValidatorError as e:
            # invalid packet for some reason
            print(e.message)
            self.connected = False
            return

        print('We connected!')
        self.connected = True
        self.call_on_connect()

        # TODO ping threading as optional start
        # self.ping_thread = threading.Thread(target=self.ping_manager)
        # self.ping_thread.start()

    def call_on_connect(self):
        try:
            self.on_connect()
        except Exception as e:
            print('Error while calling on_connect callback:')
            print(e)

    def call_on_disconnect(self):
        try:
            self.on_disconnect()
        except Exception as e:
            print('Error while calling on_disconnect callback:')
            print(e)

    def call_on_message(self, topic=None, payload=None):
        try:
            self.on_message(topic, payload)
        except Exception as e:
            print('Error while calling on_message callback:')
            print({e})

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
            client_id=self.client_id)
        data = None

        try:
            connect_packet.send()
            print('Connection packet sent, waiting for response...', end='')

            self.conn.settimeout(timeout)
            data = self.conn.recv(4)
        except TimeoutError:
            print('No response from server.')
            return None
        finally:
            self.conn.settimeout(None)

        return data

    def publish(self, topic, payload, qos, retain):
        # TODO dup might not be needed here
        if not self.connected:
            print(f'Cant publish to {topic}, not connected to server')
            return

        pub_packet = self.pg.create_publish_packet(topic, payload, qos, retain)
        if qos == 1:
            self.messages.add(pub_packet)
        if qos == 2:
            self.messages.add(pub_packet)
        self.send(pub_packet.raw_bytes)

    def subscribe(self, topic, qos):
        if not self.connected:
            print(f'Cant subscribe to {topic}, not connected to server')
            return

        sub_packet = self.pg.create_subscribe_packet(topic, qos)
        sub_packet.send()

    def loop(self):
        print('Entering loop')
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
                print(f'{self.client_id} Disconnected')
                return

            try:
                packet = self.validator.validate_packet(data)
                print(packet)
                self.handle_packet(packet)
            except PacketValidatorError as e:
                print(e)

    def handle_packet(self, packet):
        # TODO break this up
        if packet.command_type == packets.CONNACK_BYTE:
            # TODO This should only be in the initial handshake, move from here?
            self.call_on_connect()

        if packet.command_type == packets.PUBLISH_BYTE:
            # qos 2 first because we dont on on message until the handshake is complete
            if packet.qos == 2:
                self.messages.add(packet, 'PUBREC')

                # we send PUBREC here and store message for handshake
                pubrec_packet = self.pg.create_pubrec_packet(packet.packet_id)
                pubrec_packet.send()
                return

            # messages received
            self.call_on_message(packet.topic, packet.payload)

            # if qos 1 send puback
            if packet.qos == 1:
                puback_packet = self.pg.create_puback_packet(packet.packet_id)
                self.send(puback_packet.raw_bytes)

        if packet.command_type == packets.PUBACK_BYTE:
            # qos 1 acknowledgement
            self.messages.acknowledge(packet)

        if packet.command_type == packets.PUBREC_BYTE:
            # qos 2 acknowledgement
            # send PUBREL
            self.messages.acknowledge(packet)
            pubrel_packet = self.pg.create_pubrel_packet(packet.packet_id)
            self.send(pubrel_packet.raw_bytes)

        if packet.command_type == packets.PUBREL_BYTE:
            # qos 2 acknowledgement
            # SEND PUBCOMP
            pubcomp_packet = self.pg.create_pubcomp_packet(
                packet.packet_id)
            self.send(pubcomp_packet.raw_bytes)

            message = self.messages.acknowledge(packet)

            # here the handshake is complete for qos 2 messages so we can
            # process it
            self.call_on_message(message.packet.topic,
                                 message.packet.payload)

        if packet.command_type == packets.PUBCOMP_BYTE:
            # qos 2 acknowledgement
            # nothing to send
            self.messages.acknowledge(packet)

        if packet.command_type == packets.DISCONNECT_BYTE:
            self.connected = False
            self.call_on_disconnect()

    def send(self, data):
        print('Sending', end=' ')
        print('\\x'.join(f"{byte:02x}" for byte in data))
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
