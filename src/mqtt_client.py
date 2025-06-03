import socket
import random
import string
from time import sleep
import threading

import packets
from packet_handler import PacketHandler
from packet_generator import PacketGenerator

# TODO handle shutdown gracefully and kill threads


class MQTTClient:
    def __init__(self, address, port, client_id=None, keep_alive=60):
        self.address = address
        self.port = port
        self.keep_alive = keep_alive
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_id = client_id if client_id else self.generate_random_client_id()
        self.connected = False
        # callback funcs
        # TODO wrap these in something so any errors in user provided callbacks
        # dont crash us
        self.on_connect = lambda: None
        self.on_disconnect = lambda: None
        self.on_message = lambda topic, payload: None
        # internals
        self._ping_thread = None
        self._loop_thread = None

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def socket_connected(self):
        try:
            self.conn.sendall(b'')
            return True
        except (OSError, BrokenPipeError):
            return False

    def connect(self, timeout=1):
        """ Blocking method that attempts to connect to the server.
        Optional timeout 
        """
        print(f'Attempting to connect to MQTT server')

        attempts = 0
        while True:
            if self.socket_connected():
                break
            try:
                self.conn.settimeout(1)
                self.conn.connect((self.address, self.port))
                break
            except (ConnectionRefusedError, ConnectionAbortedError):
                attempts += 1
                if attempts > timeout:
                    # TODO more information about failure here
                    print('Failed to connect to server')
                    return
                sleep(1)

        print(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        connect_packet = PacketGenerator().create_connect_packet(client_id=self.client_id)

        attempts = 0

        try:
            self.conn.sendall(connect_packet)
            print('Connection packet sent, waiting for response...', end='')

            # TODO timeout and error handling
            self.conn.settimeout(timeout)
            data = self.conn.recv(4)
        except TimeoutError:
            print('No response from server.')
            return
        finally:
            self.conn.settimeout(None)

        response = PacketHandler(data).handle_packet()

        if response.success:
            print('We connected!')
            self.connected = True
            self.on_connect()
        else:
            print(f'Connection refused {response.reason}')

        # TODO ping threading as optional start
        # self.ping_thread = threading.Thread(target=self.ping_manager)
        # self.ping_thread.start()

    def subscribe(self, topic):
        if not self.connected:
            print(f'Cant subscribe to {topic}, not connected to server')
            return

        sub_packet = PacketGenerator().create_subscribe_packet(topic)
        self.conn.sendall(sub_packet)

    def publish(self, topic=None, payload=None):
        if not self.connected:
            print(f'Cant publish to {topic}, not connected to server')
            return
        pub_packet = PacketGenerator().create_publish_packet(topic, payload)
        self.conn.sendall(pub_packet)

    def ping_manager(self):
        if not self.connected:
            return
        # TODO make this timer based which resets on every comms with server
        # (publishing or acknowloging)
        # TODO make this config option
        while True:
            self.ping_server()
            sleep(self.keep_alive - 1)

    def ping_server(self):
        ping_packet = b'\xc0\x00'  # MQTT PINGREQ
        self.conn.sendall(ping_packet)

    def start_loop(self):
        self._loop_thread = threading.Thread(target=self.loop)
        self._loop_thread.start()

    def loop(self):
        print('Entering loop')
        while True:
            # TODO read more data if this isnt long enough
            # read a bunch more until no more data, or construct the bytes-left
            # of the packet and read that much more?
            data = self.conn.recv(1024)
            if not data:
                self.connected = False
                self.on_disconnect()
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
            self.on_connect()
        if response.command == packets.PUBLISH_BYTE:
            self.on_message(response.data.get('topic'),
                            response.data.get('payload'))
        if response.command == packets.DISCONNECT_BYTE:
            self.connected = False
            self.on_disconnect()


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')

    def message_handler(topic, payload):
        print(f'Message recieved {topic}: {payload}')

    def connect_handler():
        client.subscribe('test/')
        client.start_loop()

    def disconnect_handler():
        client.connect()

    client.on_message = message_handler
    client.on_connect = connect_handler
    client.on_disconnect = disconnect_handler

    while not client.connected:
        client.connect(timeout=3)

    publish_idx = 0

    while True:
        print('we still here...')
        sleep(1)

        publish_idx += 1
        if publish_idx == 3:
            client.publish('test/', 'test payload')
        if publish_idx == 6:
            client.publish('test/', 1)
        if publish_idx == 9:
            client.publish(1, 1)
            publish_idx = 0
