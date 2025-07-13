
import pytest

from wyzeapy.types import (
    Group,
    DeviceTypes,
    Device,
    Sensor,
    PropertyIDs,
    WallSwitchProps,
    ThermostatProps,
    ResponseCodes,
    ResponseCodesLock,
    File,
    Event,
    HMSStatus,
    DeviceMgmtToggleType,
    DeviceMgmtToggleProps,
)

# ---------------------------------------------------------------------------
# Group & Device helpers
# ---------------------------------------------------------------------------


def test_group_init_and_repr():
    data = {"group_id": "123", "group_name": "MyGroup"}
    group = Group(data)
    assert group.group_id == "123"
    assert group.group_name == "MyGroup"
    assert str(group) == "<Group: 123, MyGroup>"


def test_device_init_and_repr():
    data = {
        "product_type": "Light",
        "product_model": "WL1",
        "mac": "ABC",
        "nickname": "MyLight",
        "device_params": {},
    }
    dev = Device(data)
    assert not dev.available
    assert dev.product_type == "Light"
    assert dev.product_model == "WL1"
    assert dev.mac == "ABC"
    assert dev.nickname == "MyLight"
    assert dev.type == DeviceTypes.LIGHT
    assert str(dev) == "<Device: DeviceTypes.LIGHT, ABC>"


def test_device_type_unknown():
    data = {
        "product_type": "UnknownType",
        "product_model": "UM1",
        "mac": "DEF",
        "nickname": "Unknown",
        "device_params": {},
    }
    dev = Device(data)
    assert dev.type == DeviceTypes.UNKNOWN


# ---------------------------------------------------------------------------
# Sensor helpers
# ---------------------------------------------------------------------------


def test_sensor_init():
    data = {
        "product_type": "ContactSensor",
        "product_model": "CS1",
        "mac": "GHI",
        "nickname": "MySensor",
        "device_params": {"open_close_state": 0},
    }
    sensor = Sensor(data)
    assert sensor.type == DeviceTypes.CONTACT_SENSOR


def test_sensor_activity_detected_contact():
    sensor = Sensor({"product_type": "ContactSensor", "device_params": {"open_close_state": 1}})
    assert sensor.activity_detected == 1


def test_sensor_activity_detected_motion():
    sensor = Sensor({"product_type": "MotionSensor", "device_params": {"motion_state": 1}})
    assert sensor.activity_detected == 1


def test_sensor_activity_detected_assert_error():
    sensor = Sensor({"product_type": "Light", "device_params": {}})
    with pytest.raises(AssertionError):
        _ = sensor.activity_detected


def test_sensor_is_low_battery():
    sensor = Sensor({"product_type": "ContactSensor", "device_params": {"is_low_battery": 1}})
    assert sensor.is_low_battery == 1


# ---------------------------------------------------------------------------
# Enum sanity checks
# ---------------------------------------------------------------------------


def test_property_ids_enum():
    assert PropertyIDs.ON.value == "P3"
    assert PropertyIDs.BRIGHTNESS.value == "P1501"


def test_wall_switch_props_enum():
    assert WallSwitchProps.IOT_STATE.value == "iot_state"


def test_thermostat_props_enum():
    assert ThermostatProps.TEMPERATURE.value == "temperature"


def test_response_codes_enum():
    assert ResponseCodes.SUCCESS.value == "1"


def test_response_codes_lock_enum():
    assert ResponseCodesLock.SUCCESS.value == 0


# ---------------------------------------------------------------------------
# File / Event helpers
# ---------------------------------------------------------------------------


def test_file_type_mapping():
    data = {
        "file_id": "f1",
        "type": 1,
        "url": "http://example.com/img.jpg",
        "status": 0,
        "en_algorithm": 0,
        "en_password": "",
        "is_ai": 0,
        "ai_tag_list": [],
        "ai_url": "",
        "file_params": {},
    }
    f = File(data)
    assert f.type == "Image"

    data["type"] = 2
    f = File(data)
    assert f.type == "Video"


def test_event_init():
    data = {
        "event_id": "e1",
        "device_mac": "mac1",
        "device_model": "model1",
        "event_category": 1,
        "event_value": "val1",
        "event_ts": 123,
        "event_ack_result": 0,
        "is_feedback_correct": 0,
        "is_feedback_face": 0,
        "is_feedback_person": 0,
        "file_list": [],
        "event_params": {},
        "recognized_instance_list": [],
        "tag_list": [],
        "read_state": 0,
    }
    evt = Event(data)
    assert evt.event_id == "e1"
    assert evt.device_mac == "mac1"


# ---------------------------------------------------------------------------
# HMS / DeviceMgmt enums
# ---------------------------------------------------------------------------


def test_hms_status_enum():
    assert HMSStatus.HOME.value == "home"


def test_device_mgmt_toggle_type_init():
    t = DeviceMgmtToggleType("page", "toggle")
    assert t.pageId == "page"
    assert t.toggleId == "toggle"


def test_device_mgmt_toggle_props_enum():
    assert DeviceMgmtToggleProps.NOTIFICATION_TOGGLE.value.pageId == "cam_device_notify"
