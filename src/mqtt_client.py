import socket
import random
import string
from time import sleep
import threading

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
        # callback funcs
        self.on_connect = self._on_connect
        # TODO link to disconnect on disconnect
        self.on_disconnect = self._on_disconnect
        self.on_message = self._on_message
        # internals
        self._ping_thread = None
        self._loop_thread = None

    def _on_connect(self):
        pass

    def _on_disconnect(self):
        pass

    def _on_message(self):
        pass

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def connect(self):
        # TODO handle non connection
        try:
            self.conn.connect((self.address, self.port))
        except ConnectionRefusedError:
            print("Couldn't connect to server")
            return

        print(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        connect_packet = PacketGenerator().create_connect_packet(client_id=self.client_id)

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

    def subscribe(self, topic):
        print(f'Subscribing to {topic}')
        # TODO this should add subscritions to a list to subscribe to on connect
        # OR specify that subscriptions should go in the  on_connect method
        mqtt_subscribe_packet = PacketGenerator().create_subscribe_packet(topic)
        print(mqtt_subscribe_packet)
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
        self._loop_thread = threading.Thread(target=self.loop)
        self._loop_thread.start()

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
            self.handle_response(response)

    def handle_response(self, response):
        print(f'Handling response: {response}')
        if not response.success:
            print(f'Not successful')
            return

        if response.command == 0x30:
            self.on_message()


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')

    def message_handler():
        print('On message called')

    client.on_message = message_handler
    client.connect()
    client.subscribe('a/')
    client.subscribe('test/')
    client.start_loop()

    publish_idx = 0

    while True:
        print('we still here...')
        sleep(1)
        publish_idx += 1
        if publish_idx == 10:
            client.publish('test/', 'test payload')
            publish_idx = 0
