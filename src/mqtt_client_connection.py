import socket
import random
import string
from time import sleep

from packet_handler import PacketHandler
from packet_generator import PacketGenerator
import packets


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
        self.pg = PacketGenerator()

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

        server_response = self.negotiate_connection_to_server(timeout)

        response = PacketHandler(server_response).handle_packet()

        if response.success:
            print('We connected!')
            self.connected = True
            self.call_on_connect()
        else:
            print(f'Connection refused {response.reason}')
            self.connected = False

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
            self.send(connect_packet)
            print('Connection packet sent, waiting for response...', end='')

            self.conn.settimeout(timeout)
            data = self.conn.recv(4)
        except TimeoutError:
            print('No response from server.')
            return
        finally:
            self.conn.settimeout(None)

        return data

    def publish(self, topic, payload, qos, retain):
        # TODO qos
        if not self.connected:
            print(f'Cant publish to {topic}, not connected to server')
            return

        pub_packet = self.pg.create_publish_packet(topic, payload, qos, retain)
        self.send(pub_packet)

    def subscribe(self, topic):
        # TODO qos
        if not self.connected:
            print(f'Cant subscribe to {topic}, not connected to server')
            return

        sub_packet = self.pg.create_subscribe_packet(topic)
        self.send(sub_packet)

    def loop(self):
        print('Entering loop')
        while True:
            # TODO read more data if this isnt long enough
            # read a bunch more until no more data, or construct the bytes-left
            # of the packet and read that much more?
            data = self.conn.recv(1024)
            if not data:
                self.connected = False
                self.call_on_disconnect()
            if not self.connected:
                print(f'{self.client_id} Disconnected')
                return

            print(f'recv {data}')
            response = PacketHandler(data).handle_packet()
            self.handle_response(response)

    def handle_response(self, response):
        print(f'Handling response: {response}')

        if not response.success:
            print(f'Not successful {response.reason}')
            return

        if response.command == packets.CONNACK_BYTE:
            # This should only be in the initial handshake, move from here?
            self.call_on_connect()
        if response.command == packets.PUBLISH_BYTE:
            self.call_on_message(response.data.get('topic'),
                                 response.data.get('payload'))
        if response.command == packets.DISCONNECT_BYTE:
            self.connected = False
            self.call_on_disconnect()

    def send(self, data):
        # print(f'Sending {data.hex()}')
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
