# handlers for each of the expected MQTT packets:
import packets
from pprint import pformat

from mqtt_packet import MQTTPacket

"""
1	    CONNECT	        Client request to connect to a broker.
2	    CONNACK	        Connection acknowledgment from the broker.
3	    PUBLISH	        Message sent from a client to a topic.
4	    PUBACK	        Acknowledgment for QoS 1 messages.
5	    PUBREC  	    Received acknowledgment for QoS 2 messages(first step).
6	    PUBREL	        Release acknowledgment for QoS 2 messages(second step).
7	    PUBCOMP	        Completion acknowledgment for QoS 2 messages(final step).
8	    SUBSCRIBE	    Client request to subscribe to a topic.
9	    SUBACK	        Acknowledgment for a subscription request.
10	    UNSUBSCRIBE	    Client request to unsubscribe from a topic.
11	    UNSUBACK	    Acknowledgment for an unsubscribe request.
12	    PINGREQ 	    Keep - alive request from the client.
13	    PINGRESP	    Response to a keep - alive request.
14	    DISCONNECT	    Notification that a client is disconnecting.
15	    AUTH(MQTT 5.0)	Used for enhanced authentication in MQTT 5.
"""

# does this send responses or return a response to send?
# could be if it returns something from a handle_packet then it needs to be sent
# might get difficult for handshakey stuff for qos 1 and 2 messages
# might need a Message class to track unacked messages or stuff like that


COMMAND_BYTES = {
    0x00: "UNKNOWN",
    0x10: "CONNECT",
    0x20: "CONNACK",
    0x30: "PUBLISH",
    0x40: "PUBACK",
    0x50: "PUBREC",
    0x60: "PUBREL",
    0x70: "PUBCOMP",
    0x80: "SUBSCRIBE",
    0x90: "SUBACK",
    0xA0: "UNSUBSCRIBE",
    0xB0: "UNSUBACK",
    0xC0: "PINGREQ",
    0xD0: "PINGRESP",
    0xE0: "DISCONNECT",
    0xF0: "AUTH"
}


class PacketValidatorError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(f"Error while handling packet: {message}")


# class HandlerResponse:
#     def __init__(self, command, data=None):
#         self.command = command
#         # topic, payload, pid
#         self.data = data if data is not None else {}

#     def __str__(self):
#         # TODO fix this command bytes masking
#         return f'{COMMAND_BYTES[self.command & 0xf0]} | Data:\r\n{pformat(self.data)}'

# TODO check through all this as GPT generated


