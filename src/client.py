class Client:
    def __init__(self, conn, on_new_subscription):
        print('Client created')
        self.running = False
        self.conn = conn
        self.on_new_subscription = on_new_subscription

    def validate_connection(self) -> bool:
        data = self.conn.recv(1024)

        if not data or data[0] != 0x10:
            return False

        remaining_length = data[1]
        print(f'Header length: {remaining_length}')

        if len(data) < 2 + remaining_length:
            return False  # Incomplete packet

        header = data[2:2 + remaining_length]
        username, password, LWT, clean_session, keep_alive, payload_start = self.extract_header(
            header)

        payload = header[payload_start:]
        client_id, will_topic, will_message = self.extract_payload(payload)

        print(
            f"Username: {username}, Password: {password}, LWT: {LWT}, Clean Session: {clean_session}, Keep Alive: {keep_alive}")
        print(
            f"Client ID: {client_id}, Will Topic: {will_topic}, Will Message: {will_message}")

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

        return username, password, LWT_flag, clean_session, keep_alive, index

    def extract_payload(self, payload):
        index = 0

        # Extract Client ID Length
        client_id_len = int.from_bytes(payload[index:index + 2], 'big')
        index += 2

        # Extract Client ID
        client_id = payload[index:index + client_id_len].decode()
        index += client_id_len

        will_topic = will_message = None

        if len(payload) > index:
            # Extract Will Topic Length
            will_topic_len = int.from_bytes(payload[index:index + 2], 'big')
            index += 2
            will_topic = payload[index:index + will_topic_len].decode()
            index += will_topic_len

        if len(payload) > index:
            # Extract Will Message Length
            will_message_len = int.from_bytes(payload[index:index + 2], 'big')
            index += 2
            will_message = payload[index:index + will_message_len].decode()
            index += will_message_len

        return client_id, will_topic, will_message

    def acknowledge_connection(self):
        data = bytearray([0x20, 0x02, 0x01, 0])
        self.conn.send(data)

    def extract_subscription_message(self, payload):
        # Bits 3,2,1 and 0 of the fixed header of the SUBSCRIBE Control Packet are reserved and MUST be set to 0,0,1 and 0 respectively. The Server MUST treat any other value as malformed and close the Network Connection [MQTT-3.8.1-1].
        print(f'SUB message received {payload}')
        index = 0

        command_byte = payload[index]
        index += 1

        # Extract Packet Identifier
        remaining_length = payload[index]
        print(f'remaining length {remaining_length}')
        index += 1

        packet_id = int.from_bytes(payload[index:index + 2], 'big')
        index += 2
        print(f'packet id {packet_id}')

        topics = []

        while index < len(payload):
            # Extract Topic Length
            topic_len = int.from_bytes(payload[index:index + 2], 'big')
            print(topic_len, index)
            index += 2

            # Extract Topic Name
            topic_name = payload[index:index + topic_len].decode()
            index += topic_len
            print(f'topic: {topic_name}')

            # Extract QoS Level
            qos_level = payload[index]
            index += 1

            topics.append((topic_name, qos_level))

        print(topics)

        return packet_id, topics

    def run(self):
        # threaded loop to look for incoming messages and handle keep alive etc.
        self.running = True
        while self.running:
            recv = self.conn.recv(1024)
            print(recv)

            for idx, val in enumerate(recv):
                if val == 0x82:
                    self.extract_subscription_message(
                        # TODO this slicing is unpleasant
                        recv[idx:idx + recv[idx + 1] + 2])
