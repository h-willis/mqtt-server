from mqtt_client_connection import MQTTClientConnection
from time import sleep
import threading

from logging_setup import LoggerSetup
import logging  # for initial log level
LoggerSetup.setup(log_level=logging.INFO)
logger = LoggerSetup.get_logger(__name__)
logger.debug('MQTT Client module initialized')

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
            logger.error('Invalid qos value in publish %s', qos)
            return

        self.connection.publish(topic, payload, qos, retain)

    def subscribe(self, topic, qos=0):
        if qos > 2 or qos < 0:
            logger.error('Invalid qos value in subscribe %s', qos)
            return

        self.connection.subscribe(topic, qos)

    def set_will(self, topic, payload, qos=0, retain=False):
        logging.info('Setting lwt to: %s %s %s %s',
                     topic, payload, qos, retain)
        self.connection.set_will(topic, payload, qos, retain)

    @property
    def connected(self):
        return self.connection.connected

    def start_loop(self):
        self._loop_thread = threading.Thread(target=self.connection.loop)
        self._loop_thread.start()


if __name__ == '__main__':
    client = MQTTClient('localhost', 1883, 'PYMQTTClient-00000000')
    client.set_will('will_tip', 'will payload', 1, True)

    def message_handler(topic, payload):
        logger.debug('ON MESSAGE Message recieved %s: %s', topic, payload)

    def connect_handler():
        logger.debug('ON CONNECT called')
        client.subscribe('testsubqos2/', 2)
        client.start_loop()

    def disconnect_handler():
        logger.debug('ON DISCONNECT called')
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
