import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.sensor_service import SensorService, Sensor
from wyzeapy.types import DeviceTypes, PropertyIDs
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
def sensor_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = SensorService(auth_lib=mock_auth_lib)
    service._get_device_info = AsyncMock()
    service.get_updated_params = AsyncMock()
    service.get_object_list = AsyncMock()
    service._subscribers = []  # reset
    return service


def _motion_sensor():
    return Sensor(
        {
            "device_type": DeviceTypes.MOTION_SENSOR.value,
            "product_model": "PIR3U",
            "mac": "MOTION123",
            "nickname": "Test Motion Sensor",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


def _contact_sensor():
    return Sensor(
        {
            "device_type": DeviceTypes.CONTACT_SENSOR.value,
            "product_model": "DWS3U",
            "mac": "CONTACT456",
            "nickname": "Test Contact Sensor",
            "device_params": {"ip": "192.168.1.101"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "property_id, value, expected",
    [
        (PropertyIDs.MOTION_STATE, "1", True),
        (PropertyIDs.MOTION_STATE, "0", False),
    ],
)
async def test_update_motion_sensor(sensor_service, property_id, value, expected):
    motion_sensor = _motion_sensor()
    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": property_id.value, "value": value}]}
    }

    updated_sensor = await sensor_service.update(motion_sensor)
    assert updated_sensor.detected is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("value, expected", [("1", True), ("0", False)])
async def test_update_contact_sensor(sensor_service, value, expected):
    contact_sensor = _contact_sensor()
    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": PropertyIDs.CONTACT_STATE.value, "value": value}]}
    }

    updated_sensor = await sensor_service.update(contact_sensor)
    assert updated_sensor.detected is expected


@pytest.mark.asyncio
async def test_get_sensors(sensor_service):
    mock_motion_device = MagicMock()
    mock_motion_device.type = DeviceTypes.MOTION_SENSOR
    mock_motion_device.raw_dict = {
        "device_type": DeviceTypes.MOTION_SENSOR.value,
        "product_model": "PIR3U",
        "mac": "MOTION123",
    }

    mock_contact_device = MagicMock()
    mock_contact_device.type = DeviceTypes.CONTACT_SENSOR
    mock_contact_device.raw_dict = {
        "device_type": DeviceTypes.CONTACT_SENSOR.value,
        "product_model": "DWS3U",
        "mac": "CONTACT456",
    }

    sensor_service.get_object_list.return_value = [mock_motion_device, mock_contact_device]

    sensors = await sensor_service.get_sensors()

    assert len(sensors) == 2
    assert all(isinstance(s, Sensor) for s in sensors)
    sensor_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_and_deregister_for_updates(sensor_service):
    motion_sensor = _motion_sensor()
    mock_callback = MagicMock()

    await sensor_service.register_for_updates(motion_sensor, mock_callback)

    assert len(sensor_service._subscribers) == 1
    assert sensor_service._subscribers[0] == (motion_sensor, mock_callback)

    await sensor_service.deregister_for_updates(motion_sensor)
    assert len(sensor_service._subscribers) == 0


@pytest.mark.asyncio
async def test_update_with_unknown_property(sensor_service):
    motion_sensor = _motion_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": "unknown_property", "value": "1"}]}
    }

    updated_sensor = await sensor_service.update(motion_sensor)
    assert not updated_sensor.detected