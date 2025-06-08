# handlers for each of the expected MQTT packets:
import packets
from pprint import pprint

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


class PacketHandlerError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(f"Error while handling packet: {message}")


class HandlerResponse:
    def __init__(self, command, data=None):
        self.command = command
        # topic, payload, pid
        self.data = data if data is not None else {}

    def __str__(self):
        return f'{COMMAND_BYTES[self.command]} | Data:\r{pprint(self.data)}'

# TODO check through all this as GPT generated


class PacketHandler:
    def __init__(self):
        self.packet = None
        self.handlers = {
            packets.CONNECT_BYTE: self.handler_not_implemented,     # "CONNECT"
            packets.CONNACK_BYTE: self.handle_connack,              # "CONNACK"
            packets.PUBLISH_BYTE: self.handle_publish,              # "PUBLISH"
            packets.PUBACK_BYTE: self.handle_puback,      # "PUBACK"
            packets.PUBREC_BYTE: self.handler_not_implemented,      # "PUBREC"
            packets.PUBREL_BYTE: self.handler_not_implemented,      # "PUBREL"
            packets.PUBCOMP_BYTE: self.handler_not_implemented,     # "PUBCOMP"
            packets.SUBSCRIBE_BYTE: self.handler_not_implemented,   # "SUBSCRIBE"
            packets.SUBACK_BYTE: self.handle_suback,                # "SUBACK"
            packets.UNSUBSCRIBE_BYTE: self.handler_not_implemented,  # "UNSUBSCRIBE"
            packets.UNSUBACK_BYTE: self.handler_not_implemented,    # "UNSUBACK"
            packets.PINGREQ_BYTE: self.handler_not_implemented,     # "PINGREQ"
            packets.PINGRESP_BYTE: self.handle_pingresp,            # "PINGRESP"
            packets.DISCONNECT_BYTE: self.handler_not_implemented,  # "DISCONNECT"
            packets.AUTH_BYTE: self.handler_not_implemented,        # "AUTH"
        }

    def handle_packet(self, packet):
        # just look at top 4 bytes
        self.packet = packet
        if not self.packet:
            raise PacketHandlerError("No packet to handle")

        # masks out flags
        command = self.packet[0] & 0xf0

        if command not in COMMAND_BYTES:
            # basically if it's 0
            raise PacketHandlerError("Invalid command byte")

        print(f'{COMMAND_BYTES[command]} packet recieved')

        return self.handlers[command]()

    def handle_connack(self):
        # Receive the data (this could be more dynamic based on the packet size)
        print(f'Handling connack for: {self.packet}')

        # Check if the packet length is valid and it's a CONNACK packet
        if len(self.packet) < 4:
            raise PacketHandlerError("Invalid packet length")

        # CONNACK format:
        # Byte 1: Fixed header (always 0x20 for CONNACK)
        # Byte 2: Remaining length (typically 2 for CONNACK)
        # Byte 3: Return code flags
        # Byte 4: Return code (0x00 = Connection Accepted, etc.)

        fixed_header = self.packet[0]
        remaining_length = self.packet[1]

        if fixed_header != 0x20:
            raise PacketHandlerError("Invalid CONNACK packet header")

        # Get the response flags and return code
        response_flags = self.packet[2]
        return_code = self.packet[3]

        # Check return code and print the result
        if return_code == 0x00:
            print("Connection Accepted")
        elif return_code == 0x01:
            raise PacketHandlerError(
                "Connection Refused - Unacceptable Protocol Version")
        elif return_code == 0x02:
            raise PacketHandlerError(
                "Connection Refused - Identifier Rejected")
        elif return_code == 0x03:
            raise PacketHandlerError("Connection Refused - Broker Unavailable")
        elif return_code == 0x04:
            raise PacketHandlerError(
                "Connection Refused - Bad Username or Password")
        elif return_code == 0x05:
            raise PacketHandlerError("Connection Refused - Not Authorized")
        else:
            raise PacketHandlerError(f"Unknown return code: {return_code}")

        return HandlerResponse(command=0x20, data={'flags': response_flags})

    # def handle_publish(self):
    #     print(f'Handling publish for: {self.packet}')

    #     # MQTT Fixed header: byte 1 = control byte, byte 2+ = remaining length
    #     fixed_header = self.packet[0]
    #     qos = (fixed_header & 0b00000110) >> 1
    #     remaining_length = self.packet[1]

    #     # Start of variable header: Topic name (2-byte length + UTF-8 string)
    #     topic_length = int.from_bytes(self.packet[2:4], byteorder='big')
    #     topic_start = 4
    #     topic_end = topic_start + topic_length
    #     topic = self.packet[topic_start:topic_end].decode('utf-8')

    #     # Payload starts immediately after topic (and maybe packet identifier if QoS > 0)
    #     payload_start = topic_end
    #     payload = self.packet[payload_start:].decode('utf-8')

    #     print(f'Topic: {topic}, Payload: {payload}')
    #     pid = None
    #     if qos > 0:
    #         pid = self.packet[topic_end:topic_end + 2]

    #     return HandlerResponse(fixed_header, data={'topic': topic, 'payload': payload, 'pid': pid})

    def handle_publish(self):
        print(f'Handling publish for: {self.packet}')

        if len(self.packet) < 4:
            raise PacketHandlerError("Invalid PUBLISH packet length")

        fixed_header = self.packet[0]
        packet_type = fixed_header & 0xF0
        if packet_type != 0x30:
            # TODO not sure this check is required
            raise PacketHandlerError("Invalid PUBLISH packet type")

        # Extract flags
        dup_flag = (fixed_header & 0x08) >> 3
        qos_level = (fixed_header & 0x06) >> 1
        if qos_level not in [0, 1, 2]:
            raise PacketHandlerError(f"Invalid qos level: {qos_level}")
        retain = fixed_header & 0x01

        # Decode Remaining Length (MQTT uses a variable-length encoding)
        remaining_length, consumed_bytes = self._decode_remaining_length(
            self.packet[1:])
        index = 1 + consumed_bytes

        if len(self.packet) < index + remaining_length:
            raise PacketHandlerError("Incomplete PUBLISH packet")

        # Parse Topic Name
        topic_length = int.from_bytes(self.packet[index:index + 1], 'big')
        # topic_length = (self.packet[index] << 8) | self.packet[index + 1]
        index += 2
        if index + topic_length > len(self.packet):
            raise PacketHandlerError("Incomplete topic in PUBLISH packet")

        topic = self.packet[index:index + topic_length].decode('utf-8')
        index += topic_length

        # Packet Identifier (if QoS > 0)
        packet_id = None
        if qos_level > 0:
            if index + 2 > len(self.packet):
                raise PacketHandlerError(
                    "Expected Packet Identifier missing for QoS > 0")
            # packet_id = (self.packet[index] << 8) | self.packet[index + 1]
            packet_id = int.from_bytes(self.packet[index:index + 1], 'big')
            index += 2

        # Remaining is payload
        payload_bytes = self.packet[index:]
        try:
            payload = payload_bytes.decode('utf-8')
        except UnicodeDecodeError:
            payload = payload_bytes  # fallback to raw bytes if not UTF-8

        print(
            f"Received PUBLISH: topic='{topic}', payload='{payload}', QoS={qos_level}, DUP={dup_flag}, RETAIN={retain}, Packet ID={packet_id}")

        return HandlerResponse(
            command=0x30,
            data={
                'topic': topic,
                'payload': payload,
                'qos': qos_level,
                'dup': dup_flag,
                'retain': retain,
                'packet_id': packet_id,
            }
        )

    # def handle_puback(self):
    #     print(f'Handling PUBACK for: {self.packet}')
    #     return

    #     if len(self.packet) < 4:
    #         return HandlerResponse(
    #             command=packets.PUBACK_BYTE,
    #             success=False,
    #             reason="PUBACK packet too short",
    #         )

    #     fixed_header = self.packet[0]
    #     remaining_length = self.packet[1]

    #     if fixed_header != packets.PUBACK_BYTE:
    #         return HandlerResponse(
    #             command=packets.PUBACK_BYTE,
    #             success=False,
    #             reason=f"Unexpected control byte: {hex(fixed_header)}",
    #         )

    #     if remaining_length != 2:
    #         return HandlerResponse(
    #             command=packets.PUBACK_BYTE,
    #             success=False,
    #             reason=f"Invalid remaining length: {remaining_length}, expected 2",
    #         )

    #     packet_id = int.from_bytes(self.packet[2:4], byteorder='big')

    #     print(f'Received PUBACK for Packet ID: {packet_id}')

    #     # Here you might mark the original publish as complete, remove from inflight, etc.

    #     return HandlerResponse(
    #         command=packets.PUBACK_BYTE,
    #         data={'packet_id': packet_id},
    #         pid=packet_id
    #     )
    def handle_puback(self):
        print(f'Handling PUBACK for: {self.packet}')

        if len(self.packet) != 4:
            raise PacketHandlerError("Invalid PUBACK packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x40:
            raise PacketHandlerError("Invalid PUBACK packet header")

        remaining_length = self.packet[1]
        if remaining_length != 0x02:
            raise PacketHandlerError("Invalid PUBACK remaining length")

        packet_id = (self.packet[2] << 8) | self.packet[3]
        packet_id = int.from_bytes(self.packet[2:], 'big')

        print(f"Received PUBACK for Packet ID: {packet_id}")

        return HandlerResponse(command=0x40, data={'packet_id': packet_id})

    # def handle_suback(self):
    #     # Receive the data (this could be more dynamic based on the packet size)
    #     print(f'Handling suback for: {self.packet}')
    #     success = True

    #     # Check if the packet length is valid and it's a SUBACK packet
    #     if len(self.packet) < 4:
    #         print("Invalid packet length")
    #         success = False
    #         return success

    #     # SUBACK format:
    #     # Byte 1: Fixed header (always 0x90 for SUBACK)
    #     # Byte 2: Remaining length (typically the number of QoS values)
    #     # Byte 3: Packet ID (2 bytes)
    #     # Byte 4+ : Return codes (1 byte for each subscription)

    #     fixed_header = self.packet[0]
    #     remaining_length = self.packet[1]

    #     # Ensure the packet starts with the correct SUBACK header (0x90)
    #     if fixed_header != 0x90:
    #         print("Invalid SUBACK packet")
    #         success = False
    #         return success

    #     # Packet ID is 2 bytes
    #     packet_id = int.from_bytes(self.packet[2:4], byteorder='big')

    #     # Get the QoS levels (starting from byte 4)
    #     qos_levels = self.packet[4:]

    #     print(f"Packet ID: {packet_id}")
    #     print(f"QoS levels: {qos_levels}")

    #     # Validate the QoS return codes (valid values are 0x00, 0x01, and 0x02)
    #     for i, qos in enumerate(qos_levels):
    #         if qos not in [0x00, 0x01, 0x02]:
    #             print(f"Invalid QoS level at index {i}: {qos}")
    #             success = False
    #             break

    #     # Optionally handle additional scenarios if needed
    #     return HandlerResponse(command=packets.SUBACK_BYTE, success=True)

    def handle_suback(self):
        print(f'Handling SUBACK for: {self.packet}')

        if len(self.packet) < 5:
            raise PacketHandlerError("Invalid SUBACK packet length")

        fixed_header = self.packet[0]
        if fixed_header != 0x90:
            raise PacketHandlerError("Invalid SUBACK packet header")

        # Decode Remaining Length using the variable-length method
        remaining_length, consumed_bytes = self._decode_remaining_length(
            self.packet[1:])
        index = 1 + consumed_bytes

        if len(self.packet) < index + remaining_length:
            raise PacketHandlerError("Incomplete SUBACK packet")

        # Packet Identifier (2 bytes)
        packet_id = (self.packet[index] << 8) | self.packet[index + 1]
        packet_id = int.from_bytes(self.packet[index:index + 1], 'big')
        index += 2

        # Return codes (one byte per subscription topic)
        # TODO more readable
        return_codes = list(self.packet[index:index + (remaining_length - 2)])

        print(
            f"Received SUBACK: Packet ID={packet_id}, Return Codes={return_codes}")

        return HandlerResponse(
            command=0x90,
            data={
                'packet_id': packet_id,
                'return_codes': return_codes,
            }
        )

    def handle_pingresp(self):
        print(f'Handling pingresp for {self.packet}')
        print("TODO somehow use this for the client to know when it's connection is dead")
        return HandlerResponse(command=packets.PINGRESP_BYTE)

    def handler_not_implemented(self):
        raise PacketHandlerError('Handler not implemented')

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
                raise PacketHandlerError(
                    "Malformed Remaining Length field: incomplete data")

            encoded_byte = data[index]
            value += (encoded_byte & 0x7F) * multiplier

            if (encoded_byte & 0x80) == 0:  # MSB not set, done reading
                break

            multiplier *= 128
            # equivalent to 128*128*128 (max allowed multiplier)
            if multiplier > 128**3:
                raise PacketHandlerError(
                    "Malformed Remaining Length field: length too long")

            index += 1

        return value, index + 1
