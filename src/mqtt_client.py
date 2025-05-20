import socket
import random
import string
from time import sleep
import threading

from packet_handler import PacketHandler


class MQTTClient:
    def __init__(self, address, port, client_id=None, keep_alive=60):
        self.address = address
        self.port = port
        self.keep_alive = keep_alive
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_id = client_id if client_id is not None else self.generate_random_client_id()
        # callback funcs
        self.on_connect = None
        # TODO link to disconnect on disconnect
        self.on_disconnect = None
        self.on_message = None
        # keepalive duration
        self.ping_thread = None

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def connect(self):
        try:
            self.conn.connect((self.address, self.port))
            # self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except ConnectionRefusedError:
            print("Couldn't connect to server")
            return

        print(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        # GPT generated for testing
        # TODO generate connection packet
        connect_packet = bytearray(
            b'\x10\x21\x00\x04MQTT\x04\x02\x00<\x00\x15PYMQTTClient-00000000')

        self.conn.sendall(connect_packet)
        print('connection packet sent')
        data = self.conn.recv(4)
        handler = PacketHandler(data)
        response = handler.handle_packet()

        if response.success:
            # TODO link to on_connect method here
            print('We connected')
        else:
            print(f'Couldnt connect {response.reason}')
            return

        self.ping_thread = threading.Thread(target=self.ping_manager)
        self.ping_thread.start()

        self.subscribe()
        self.publish()

    def subscribe(self):
        sleep(1)
        # GPT generated for testing
        # TODO generate subscribe packet
        mqtt_subscribe_packet = b'\x82\x07\x00\x01\x00\x02a/\x00'  # Subscribe to "a/"

        self.conn.sendall(mqtt_subscribe_packet)

    def publish(self, topic=None, payload=None):
        pub_packet = bytearray(
            b'\x30\x0a\x00\x02b/b_test')

        self.conn.sendall(pub_packet)

    def ping_manager(self):
        # TODO make this timer based which resets on every comms with server
        # (publishing or acknowloging)
        while True:
            self.ping_server()
            sleep(self.keep_alive - 1)

    def ping_server(self):
        print('pinging')
        ping_packet = b'\xc0\x00'  # MQTT PINGREQ
        self.conn.sendall(ping_packet)

    def loop(self):
        print('Entering loop')
        while True:
            # TODO read more data if this isnt long enough
            data = self.conn.recv(1024)
            if not data:
                print(f'{self.client_id} Disconnected')
                return
            print(f'recv {data}')
            response = PacketHandler(data).handle_packet()
            # TODO link to on_message method here
            print(response)


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')
    client.connect()
    client.loop()
