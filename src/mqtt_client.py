import socket
import random
import string

from packet_handler import PacketHandler


class MQTTClient:
    def __init__(self, address, port, client_id=None):
        self.address = address
        self.port = port
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_id = client_id if client_id is not None else self.generate_random_client_id()
        # callback funcs
        self.on_connect = None
        self.on_message = None

    def generate_random_client_id(self):
        return 'PYMQTTClient-'.join(random.choices(string.ascii_letters + string.digits, k=8))

    def connect(self):
        try:
            self.conn.connect((self.address, self.port))
        except ConnectionRefusedError:
            print("Couldn't connect to server")
            return

        print(
            f'Client: {self.client_id} connected to {self.address}:{self.port}')

        # GPT generated for testing
        connect_packet = bytearray(
            b'\x10\x1f\x00\x04MQTT\x04\x02\x00<\x00\x13PYMQTTClient-00000000')

        self.conn.send(connect_packet)
        data = self.conn.recv(1024)
        handler = PacketHandler(data)
        response = handler.handle_packet()

        if response.success:
            print('We connected')
        else:
            print('Couldnt connect')

        while True:
            data = self.conn.recv(1024)
            print(f'recv {data}')

    def handle_connack_response(self):
        # Receive the data (this could be more dynamic based on the packet size)
        data = self.conn.recv(1024)

        print(f'Response: {data}')
        success = True

        # Check if the packet length is valid and it's a CONNACK packet
        if len(data) < 4:
            print("Invalid packet length")
            success = False
            return success

        # CONNACK format:
        # Byte 1: Fixed header (always 0x20 for CONNACK)
        # Byte 2: Remaining length (typically 2 for CONNACK)
        # Byte 3: Return code flags
        # Byte 4: Return code (0x00 = Connection Accepted, etc.)

        fixed_header = data[0]
        remaining_length = data[1]

        # Ensure the packet starts with the correct CONNACK header (0x20)
        if fixed_header != 0x20:
            print("Invalid CONNACK packet")
            success = False
            return success

        # Get the response flags and return code
        response_flags = data[2]
        return_code = data[3]

        # Check return code and print the result
        if return_code == 0x00:
            print("Connection Accepted")
        elif return_code == 0x01:
            print("Connection Refused - Unacceptable Protocol Version")
            success = False
        elif return_code == 0x02:
            print("Connection Refused - Identifier Rejected")
            success = False
        elif return_code == 0x03:
            print("Connection Refused - Broker Unavailable")
            success = False
        elif return_code == 0x04:
            print("Connection Refused - Bad Username or Password")
            success = False
        elif return_code == 0x05:
            print("Connection Refused - Not Authorized")
            success = False
        else:
            print(f"Unknown return code: {return_code}")
            success = False

        # Optionally handle additional flags or scenarios
        if response_flags != 0:
            print(f"Response flags: {response_flags}")
        return success


if __name__ == '__main__':
    MQTTClient('127.0.0.1', 1883, 'PYMQTTClient-00000000').connect()
