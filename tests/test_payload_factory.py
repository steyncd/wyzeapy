import time
import pytest
from unittest.mock import patch, MagicMock
from wyzeapy.payload_factory import (
    ford_create_payload,
    olive_create_get_payload,
    olive_create_post_payload,
    olive_create_hms_payload,
    olive_create_user_info_payload,
    olive_create_hms_get_payload,
    olive_create_hms_patch_payload,
    devicemgmt_create_capabilities_payload,
    devicemgmt_get_iot_props_list
)
from wyzeapy.crypto import olive_create_signature


@patch('wyzeapy.payload_factory.ford_create_signature')
@patch('time.time', return_value=1234567890.123)
def test_ford_create_payload(mock_time, mock_create_signature):
    mock_create_signature.return_value = "mock_signature"
    access_token = "test_access_token"
    payload = {"param1": "value1"}
    url_path = "/test/path"
    request_method = "POST"

    result = ford_create_payload(access_token, payload, url_path, request_method)

    assert result["access_token"] == access_token
    assert result["key"] == "275965684684dbdaf29a0ed9" # FORD_APP_KEY from const.py
    assert result["timestamp"] == "1234567890123"
    assert result["sign"] == "mock_signature"
    mock_create_signature.assert_called_once_with(url_path, request_method, result)


@patch('time.time', return_value=1234567890.123)
def test_olive_create_get_payload(mock_time):
    device_mac = "test_mac"
    keys = "key1,key2"

    result = olive_create_get_payload(device_mac, keys)

    assert result["keys"] == keys
    assert result["did"] == device_mac
    assert result["nonce"] == 1234567890123


@patch('time.time', return_value=1234567890.123)
def test_olive_create_post_payload(mock_time):
    device_mac = "test_mac"
    device_model = "test_model"
    prop_key = "test_prop"
    value = "test_value"

    result = olive_create_post_payload(device_mac, device_model, prop_key, value)

    assert result["did"] == device_mac
    assert result["model"] == device_model
    assert result["props"] == {prop_key: value}
    assert result["is_sub_device"] == 0
    assert result["nonce"] == "1234567890123"


@patch('time.time', return_value=1234567890.123)
def test_olive_create_hms_payload(mock_time):
    result = olive_create_hms_payload()

    assert result["group_id"] == "hms"
    assert result["nonce"] == "1234567890123"


@patch('time.time', return_value=1234567890.123)
def test_olive_create_user_info_payload(mock_time):
    result = olive_create_user_info_payload()

    assert result["nonce"] == "1234567890123"


@patch('time.time', return_value=1234567890.123)
def test_olive_create_hms_get_payload(mock_time):
    hms_id = "test_hms_id"

    result = olive_create_hms_get_payload(hms_id)

    assert result["hms_id"] == hms_id
    assert result["nonce"] == "1234567890123"


def test_olive_create_hms_patch_payload():
    hms_id = "test_hms_id"
    hms_status = "test_status"

    result = olive_create_hms_patch_payload(hms_id, hms_status)

    assert result["hms_id"] == hms_id
    assert result["hms_status"] == hms_status


def test_devicemgmt_create_capabilities_payload_floodlight():
    result = devicemgmt_create_capabilities_payload("floodlight", "on", "1")

    assert result["name"] == "floodlight"
    assert result["properties"][0]["prop"] == "on"


def test_devicemgmt_create_capabilities_payload_spotlight():
    result = devicemgmt_create_capabilities_payload("spotlight", "on", "1")

    assert result["name"] == "spotlight"
    assert result["properties"][0]["prop"] == "on"


def test_devicemgmt_create_capabilities_payload_power():
    result = devicemgmt_create_capabilities_payload("power", "test_value", "1")

    assert result["name"] == "iot-device"
    assert result["functions"][0]["name"] == "test_value"


def test_devicemgmt_create_capabilities_payload_siren():
    result = devicemgmt_create_capabilities_payload("siren", "test_value", "1")

    assert result["name"] == "siren"
    assert result["functions"][0]["name"] == "test_value"


def test_devicemgmt_create_capabilities_payload_not_implemented():
    with pytest.raises(NotImplementedError):
        devicemgmt_create_capabilities_payload("unknown", "test_value", "1")


def test_devicemgmt_get_iot_props_list_LD_CFP():
    result = devicemgmt_get_iot_props_list("LD_CFP")

    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "camera"


def test_devicemgmt_get_iot_props_list_AN_RSCW():
    result = devicemgmt_get_iot_props_list("AN_RSCW")

    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "camera"


def test_devicemgmt_get_iot_props_list_GW_GC1():
    result = devicemgmt_get_iot_props_list("GW_GC1")

    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "camera"


def test_devicemgmt_get_iot_props_list_not_implemented():
    with pytest.raises(NotImplementedError):
        devicemgmt_get_iot_props_list("UNKNOWN")


def test_olive_create_signature_with_string_payload():
    payload = "test_payload"
    signature = olive_create_signature(payload)

    assert isinstance(signature, str)
    assert len(signature) == 32 # MD5 hash is 32 hex characters