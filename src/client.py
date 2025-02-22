class Client:
    def __init__(self, conn):
        print('Client created')
        self.running = False
        self.conn = conn

    def validate_connection(self) -> bool:
        data = self.conn.recv(1024)

        print(f'Client data: {data}')

        if data[0] != 0x10:
            print(f'Invalid connection byte {data[0]}')
            return False

        remaining_length = data[1]
        print(f'Header length: {remaining_length}')

        header = data[2:2 + remaining_length]
        username, password, lwt, clean_session, keep_alive = self.extract_header(
            header)

        print(
            f"Username: {username}, Password: {password}, LWT: {lwt}, Clean Session: {clean_session}, Keep Alive: {keep_alive}")

        self.acknowledge_connection()

        return True

    def extract_header(self, header):
        index = 0

        # Extract Protocol Name Length
        proto_len = int.from_bytes(header[index:index + 2], 'big')
        index += 2

        # Extract Protocol Name
        proto_name = header[index:index + proto_len].decode()
        index += proto_len

        # Extract Protocol Level
        proto_level = header[index]
        index += 1

        # Extract Connect Flags
        flags = header[index]
        index += 1

        clean_session = (flags & 0x02) != 0
        LWT_flag = (flags & 0x04) != 0
        username_flag = (flags & 0x80) != 0
        password_flag = (flags & 0x40) != 0

        # Extract Keep Alive
        keep_alive = int.from_bytes(header[index:index + 2], 'big')
        index += 2

        username = password = None

        if username_flag:
            user_len = int.from_bytes(header[index:index + 2], 'big')
            index += 2
            username = header[index:index + user_len].decode()
            index += user_len

        if password_flag:
            pass_len = int.from_bytes(header[index:index + 2], 'big')
            index += 2
            password = header[index:index + pass_len].decode()
            index += pass_len

        return username, password, LWT_flag, clean_session, keep_alive

    def acknowledge_connection(self):
        data = bytearray([0x20, 0x02, 0x01, 0])
        self.conn.send(data)

    def run(self):
        # threaded loop to look for incoming messages and handle keep alive etc.
        self.running = True
        while self.running:
            recv = self.conn.recv(1024)
            print(recv)
