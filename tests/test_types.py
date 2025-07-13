
from wyzeapy.types import Group, DeviceTypes, Device, Sensor, PropertyIDs, WallSwitchProps, ThermostatProps, ResponseCodes, ResponseCodesLock, File, Event, HMSStatus, DeviceMgmtToggleType, DeviceMgmtToggleProps
import pytest


def test_group_init_and_repr():
    data = {"group_id": "123", "group_name": "MyGroup"}
    group = Group(data)
    assert group.group_id == "123"
    assert group.group_name == "MyGroup"
    assert str(group) == "<Group: 123, MyGroup>"


def test_device_init_and_repr():
    data = {"product_type": "Light", "product_model": "WL1", "mac": "ABC", "nickname": "MyLight", "device_params": {}}
    device = Device(data)
    assert device.available is False
    assert device.product_type == "Light"
    assert device.product_model == "WL1"
    assert device.mac == "ABC"
    assert device.nickname == "MyLight"
    assert device.type == DeviceTypes.LIGHT
    assert str(device) == "<Device: DeviceTypes.LIGHT, ABC>"


def test_device_type_unknown():
    data = {"product_type": "UnknownType", "product_model": "UM1", "mac": "DEF", "nickname": "Unknown", "device_params": {}}
    device = Device(data)
    assert device.type == DeviceTypes.UNKNOWN


def test_sensor_init():
    data = {"product_type": "ContactSensor", "product_model": "CS1", "mac": "GHI", "nickname": "MySensor", "device_params": {"open_close_state": 0}}
    sensor = Sensor(data)
    assert sensor.type == DeviceTypes.CONTACT_SENSOR


def test_sensor_activity_detected_contact_sensor():
    data = {"product_type": "ContactSensor", "device_params": {"open_close_state": 1}}
    sensor = Sensor(data)
    assert sensor.activity_detected == 1


def test_sensor_activity_detected_motion_sensor():
    data = {"product_type": "MotionSensor", "device_params": {"motion_state": 1}}
    sensor = Sensor(data)
    assert sensor.activity_detected == 1


def test_sensor_activity_detected_assertion_error():
    data = {"product_type": "Light", "device_params": {}}
    sensor = Sensor(data)
    with pytest.raises(AssertionError):
        sensor.activity_detected


def test_sensor_is_low_battery():
    data = {"product_type": "ContactSensor", "device_params": {"low_battery": 1}}
    sensor = Sensor(data)
    assert sensor.is_low_battery == 1


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


def test_file_init():
    data = {"type": "image", "url": "http://example.com/image.jpg"}
    file_obj = File(data)
    assert file_obj.type == "Image"

    data = {"type": "video", "url": "http://example.com/video.mp4"}
    file_obj = File(data)
    assert file_obj.type == "Video"


def test_event_init():
    data = {"event_id": "e1", "device_mac": "mac1", "event_category": "1", "event_tag": "tag1"}
    event = Event(data)
    assert event.event_id == "e1"
    assert event.device_mac == "mac1"


def test_hms_status_enum():
    assert HMSStatus.HOME.value == "home"


def test_device_mgmt_toggle_type_init():
    toggle_type = DeviceMgmtToggleType("page", "toggle")
    assert toggle_type.pageId == "page"
    assert toggle_type.toggleId == "toggle"


def test_device_mgmt_toggle_props_enum():
    assert DeviceMgmtToggleProps.NOTIFICATION_TOGGLE.value.pageId == "cam_device_notify"