class PacketValidator:
    def __init__(self, send_func):
        self.packet = None
        self.handlers = {
            packets.CONNECT_BYTE: self.handler_not_implemented,     # "CONNECT"
            packets.CONNACK_BYTE: self.handle_connack,              # "CONNACK"
            packets.PUBLISH_BYTE: self.handle_publish,              # "PUBLISH"
            packets.PUBACK_BYTE: self.handle_puback,                # "PUBACK"
            packets.PUBREC_BYTE: self.handle_pubrec,                # "PUBREC"
            packets.PUBREL_BYTE: self.handle_pubrel,                # "PUBREL"
            packets.PUBCOMP_BYTE: self.handle_pubcomp,              # "PUBCOMP"
            packets.SUBSCRIBE_BYTE: self.handler_not_implemented,   # "SUBSCRIBE"
            packets.SUBACK_BYTE: self.handle_suback,                # "SUBACK"
            packets.UNSUBSCRIBE_BYTE: self.handler_not_implemented,  # "UNSUBSCRIBE"
            packets.UNSUBACK_BYTE: self.handler_not_implemented,    # "UNSUBACK"
            packets.PINGREQ_BYTE: self.handler_not_implemented,     # "PINGREQ"
            packets.PINGRESP_BYTE: self.handle_pingresp,            # "PINGRESP"
            packets.DISCONNECT_BYTE: self.handler_not_implemented,  # "DISCONNECT"
            packets.AUTH_BYTE: self.handler_not_implemented,        # "AUTH"
        }
        self.send_func = send_func

    def validate_packet(self, packet):
        datapr = ', '.join(f"{byte:02x}" for byte in packet)
        print(f'recv {datapr}', end='')

        # just look at top 4 bytes
        self.packet = packet
        if not self.packet:
            print('\r')
            raise PacketValidatorError("No packet to handle")

        # masks out flags
        command = self.packet[0] & 0xf0

        if command not in COMMAND_BYTES:
            # basically if it's 0
            print('\r')
            raise PacketValidatorError("Invalid command byte")

        print(f' | {COMMAND_BYTES[command]}')

        handler = self.handlers[command]
        return handler()

    def handle_connack(self):
        # Check if the packet length is valid and it's a CONNACK packet
        if len(self.packet) < 4:
            raise PacketValidatorError("Invalid packet length")

        # CONNACK format:
        # Byte 1: Fixed header (always 0x20 for CONNACK)
        # Byte 2: Remaining length (typically 2 for CONNACK)
        # Byte 3: Return code flags
        # Byte 4: Return code (0x00 = Connection Accepted, etc.)

        fixed_header = self.packet[0]
        remaining_length = self.packet[1]

        if fixed_header != 0x20:
            raise PacketValidatorError("Invalid CONNACK packet header")

        # Get the response flags and return code
        response_flags = self.packet[2]
        return_code = self.packet[3]

        # Check return code and print the result
        if return_code == 0x00:
            print("Connection Accepted")
        elif return_code == 0x01:
            raise PacketValidatorError(
                "Connection Refused - Unacceptable Protocol Version")
        elif return_code == 0x02:
            raise PacketValidatorError(
                "Connection Refused - Identifier Rejected")
        elif return_code == 0x03:
            raise PacketValidatorError(
                "Connection Refused - Broker Unavailable")
        elif return_code == 0x04:
            raise PacketValidatorError(
                "Connection Refused - Bad Username or Password")
        elif return_code == 0x05:
            raise PacketValidatorError("Connection Refused - Not Authorized")
        else:
            raise PacketValidatorError(f"Unknown return code: {return_code}")

        return MQTTPacket(fixed_header, self.packet, data={'flags': response_flags}, send_func=self.send_func)

    def handle_publish(self):
        if len(self.packet) < 4:
            raise PacketValidatorError("Invalid PUBLISH packet length")

        fixed_header = self.packet[0]
        packet_type = fixed_header & 0xF0
        if packet_type != 0x30:
            # TODO not sure this check is required
            raise PacketValidatorError("Invalid PUBLISH packet type")

        # Extract flags
        dup_flag = (fixed_header & 0x08) >> 3
        qos_level = (fixed_header & 0x06) >> 1
        if qos_level not in [0, 1, 2]:
            raise PacketValidatorError(f"Invalid qos level: {qos_level}")
        retain = fixed_header & 0x01

        # Decode Remaining Length (MQTT uses a variable-length encoding)
        remaining_length, consumed_bytes = self._decode_remaining_length(
            self.packet[1:])
        index = 1 + consumed_bytes

        if len(self.packet) < index + remaining_length:
            raise PacketValidatorError("Incomplete PUBLISH packet")

        # Parse Topic Name
        topic_length = int.from_bytes(self.packet[index:index + 2], 'big')
        # topic_length = (self.packet[index] << 8) | self.packet[index + 1]
        index += 2
        if index + topic_length > len(self.packet):
            raise PacketValidatorError("Incomplete topic in PUBLISH packet")

        topic = self.packet[index:index + topic_length].decode('utf-8')
        index += topic_length

        # Packet Identifier (if QoS > 0)
        packet_id = None
        if qos_level > 0:
            if index + 2 > len(self.packet):
                raise PacketValidatorError(
                    "Expected Packet Identifier missing for QoS > 0")
            # packet_id = (self.packet[index] << 8) | self.packet[index + 1]
            packet_id = int.from_bytes(self.packet[index:index + 2], 'big')
            index += 2

        # Remaining is payload
        payload_bytes = self.packet[index:]
        try:
            payload = payload_bytes.decode('utf-8')
        except UnicodeDecodeError:
            payload = payload_bytes  # fallback to raw bytes if not UTF-8

        return MQTTPacket(
            fixed_header,
            self.packet,
            data={
                'topic': topic,
                'payload': payload,
                'qos': qos_level,
                'dup': dup_flag,
                'retain': retain,
                'packet_id': packet_id,
            }, send_func=self.send_func
        )

    def handle_puback(self):
        if len(self.packet) != 4:
            raise PacketValidatorError("Invalid PUBACK packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x40:
            raise PacketValidatorError("Invalid PUBACK packet header")

        remaining_length = self.packet[1]
        if remaining_length != 0x02:
            raise PacketValidatorError("Invalid PUBACK remaining length")

        packet_id = (self.packet[2] << 8) | self.packet[3]
        packet_id = int.from_bytes(self.packet[2:], 'big')

        # print(f"Received PUBACK for Packet ID: {packet_id}")

        return MQTTPacket(fixed_header, self.packet, data={'packet_id': packet_id}, send_func=self.send_func)

    def handle_pubrec(self):
        if len(self.packet) != 4:
            raise PacketValidatorError("Invalid PUBREC packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x50:
            raise PacketValidatorError("Invalid PUBREC packet header")

        remaining_length = self.packet[1]
        if remaining_length != 0x02:
            raise PacketValidatorError("Invalid PUBREC remaining length")

        packet_id = int.from_bytes(self.packet[2:], 'big')

        return MQTTPacket(fixed_header, self.packet, data={'packet_id': packet_id}, send_func=self.send_func)

    def handle_pubrel(self):
        if len(self.packet) != 4:
            raise PacketValidatorError("Invalid PUBREL packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x62:
            raise PacketValidatorError("Invalid PUBREL packet header")

        remaining_length = self.packet[1]
        if remaining_length != 0x02:
            raise PacketValidatorError("Invalid PUBREL remaining length")

        packet_id = int.from_bytes(self.packet[2:], 'big')

        return MQTTPacket(fixed_header, self.packet, data={'packet_id': packet_id}, send_func=self.send_func)

    def handle_pubcomp(self):
        if len(self.packet) != 4:
            raise PacketValidatorError("Invalid PUBCOMP packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x70:
            raise PacketValidatorError("Invalid PUBCOMP packet header")

        remaining_length = self.packet[1]
        if remaining_length != 0x02:
            raise PacketValidatorError("Invalid PUBCOMP remaining length")

        packet_id = int.from_bytes(self.packet[2:], 'big')

        return MQTTPacket(fixed_header, self.packet, data={'packet_id': packet_id}, send_func=self.send_func)

    def handle_suback(self):
        if len(self.packet) < 5:
            raise PacketValidatorError("Invalid SUBACK packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x90:
            raise PacketValidatorError("Invalid SUBACK packet header")

        # Decode Remaining Length using the variable-length method
        remaining_length, consumed_bytes = self._decode_remaining_length(
            self.packet[1:])
        index = 1 + consumed_bytes

        if len(self.packet) < index + remaining_length:
            raise PacketValidatorError("Incomplete SUBACK packet")

        # Packet Identifier (2 bytes)
        # packet_id = (self.packet[index] << 8) | self.packet[index + 1]
        packet_id = int.from_bytes(self.packet[index:index + 2], 'big')
        index += 2

        # Return codes (one byte per subscription topic)
        # TODO more readable
        return_codes = list(self.packet[index:index + (remaining_length - 2)])

        # print(
        #     f"Received SUBACK: Packet ID={packet_id}, Return Codes={return_codes}")

        return MQTTPacket(
            fixed_header,
            self.packet,
            data={
                'packet_id': packet_id,
                'return_codes': return_codes,
            }, send_func=self.send_func
        )

    def handle_pingresp(self):
        print("TODO somehow use this for the client to know when it's connection is dead")
        return MQTTPacket(self.packet[0], self.packet, send_func=self.send_func)

    def handler_not_implemented(self):
        raise PacketValidatorError('Handler not implemented')

    def _decode_remaining_length(self, data):
        """
        GPT
        Decodes MQTT Remaining Length field from the given bytes.

        Args:
            data (bytes or bytearray): bytes starting from Remaining Length field.

        Returns:
            tuple: (remaining_length_value, bytes_consumed)

        Raises:
            PacketHandlerError: if malformed length or length too long.
        """
        multiplier = 1
        value = 0
        index = 0

        while True:
            if index >= len(data):
                raise PacketValidatorError(
                    "Malformed Remaining Length field: incomplete data")

            encoded_byte = data[index]
            value += (encoded_byte & 0x7F) * multiplier

            if (encoded_byte & 0x80) == 0:  # MSB not set, done reading
                break

            multiplier *= 128
            # equivalent to 128*128*128 (max allowed multiplier)
            if multiplier > 128**3:
                raise PacketValidatorError(
                    "Malformed Remaining Length field: length too long")

            index += 1

        return value, index + 1
