from time import sleep
import threading

from mqtt_client_connection import MQTTClientConnection

# TODO handle shutdown gracefully and kill threads


class MQTTClient:
    def __init__(self, address, port, client_id=None, keep_alive=60):
        self.keep_alive = keep_alive
        self.connection = MQTTClientConnection(
            address, port, client_id, keep_alive)

        # internals
        # TODO move these
        self._ping_thread = None
        self._loop_thread = None

    def set_on_connect_callback(self, callback):
        self.connection.on_connect = callback

    def set_on_disconnect_callback(self, callback):
        self.connection.on_disconnect = callback

    def set_on_message_callback(self, callback):
        # TODO check topic and payload are in callback?
        self.connection.on_message = callback

    def connect(self, timeout=1):
        """ Blocking method that attempts to connect to the server.
        Optional timeout
        """
        self.connection.connect(timeout)

    def publish(self, topic=None, payload=None, qos=0, retain=False):
        if qos > 2 or qos < 0:
            print(f'Invalid qos value {qos}')
            return

        self.connection.publish(topic, payload, qos, retain)

    def subscribe(self, topic, qos=0):
        if qos > 2 or qos < 0:
            print(f'Invalid qos value {qos}')
            return

        self.connection.subscribe(topic, qos)

    @property
    def connected(self):
        return self.connection.connected

    def start_loop(self):
        self._loop_thread = threading.Thread(target=self.connection.loop)
        self._loop_thread.start()


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')

    def message_handler(topic, payload):
        print(f'ON MESSAGE Message recieved {topic}: {payload}')

    def connect_handler():
        print('ON CONNECT called')
        client.subscribe('testsubqos2/', 2)
        client.start_loop()

    def disconnect_handler():
        print('ON DISCONNECT called')
        client.connect()

    client.set_on_message_callback(message_handler)
    client.set_on_connect_callback(connect_handler)
    client.set_on_disconnect_callback(disconnect_handler)

    def connection_loop():
        while not client.connected:
            client.connect(timeout=3)

    connection_loop()

    publish_idx = 0

    while True:
        # print('we still here...')
        sleep(1)

        if not client.connected:
            connection_loop()

        publish_idx += 1
        if publish_idx == 3:
            # client.publish('test/', 'test payload', 1)
            pass
        if publish_idx == 6:
            client.publish('testpubqos2/', 1, 2, True)
        # if publish_idx == 9:
        #     # client.publish(1, 1)
        #     publish_idx = 0
