import packets

"""
Handles creation of mqtt packets to be sent including encoding length
"""


class Packet:
    def __init__(self, command, raw_bytes, pid=None):
        self.command = command
        self.raw_bytes = raw_bytes
        self.pid = pid

    def __str__(self):
        return f'{self.command} | {self.pid}'


class PacketGenerator:
    def __init__(self):
        self.pid_generator = self.get_packet_id_bytes()

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
        # TODO connect flags, username, password, protocol name
        protocol_name = self._encode_string_with_length('MQTT')
        protocol_level = bytes([0x04])  # MQTT 3.1.1

        # TODO connect flags
        connect_flags = bytes([0])

        # TODO range check
        keep_alive_bytes = keep_alive.to_bytes(2, 'big')

        variable_header = protocol_name + protocol_level + connect_flags + keep_alive_bytes

        # TODO check client_id
        payload = self._encode_string_with_length(client_id)

        packet_type_flag = bytes([packets.CONNECT_BYTE])  # connect packet flag
        remaining_length = self._encode_remaining_length(
            len(variable_header) + len(payload))

        return packet_type_flag + remaining_length + variable_header + payload

    def create_publish_packet(self, topic, payload, qos, retain):
        print(f'Publishing {payload} to {topic} | {qos} | {retain}')
        # TODO flags (DUP)
        # TODO improve this
        command_byte = packets.PUBLISH_BYTE

        if qos == 1:
            command_byte |= packets.QOS_1_BITS
        if qos == 2:
            command_byte |= packets.QOS_2_BITS
        if retain:
            command_byte |= packets.RETAIN_BIT

        print(f'Command byte {hex(command_byte)}')

        # TODO is this the best way to do this?
        packet_type_flag = bytes([command_byte])

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

        raw_bytes = packet_type_flag + remaining_length + \
            variable_header + encoded_payload
        return Packet(command_byte, raw_bytes, int.from_bytes(pid, 'big'))

    def create_puback_packet(self, pid):
        command_byte = bytes([packets.PUBACK_BYTE])
        remaining_length = bytes([2])
        raw_bytes = command_byte + remaining_length + pid.to_bytes(2, 'big')

        return Packet(command_byte, raw_bytes, pid)

    def create_subscribe_packet(self, topic, qos=0):
        print(f'Subscribing to {topic} at QoS:{qos}')
        # TODO list of topics
        encoded_topic = self._encode_string_with_length(topic)
        encoded_topic += bytes([qos])

        packet_id = next(self.pid_generator)

        remaining_length = self._encode_remaining_length(
            len(packet_id) + len(encoded_topic))

        # lower nibble must be 2 on subscribe command bytes
        packet_type_flag = bytes([packets.SUBSCRIBE_BYTE & 0xf2])

        return packet_type_flag + remaining_length + packet_id + encoded_topic

    def get_packet_id_bytes(self, start=1):
        # pid cant be 0 so must start at 1
        # TODO should the client have some non vol memory to start the pid at
        # the last used value?
        # TODO loop round at highest pid value - 16 bits?
        while True:
            yield start.to_bytes(2, 'big')
            start += 1
