

class MQTTPacket:
    # this is either created from the packet generator or from a received packet
    # topic and payload are encoded as utf-8 strings
    def __init__(self, command_byte, raw_bytes, data=None):
        self.command_byte = command_byte
        self.raw_bytes = raw_bytes
        self.data = data if data is not None else {}
        self.send_func = lambda x: None

    @property
    def command_type(self):
        """ Returns the command type of the packet """
        return self.command_byte & 0xf0

    # TODO double check the default return types for these
    @property
    def packet_id(self):
        return self.data.get('packet_id', None)

    @property
    def qos(self):
        return self.data.get('qos', 0)

    @property
    def retain(self):
        return self.data.get('retain', False)

    @property
    def topic(self):
        return self.data.get('topic', None)

    @property
    def payload(self):
        return self.data.get('payload', None)

    def send(self):
        """ Sends the packet using the provided send function """
        print('Sending', end=' ')
        print('\\x'.join(f"{byte:02x}" for byte in self.raw_bytes))
        self.send_func(self.raw_bytes)
