import packets
from mqtt_packet import MQTTPacket

"""
Handles creation of mqtt packets to be sent including 
"""


class PacketGenerator:
    def __init__(self, send_func):
        self.pid_generator = self.get_packet_id_bytes()
        self.send_func = send_func

    def _encode_string_with_length(self, s):
        """ Encodes a string with a 2 byte length prefix

        Args:
            s: string to be encoded
        """
        byte_string = str(s).encode('utf-8')
        return len(byte_string).to_bytes(2, 'big') + byte_string

    def _encode_remaining_length(self, length):
        """ Encodes the remaining length (normally the variable header and payload)
        of an MQTT packet. The length is encoded into base 128 with the msb of
        each byte being a continuation bit that there is more data to the length

        Args:
            length: number to be encoded

        Returns:
            byte array of encoded length
        """
        encoded = bytearray()
        while True:
            byte = length % 128
            length //= 128
            # if more data to encode then set the continuation bit
            if length > 0:
                byte |= 0x80
            encoded.append(byte)
            if length == 0:
                break
        return encoded

    def create_connect_packet(self, keep_alive=60, client_id=None):
        # TODO connect flags, username, password, protocol name, lwt
        protocol_name = self._encode_string_with_length('MQTT')
        protocol_level = bytes([0x04])  # MQTT 3.1.1

        # TODO connect flags
        connect_flags = bytes([0])

        # TODO range check
        keep_alive_bytes = keep_alive.to_bytes(2, 'big')

        variable_header = protocol_name + protocol_level + connect_flags + keep_alive_bytes

        # TODO check client_id
        payload = self._encode_string_with_length(client_id)

        command_byte = bytes([packets.CONNECT_BYTE])  # connect packet flag
        remaining_length = self._encode_remaining_length(
            len(variable_header) + len(payload))

        raw_bytes = command_byte + remaining_length + variable_header + payload
        # I dont think we need any of this returned in the data field
        return MQTTPacket(command_byte, raw_bytes, send_func=self.send_func)

    def create_publish_packet(self, topic, payload, qos, retain):
        print(f'Publishing {payload} to {topic} | {qos} | {retain}')
        # TODO improve this
        command_byte = packets.PUBLISH_BYTE

        if qos == 1:
            command_byte |= packets.QOS_1_BITS
        if qos == 2:
            command_byte |= packets.QOS_2_BITS
        if retain:
            command_byte |= packets.RETAIN_BIT
        # if dup:
        #     command_byte |= packets.DUP_BIT

        print(f'Command byte {hex(command_byte)}')

        command_byte = bytes([command_byte])

        variable_header = self._encode_string_with_length(topic)

        pid = None
        if qos > 0:
            # add packet id in correct places
            pid = next(self.pid_generator)
            variable_header += pid

        print(variable_header)

        # NOTE could add config here to allow for numbers encoded as bytes?
        encoded_payload = str(payload).encode('utf-8')
        payload_length = len(encoded_payload)

        remaining_length = self._encode_remaining_length(
            len(variable_header) + payload_length)

        raw_bytes = command_byte + remaining_length + \
            variable_header + encoded_payload

        return MQTTPacket(command_byte, raw_bytes, data={
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'packet_id': int.from_bytes(pid, 'big') if pid else None
        }, send_func=self.send_func)

    def create_puback_packet(self, pid, dup=False):
        command = packets.PUBACK_BYTE
        if dup:
            command |= packets.DUP_BIT
        command_byte = bytes([command])
        remaining_length = bytes([2])
        raw_bytes = command_byte + remaining_length + pid.to_bytes(2, 'big')

        return MQTTPacket(command_byte, raw_bytes, data={'packet_id': pid}, send_func=self.send_func)

    def create_pubrec_packet(self, pid, dup=False):
        command = packets.PUBREC_BYTE
        if dup:
            command |= packets.DUP_BIT
        command_byte = bytes([command])
        remaining_length = bytes([2])
        raw_bytes = command_byte + remaining_length + pid.to_bytes(2, 'big')

        return MQTTPacket(command_byte, raw_bytes, data={'packet_id': pid}, send_func=self.send_func)

    def create_pubrel_packet(self, pid, dup=False):
        command = packets.PUBREL_BYTE
        if dup:
            command |= packets.DUP_BIT
        # lower nibble MUST be 0x02 according to MQTT spec
        command_byte = bytes([command | 0x02])
        remaining_length = bytes([2])
        raw_bytes = command_byte + remaining_length + pid.to_bytes(2, 'big')

        return MQTTPacket(command_byte, raw_bytes, data={'packet_id': pid}, send_func=self.send_func)

    def create_pubcomp_packet(self, pid):
        # no DUP bit for PUBCOMP
        command_byte = bytes([packets.PUBCOMP_BYTE])
        remaining_length = bytes([2])
        raw_bytes = command_byte + remaining_length + pid.to_bytes(2, 'big')

        return MQTTPacket(command_byte, raw_bytes, data={'packet_id': pid}, send_func=self.send_func)

    def create_subscribe_packet(self, topic, qos=0):
        print(f'Subscribing to {topic} at QoS:{qos}')
        # TODO list of topics
        encoded_topic = self._encode_string_with_length(topic)
        encoded_topic += bytes([qos])

        packet_id = next(self.pid_generator)

        remaining_length = self._encode_remaining_length(
            len(packet_id) + len(encoded_topic))

        # lower nibble must be 2 on subscribe command bytes
        command_byte = bytes([packets.SUBSCRIBE_BYTE & 0xf2])

        raw_bytes = command_byte + remaining_length + packet_id + encoded_topic
        return MQTTPacket(command_byte, raw_bytes, data={
            'packet_id': int.from_bytes(packet_id, 'big'),
            'topic': topic,
            'qos': qos
        }, send_func=self.send_func)

    def get_packet_id_bytes(self, start=1):
        # pid cant be 0 so must start at 1
        # TODO should the client have some non vol memory to start the pid at
        # the last used value?
        # TODO loop round at highest pid value - 16 bits?
        while True:
            yield start.to_bytes(2, 'big')
            start += 1
