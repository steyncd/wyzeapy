import time
from unittest.mock import patch

import pytest

from wyzeapy.payload_factory import (
    ford_create_payload,
    olive_create_get_payload,
    olive_create_post_payload,
    olive_create_hms_payload,
    olive_create_user_info_payload,
    olive_create_hms_get_payload,
    olive_create_hms_patch_payload,
    devicemgmt_create_capabilities_payload,
    devicemgmt_get_iot_props_list,
)
from wyzeapy.crypto import olive_create_signature


# ---------------------------------------------------------------------------
# ford_create_payload
# ---------------------------------------------------------------------------


@patch("wyzeapy.payload_factory.ford_create_signature", return_value="mock_signature")
@patch("time.time", return_value=1234567890.123)
def test_ford_create_payload(mock_time, mock_sig):
    access_token = "atk"
    payload = {"p": "v"}
    url_path = "/test/path"
    method = "POST"

    res = ford_create_payload(access_token, payload, url_path, method)

    assert res["access_token"] == access_token
    assert res["key"] == "275965684684dbdaf29a0ed9"
    assert res["timestamp"] == "1234567890123"
    assert res["sign"] == "mock_signature"
    mock_sig.assert_called_once_with(url_path, method, res)


# ---------------------------------------------------------------------------
# Olive helpers – nonce frozen at 1234567890123
# ---------------------------------------------------------------------------


@patch("time.time", return_value=1234567890.123)
def test_olive_create_get_payload(mock_time):
    res = olive_create_get_payload("mac", "k1,k2")
    assert res == {"keys": "k1,k2", "did": "mac", "nonce": 1234567890123}


@patch("time.time", return_value=1234567890.123)
def test_olive_create_post_payload(mock_time):
    res = olive_create_post_payload("mac", "model", "prop", "val")
    assert res == {
        "did": "mac",
        "model": "model",
        "props": {"prop": "val"},
        "is_sub_device": 0,
        "nonce": "1234567890123",
    }


@patch("time.time", return_value=1234567890.123)
def test_olive_create_hms_payload(mock_time):
    assert olive_create_hms_payload() == {"group_id": "hms", "nonce": "1234567890123"}


@patch("time.time", return_value=1234567890.123)
def test_olive_create_user_info_payload(mock_time):
    assert olive_create_user_info_payload() == {"nonce": "1234567890123"}


@patch("time.time", return_value=1234567890.123)
def test_olive_create_hms_get_payload(mock_time):
    res = olive_create_hms_get_payload("hms")
    assert res == {"hms_id": "hms", "nonce": "1234567890123"}


def test_olive_create_hms_patch_payload():
    assert olive_create_hms_patch_payload("hms") == {"hms_id": "hms"}


# ---------------------------------------------------------------------------
# DeviceMgmt helpers
# ---------------------------------------------------------------------------


def test_devicemgmt_create_capabilities_payload_variants():
    # floodlight / spotlight
    fl = devicemgmt_create_capabilities_payload("floodlight", "on")
    assert fl["name"] == "floodlight" and fl["properties"][0]["prop"] == "on"

    sp = devicemgmt_create_capabilities_payload("spotlight", "on")
    assert sp["name"] == "spotlight" and sp["properties"][0]["prop"] == "on"

    pw = devicemgmt_create_capabilities_payload("power", "val")
    assert pw["name"] == "iot-device" and pw["functions"][0]["name"] == "val"

    sr = devicemgmt_create_capabilities_payload("siren", "val")
    assert sr["name"] == "siren" and sr["functions"][0]["name"] == "val"

    with pytest.raises(NotImplementedError):
        devicemgmt_create_capabilities_payload("unsupported_type", "x")


def test_devicemgmt_get_iot_props_list_variants():
    for model in ("LD_CFP", "AN_RSCW", "GW_GC1"):
        lst = devicemgmt_get_iot_props_list(model)
        assert isinstance(lst, list) and lst and lst[0]["name"] == "camera"

    with pytest.raises(NotImplementedError):
        devicemgmt_get_iot_props_list("unsupported_model")


# ---------------------------------------------------------------------------
# olive_create_signature basic length
# ---------------------------------------------------------------------------


def test_olive_create_signature_with_string():
    sig = olive_create_signature("payload", "token")
    assert isinstance(sig, str) and len(sig) == 32  # MD5 hex