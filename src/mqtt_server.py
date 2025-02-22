import socket
from client import Client

clients = []


class MQTTServer:
    def __init__(self):
        print('Starting server...')

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

                    client = Client(conn)
                    if (client.validate_connection()):
                        client.run()

                except KeyboardInterrupt:
                    break
                    # data = conn.recv(1024)
                    # print(f'Raw received: {data}')

                    # if data:
                    #     print(f"Received: {data.decode()}")

        print('Exiting')


if __name__ == '__main__':
    MQTTServer().run()
