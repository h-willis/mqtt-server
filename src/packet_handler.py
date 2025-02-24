# handlers for each of the expected MQTT packets:

'''
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
'''

# does this send responses or return a response to send?
# could be if it returns something from a handle_packet then it needs to be sent
# might get difficult for handshakey stuff for qos 1 and 2 messages
# might need a Message class to track unacked messages or stuff like that

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


class PacketResponse:
    def __init__(self):
        self.success = False


class PacketHandler:
    def __init__(self, packet):
        self.packet = packet

    def handle_packet(self):
        # just look at top 4 bytes
        command = self.packet[0] & 0xf0
        if command not in COMMAND_BYTES:
            # basically if it's 0
            # TODO probably return some sort of packet_response class
            return False

        print(f'{COMMAND_BYTES[command]} packet recieved')
        response = PacketResponse()
        response.success = True
        return response
