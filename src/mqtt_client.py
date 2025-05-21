import socket
import random
import string
from time import sleep
import threading

from packet_handler import PacketHandler
from packet_generator import PacketGenerator


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
        self.loop_thread = None

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
        connect_packet = PacketGenerator().create_connect_packet(
            client_id='PYMQTTClient-00000000')

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

        # TODO ping threading as optional start
        # self.ping_thread = threading.Thread(target=self.ping_manager)
        # self.ping_thread.start()

        # TODO bring these outside
        self.subscribe()
        self.publish(topic="b/", payload='b_test')

    def subscribe(self):
        # TODO this should add subscritions to a list to subscribe to on connect
        # OR specify that subscriptions should go in the  on_connect method
        sleep(1)
        # GPT generated for testing
        # TODO generate subscribe packet
        mqtt_subscribe_packet = b'\x82\x07\x00\x01\x00\x02a/\x00'  # Subscribe to "a/"

        self.conn.sendall(mqtt_subscribe_packet)

    def publish(self, topic=None, payload=None):
        pub_packet = PacketGenerator().create_publish_packet(topic, payload)

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

    def start_loop(self):
        self.loop_thread = threading.Thread(target=self.loop)
        self.loop_thread.start()

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

            print(response)
            if (response.command == 0x30):
                if self.on_message:
                    self.on_message()


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')

    def message_handler():
        print('On message called')

    client.on_message = message_handler
    client.connect()
    client.start_loop()

    while True:
        print('we still here...')
        sleep(1)
