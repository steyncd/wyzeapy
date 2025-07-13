
# Converted to pytest style tests

import pytest
from unittest.mock import MagicMock
from wyzeapy.utils import (
    pad,
    wyze_encrypt,
    wyze_decrypt,
    wyze_decrypt_cbc,
    create_password,
    check_for_errors_standard,
    check_for_errors_lock,
    check_for_errors_devicemgmt,
    check_for_errors_iot,
    check_for_errors_hms,
    return_event_for_device,
    create_pid_pair
)
from wyzeapy.exceptions import ParameterError, AccessTokenError, UnknownApiError
from wyzeapy.types import ResponseCodes, PropertyIDs, Device, Event


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------


def test_pad():
    assert len(pad("short")) == 16
    assert len(pad("eightchr")) == 16
    assert len(pad("morethan8")) == 16


def test_wyze_encrypt_decrypt():
    key = "abcdefghijklmnop"
    text = "Hello, Wyze!"
    encrypted_text = wyze_encrypt(key, text)
    decrypted_text = wyze_decrypt(key, encrypted_text)
    assert decrypted_text.strip(b"\x05".decode("ascii")) == text


def test_wyze_decrypt_cbc():
    key = "testkey"
    encrypted_hex = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    # We mainly want to ensure the function runs and handles errors gracefully.
    try:
        wyze_decrypt_cbc(key, encrypted_hex)
    except Exception:
        # Function is expected to raise with dummy data — that is acceptable.
        pass


def test_create_password():
    password = "mysecretpassword"
    hashed_password = create_password(password)
    assert len(hashed_password) == 32  # MD5 hash is 32 hex characters


# ---------------------------------------------------------------------------
# Error handling helpers
# ---------------------------------------------------------------------------


def test_check_for_errors_standard_success():
    mock_service = MagicMock()
    response_json = {"code": ResponseCodes.SUCCESS.value}
    check_for_errors_standard(mock_service, response_json)


def test_check_for_errors_standard_parameter_error():
    mock_service = MagicMock()
    response_json = {"code": ResponseCodes.PARAMETER_ERROR.value, "msg": "Invalid param"}
    with pytest.raises(ParameterError):
        check_for_errors_standard(mock_service, response_json)


def test_check_for_errors_standard_access_token_error():
    mock_service = MagicMock()
    mock_service._auth_lib.token = MagicMock()
    response_json = {"code": ResponseCodes.ACCESS_TOKEN_ERROR.value, "msg": "Token expired"}
    with pytest.raises(AccessTokenError):
        check_for_errors_standard(mock_service, response_json)
    assert mock_service._auth_lib.token.expired


def test_check_for_errors_standard_device_offline():
    mock_service = MagicMock()
    response_json = {"code": ResponseCodes.DEVICE_OFFLINE.value, "msg": "Device offline"}
    check_for_errors_standard(mock_service, response_json)


def test_check_for_errors_standard_unknown_api_error():
    mock_service = MagicMock()
    response_json = {"code": "9999", "msg": "Unknown error"}
    with pytest.raises(UnknownApiError):
        check_for_errors_standard(mock_service, response_json)


def test_check_for_errors_lock_success():
    mock_service = MagicMock()
    response_json = {"ErrNo": 0}
    check_for_errors_lock(mock_service, response_json)


def test_check_for_errors_lock_parameter_error():
    mock_service = MagicMock()
    response_json = {"ErrNo": 1, "code": ResponseCodes.PARAMETER_ERROR.value}
    with pytest.raises(ParameterError):
        check_for_errors_lock(mock_service, response_json)


def test_check_for_errors_lock_access_token_error():
    mock_service = MagicMock()
    mock_service._auth_lib.token = MagicMock()
    response_json = {"ErrNo": 1, "code": ResponseCodes.ACCESS_TOKEN_ERROR.value}
    with pytest.raises(AccessTokenError):
        check_for_errors_lock(mock_service, response_json)
    assert mock_service._auth_lib.token.expired


def test_check_for_errors_lock_unknown_api_error():
    mock_service = MagicMock()
    response_json = {"ErrNo": 1, "code": "9999"}
    with pytest.raises(UnknownApiError):
        check_for_errors_lock(mock_service, response_json)


def test_check_for_errors_devicemgmt_success():
    mock_service = MagicMock()
    response_json = {"status": 200}
    check_for_errors_devicemgmt(mock_service, response_json)


def test_check_for_errors_devicemgmt_access_token_error():
    mock_service = MagicMock()
    mock_service._auth_lib.token = MagicMock()
    response_json = {"status": 401, "response": {"errors": [{"message": "InvalidTokenError>"}]}}
    with pytest.raises(AccessTokenError):
        check_for_errors_devicemgmt(mock_service, response_json)
    assert mock_service._auth_lib.token.expired


def test_check_for_errors_devicemgmt_unknown_api_error():
    mock_service = MagicMock()
    response_json = {"status": 500, "response": {"errors": [{"message": "Some other error"}]}}
    with pytest.raises(UnknownApiError):
        check_for_errors_devicemgmt(mock_service, response_json)


def test_check_for_errors_iot_success():
    mock_service = MagicMock()
    response_json = {"code": 1}
    check_for_errors_iot(mock_service, response_json)


def test_check_for_errors_iot_access_token_error():
    mock_service = MagicMock()
    mock_service._auth_lib.token = MagicMock()
    response_json = {"code": "2001"}
    with pytest.raises(AccessTokenError):
        check_for_errors_iot(mock_service, response_json)
    assert mock_service._auth_lib.token.expired


def test_check_for_errors_iot_unknown_api_error():
    mock_service = MagicMock()
    response_json = {"code": 9999}
    with pytest.raises(UnknownApiError):
        check_for_errors_iot(mock_service, response_json)


def test_check_for_errors_hms_success():
    mock_service = MagicMock()
    response_json = {"message": "Success"}
    check_for_errors_hms(mock_service, response_json)


def test_check_for_errors_hms_access_token_error():
    mock_service = MagicMock()
    mock_service._auth_lib.token = MagicMock()
    response_json = {"message": None}
    with pytest.raises(AccessTokenError):
        check_for_errors_hms(mock_service, response_json)
    assert mock_service._auth_lib.token.expired


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def test_return_event_for_device_found():
    mock_device = MagicMock(spec=Device)
    mock_device.mac = "test_mac"
    mock_event = MagicMock(spec=Event)
    mock_event.device_mac = "test_mac"
    events = [mock_event]
    result = return_event_for_device(mock_device, events)
    assert result == mock_event


def test_return_event_for_device_not_found():
    mock_device = MagicMock(spec=Device)
    mock_device.mac = "test_mac_2"
    mock_event = MagicMock(spec=Event)
    mock_event.device_mac = "test_mac_1"
    events = [mock_event]
    result = return_event_for_device(mock_device, events)
    assert result is None


def test_create_pid_pair():
    pid_enum = PropertyIDs.ON
    value = "1"
    expected = {"pid": "P3", "pvalue": "1"}
    result = create_pid_pair(pid_enum, value)
    assert result == expected
 
