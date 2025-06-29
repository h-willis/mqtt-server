from mqtt_packet import MQTTPacket
import packets
import pytest


def test_command_byte_int_and_bytes():
    pkt1 = MQTTPacket(0x32, b'\x32\x00')
    assert pkt1.command_byte == 0x32

    pkt2 = MQTTPacket(b'\x32', b'\x32\x00')
    assert pkt2.command_byte == 0x32


def test_properties_defaults():
    pkt = MQTTPacket(0x30, b'\x30\x00')
    assert pkt.packet_id is None
    assert pkt.qos == 0
    assert pkt.retain is False
    assert pkt.topic is None
    assert pkt.payload is None


def test_properties_with_data():
    data = {'packet_id': 42, 'qos': 2, 'retain': True,
            'topic': 'foo', 'payload': b'bar'}
    pkt = MQTTPacket(0x30, b'\x30\x00', data)
    assert pkt.packet_id == 42
    assert pkt.qos == 2
    assert pkt.retain is True
    assert pkt.topic == 'foo'
    assert pkt.payload == b'bar'


def test_command_type():
    pkt = MQTTPacket(0x32, b'\x32\x00')
    assert pkt.command_type == 0x30


def test_dup_and_set_dup_bit():
    pkt = MQTTPacket(0x30, b'\x30\x00')
    assert not pkt.dup
    pkt.set_dup_bit()
    assert pkt.dup
    assert (pkt.command_byte & packets.DUP_BIT) != 0


def test_set_dup_bit_idempotent():
    pkt = MQTTPacket(0x38, b'\x38\x00')  # DUP bit already set
    pkt.set_dup_bit()
    assert pkt.dup
    assert pkt.command_byte == 0x38


def test_str_repr():
    data = {'topic': 'foo'}
    pkt = MQTTPacket(0x30, b'\x30\x00', data)
    s = str(pkt)
    assert "MQTTPacket" in s
    assert "command_byte=48" in s
    assert "topic" in s


def test_send_calls_send_func():
    called = {}

    def fake_send(raw):
        called['raw'] = raw

    pkt = MQTTPacket(0x30, b'\x30\x00', send_func=fake_send)
    pkt.send()
    assert called['raw'] == b'\x30\x00'


def test_send_no_send_func():
    pkt = MQTTPacket(0x30, b'\x30\x00')
    # Should not raise
    pkt.send()
