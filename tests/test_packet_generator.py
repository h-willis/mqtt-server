import pytest
import packets
from mqtt_packet import MQTTPacket
from packet_generator import PacketGenerator


class DummyPacket(MQTTPacket):
    def __init__(self, command_byte, raw_bytes, data, send_func):
        self.command_byte = command_byte
        self.raw_bytes = raw_bytes
        self.data = data
        self.send_func = send_func


@pytest.fixture
def packet_gen(monkeypatch):
    # Patch MQTTPacket to avoid side effects
    monkeypatch.setattr('mqtt_packet.MQTTPacket', DummyPacket)
    return PacketGenerator(send_func=lambda x: x)


def test_encode_string_with_length(packet_gen):
    result = packet_gen._encode_string_with_length("abc")
    assert result == b'\x00\x03abc'


def test_encode_remaining_length(packet_gen):
    assert packet_gen._encode_remaining_length(127) == b'\x7f'
    assert packet_gen._encode_remaining_length(128) == b'\x80\x01'


def test_create_connect_packet(packet_gen):
    pkt = packet_gen.create_connect_packet(
        client_id="test", username="u", password="p")
    assert pkt.data['client_id'] == "test"
    assert pkt.data['username'] == "u"
    assert pkt.data['password'] == "p"
    assert pkt.raw_bytes[0] == packets.CONNECT_BYTE


def test_create_publish_packet(packet_gen):
    pkt = packet_gen.create_publish_packet(
        "topic", "payload", qos=1, retain=True)
    assert pkt.data['topic'] == "topic"
    assert pkt.data['payload'] == "payload"
    assert pkt.data['qos'] == 1
    assert pkt.data['retain'] is True
    assert pkt.raw_bytes[0] & 0xF0 == packets.PUBLISH_BYTE


def test_create_puback_packet(packet_gen):
    pkt = packet_gen.create_puback_packet(42)
    assert pkt.data['packet_id'] == 42
    assert pkt.raw_bytes[0] == packets.PUBACK_BYTE


def test_create_pubrec_packet(packet_gen):
    pkt = packet_gen.create_pubrec_packet(42)
    assert pkt.data['packet_id'] == 42
    assert pkt.raw_bytes[0] == packets.PUBREC_BYTE


def test_create_pubrel_packet(packet_gen):
    pkt = packet_gen.create_pubrel_packet(42)
    assert pkt.data['packet_id'] == 42
    assert pkt.raw_bytes[0] & 0xF0 == packets.PUBREL_BYTE & 0xF0


def test_create_pubcomp_packet(packet_gen):
    pkt = packet_gen.create_pubcomp_packet(42)
    assert pkt.data['packet_id'] == 42
    assert pkt.raw_bytes[0] == packets.PUBCOMP_BYTE


def test_create_subscribe_packet(packet_gen):
    pkt = packet_gen.create_subscribe_packet("topic", qos=1)
    assert pkt.data['topic'] == "topic"
    assert pkt.data['qos'] == 1
    assert pkt.raw_bytes[0] & 0xF0 == packets.SUBSCRIBE_BYTE & 0xF0


def test_get_packet_id_bytes(packet_gen):
    gen = packet_gen.get_packet_id_bytes(start=1)
    assert next(gen) == b'\x00\x01'
    for _ in range(65534):
        next(gen)
    assert next(gen) == b'\x00\x01'  # wraps around after 65536
