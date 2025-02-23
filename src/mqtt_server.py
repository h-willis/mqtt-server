import socket
from mqtt_connection import MQTTConnection
from time import sleep

clients = []
topics = {}


class MQTTServer:
    def __init__(self):
        print('Starting server...')

    def add_new_subscription(self, topic, client_id):
        try:
            topics[topic].append(client_id)
        except KeyError:
            topics[topic] = [client_id]

    def run(self):
        host = 'localhost'
        port = 1883

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

            server_socket.bind((host, port))

            # queue 5 connections
            # TODO make bigger as and when needed
            server_socket.listen(5)
            print(f'Server listening on port {port}')

            while True:
                try:
                    conn, addr = server_socket.accept()
                    print(f'Connection from {addr}')

                    client = MQTTConnection(
                        conn, on_new_subscription=self.add_new_subscription)
                    if (client.validate_connection()):
                        clients.append(client)
                        client.start()

                    self.publish_sys_info()

                except KeyboardInterrupt:
                    break

        print('Exiting')

    def publish_sys_info(self):
        while True:
            sleep(5)
            self.publish('$SYS/info', 'Some info')

    def publish(self, topic, payload, qos=0):
        command_byte = 0b00110000
        topic_length = len(topic)
        encoded_topic = topic.encode('utf-8')
        encoded_payload = payload.encode('utf-8')

        # variable header length + topic length + length of topic and payload (sometimes + packet_id if qos > 0)
        length = 1 + 2 + topic_length + len(encoded_payload)

        data = bytearray(
            [command_byte, length, (topic_length << 8) & 0xff, topic_length & 0xff])
        data.extend(encoded_topic)
        data.extend(encoded_payload)

        print(f'publish: {data}')

        clients[0].conn.send(data)


if __name__ == '__main__':
    MQTTServer().run()
