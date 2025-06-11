

class MQTTPacket:
    # this is either created from the packet generator or from a received packet
    def __init__(self, command_byte, raw_bytes, send_func, data=None):
        self.command_byte = command_byte
        self.raw_bytes = raw_bytes
        self.data = data if data is not None else {}
        self.send_func = send_func

    def send(self):
        """ Sends the packet using the provided send function """
        print('Sending', end=' ')
        print('\\x'.join(f"{byte:02x}" for byte in self.raw_bytes))
        self.send_func(self.raw_bytes)
