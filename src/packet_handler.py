# handlers for each of the expected MQTT packets:
import packets

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


class MQTTMessage:
    def __init__(self):
        self.packet_id = None


COMMAND_BYTES = {
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


class HandlerResponse:
    def __init__(self, command, success=True, reason=None, response=None, data={}):
        self.command = command
        self.success = success
        # reason for failures for logging
        self.reason = reason
        # for qos > 1
        self.response = response
        # topics and payloads?
        # TODO see if there's a better way of returning this
        self.data = data

    def __str__(self):
        return f'{hex(self.command)} | {self.success} | {self.reason} | {self.response}'


class PacketHandler:
    def __init__(self, packet):
        self.packet = packet
        self.handlers = {
            packets.CONNECT_BYTE: self.handler_not_implemented,     # "CONNECT"
            packets.CONNACK_BYTE: self.handle_connack,              # "CONNACK"
            packets.PUBLISH_BYTE: self.handle_publish,              # "PUBLISH"
            packets.PUBACK_BYTE: self.handler_not_implemented,      # "PUBACK"
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

    def handle_packet(self):
        # just look at top 4 bytes
        if not self.packet:
            return HandlerResponse(False, 'No Packet')

        command = self.packet[0] & 0xf0

        if command not in COMMAND_BYTES:
            # basically if it's 0
            # TODO probably return some sort of packet_response class
            return HandlerResponse(False, 'Invalid command byte')

        print(f'{COMMAND_BYTES[command]} packet recieved')

        return self.handlers[command]()

    def handle_connack(self):
        # Receive the data (this could be more dynamic based on the packet size)
        print(f'Handling connack for: {self.packet}')
        success = True

        # Check if the packet length is valid and it's a CONNACK packet
        if len(self.packet) < 4:
            print("Invalid packet length")
            success = False
            return success

        # CONNACK format:
        # Byte 1: Fixed header (always 0x20 for CONNACK)
        # Byte 2: Remaining length (typically 2 for CONNACK)
        # Byte 3: Return code flags
        # Byte 4: Return code (0x00 = Connection Accepted, etc.)

        fixed_header = self.packet[0]
        remaining_length = self.packet[1]

        # Ensure the packet starts with the correct CONNACK header (0x20)
        if fixed_header != 0x20:
            print("Invalid CONNACK packet")
            success = False
            return success

        # Get the response flags and return code
        response_flags = self.packet[2]
        return_code = self.packet[3]

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

        return HandlerResponse(command=0x20, success=success)

    def handle_publish(self):
        print(f'Handling publish for: {self.packet}')

        # MQTT Fixed header: byte 1 = control byte, byte 2+ = remaining length
        fixed_header = self.packet[0]
        remaining_length = self.packet[1]

        # Start of variable header: Topic name (2-byte length + UTF-8 string)
        topic_length = int.from_bytes(self.packet[2:4], byteorder='big')
        topic_start = 4
        topic_end = topic_start + topic_length
        topic = self.packet[topic_start:topic_end].decode('utf-8')

        # Payload starts immediately after topic (and maybe packet identifier if QoS > 0)
        payload_start = topic_end
        payload = self.packet[payload_start:].decode('utf-8')

        print(f'Topic: {topic}, Payload: {payload}')

        # Optionally store or forward this message, depending on your broker logic

        return HandlerResponse(packets.PUBLISH_BYTE, data={'topic': topic, 'payload': payload})

    def handle_suback(self):
        # Receive the data (this could be more dynamic based on the packet size)
        print(f'Handling suback for: {self.packet}')
        success = True

        # Check if the packet length is valid and it's a SUBACK packet
        if len(self.packet) < 4:
            print("Invalid packet length")
            success = False
            return success

        # SUBACK format:
        # Byte 1: Fixed header (always 0x90 for SUBACK)
        # Byte 2: Remaining length (typically the number of QoS values)
        # Byte 3: Packet ID (2 bytes)
        # Byte 4+ : Return codes (1 byte for each subscription)

        fixed_header = self.packet[0]
        remaining_length = self.packet[1]

        # Ensure the packet starts with the correct SUBACK header (0x90)
        if fixed_header != 0x90:
            print("Invalid SUBACK packet")
            success = False
            return success

        # Packet ID is 2 bytes
        packet_id = int.from_bytes(self.packet[2:4], byteorder='big')

        # Get the QoS levels (starting from byte 4)
        qos_levels = self.packet[4:]

        print(f"Packet ID: {packet_id}")
        print(f"QoS levels: {qos_levels}")

        # Validate the QoS return codes (valid values are 0x00, 0x01, and 0x02)
        for i, qos in enumerate(qos_levels):
            if qos not in [0x00, 0x01, 0x02]:
                print(f"Invalid QoS level at index {i}: {qos}")
                success = False
                break

        # Optionally handle additional scenarios if needed
        return HandlerResponse(command=packets.SUBACK_BYTE, success=True)

    def handle_pingresp(self):
        print(f'Handling pingresp for {self.packet}')
        print("TODO somehow use this for the client to know when it's connection is dead")
        return HandlerResponse(command=packets.PINGRESP_BYTE)

    def handler_not_implemented(self):
        print(f'HANDLER NOT IMPLEMENTED')
        return HandlerResponse(0x00, success=False, reason='Not implemented')
