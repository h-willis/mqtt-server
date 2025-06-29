import pytest
from unittest.mock import MagicMock, patch

from mqtt_client import MQTTClient


@pytest.fixture
def mock_connection():
    with patch('mqtt_client.MQTTClientConnection') as MockConn:
        yield MockConn


def test_connect_calls_connection_connect(mock_connection):
    client = MQTTClient('localhost', 1883)
    client.connection.connect = MagicMock()
    client.connect(timeout=5)
    client.connection.connect.assert_called_once_with(5)


def test_publish_calls_connection_publish(mock_connection):
    client = MQTTClient('localhost', 1883)
    client.connection.publish = MagicMock()
    client.publish('topic', 'payload', qos=1, retain=True)
    client.connection.publish.assert_called_once_with(
        'topic', 'payload', 1, True)


def test_subscribe_calls_connection_subscribe(mock_connection):
    client = MQTTClient('localhost', 1883)
    client.connection.subscribe = MagicMock()
    client.subscribe('topic', qos=2)
    client.connection.subscribe.assert_called_once_with('topic', 2)


def test_set_will_calls_connection_set_will(mock_connection):
    client = MQTTClient('localhost', 1883)
    client.connection.set_will = MagicMock()
    client.set_will('topic', 'payload', qos=1, retain=True)
    client.connection.set_will.assert_called_once_with(
        'topic', 'payload', 1, True)


def test_set_on_connect_callback_sets_callback(mock_connection):
    client = MQTTClient('localhost', 1883)
    cb = MagicMock()
    client.set_on_connect_callback(cb)
    assert client.connection.on_connect == cb


def test_set_on_disconnect_callback_sets_callback(mock_connection):
    client = MQTTClient('localhost', 1883)
    cb = MagicMock()
    client.set_on_disconnect_callback(cb)
    assert client.connection.on_disconnect == cb


def test_set_on_message_callback_sets_callback(mock_connection):
    client = MQTTClient('localhost', 1883)
    cb = MagicMock()
    client.set_on_message_callback(cb)
    assert client.connection.on_message == cb


def test_connected_property(mock_connection):
    client = MQTTClient('localhost', 1883)
    client.connection.connected = True
    assert client.connected is True
