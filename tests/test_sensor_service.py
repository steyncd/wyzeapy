import pytest
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.sensor_service import SensorService, Sensor
from wyzeapy.types import DeviceTypes, PropertyIDs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sensor_service(mock_auth_lib):
    service = SensorService(auth_lib=mock_auth_lib)
    service._get_device_info = AsyncMock()
    service.get_updated_params = AsyncMock()
    service.get_object_list = AsyncMock()
    # Reset subscribers for isolation
    service._subscribers = []
    return service


def _motion_sensor(mac: str = "MOTION123"):
    return Sensor(
        {
            "device_type": DeviceTypes.MOTION_SENSOR.value,
            "product_model": "PIR3U",
            "mac": mac,
            "nickname": "Motion",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


def _contact_sensor(mac: str = "CONTACT456"):
    return Sensor(
        {
            "device_type": DeviceTypes.CONTACT_SENSOR.value,
            "product_model": "DWS3U",
            "mac": mac,
            "nickname": "Contact",
            "device_params": {"ip": "192.168.1.101"},
            "raw_dict": {},
        }
    )


# ---------------------------------------------------------------------------
# Tests – update helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_motion_sensor_detected(sensor_service):
    sensor = _motion_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": PropertyIDs.MOTION_STATE.value, "value": "1"}]}
    }

    updated = await sensor_service.update(sensor)
    assert updated.detected


@pytest.mark.asyncio
async def test_update_motion_sensor_not_detected(sensor_service):
    sensor = _motion_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": PropertyIDs.MOTION_STATE.value, "value": "0"}]}
    }

    updated = await sensor_service.update(sensor)
    assert not updated.detected


@pytest.mark.asyncio
async def test_update_contact_sensor_detected(sensor_service):
    sensor = _contact_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": PropertyIDs.CONTACT_STATE.value, "value": "1"}]}
    }

    updated = await sensor_service.update(sensor)
    assert updated.detected


@pytest.mark.asyncio
async def test_update_contact_sensor_not_detected(sensor_service):
    sensor = _contact_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": PropertyIDs.CONTACT_STATE.value, "value": "0"}]}
    }

    updated = await sensor_service.update(sensor)
    assert not updated.detected


# ---------------------------------------------------------------------------
# get_sensors helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sensors(sensor_service):
    motion_device = MagicMock()
    motion_device.type = DeviceTypes.MOTION_SENSOR
    motion_device.raw_dict = {
        "device_type": DeviceTypes.MOTION_SENSOR.value,
        "product_model": "PIR3U",
        "mac": "MOTION123",
    }

    contact_device = MagicMock()
    contact_device.type = DeviceTypes.CONTACT_SENSOR
    contact_device.raw_dict = {
        "device_type": DeviceTypes.CONTACT_SENSOR.value,
        "product_model": "DWS3U",
        "mac": "CONTACT456",
    }

    sensor_service.get_object_list.return_value = [motion_device, contact_device]

    sensors = await sensor_service.get_sensors()

    assert len(sensors) == 2
    assert all(isinstance(s, Sensor) for s in sensors)
    sensor_service.get_object_list.assert_awaited_once()


# ---------------------------------------------------------------------------
# subscribe helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_and_deregister_for_updates(sensor_service):
    sensor = _motion_sensor()
    callback = MagicMock()

    await sensor_service.register_for_updates(sensor, callback)
    assert sensor_service._subscribers == [(sensor, callback)]

    await sensor_service.deregister_for_updates(sensor)
    assert not sensor_service._subscribers


# ---------------------------------------------------------------------------
# Unknown property handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_with_unknown_property(sensor_service):
    sensor = _motion_sensor()

    sensor_service._get_device_info.return_value = {
        "data": {"property_list": [{"pid": "unknown", "value": "1"}]}
    }

    updated = await sensor_service.update(sensor)
    # Should retain default (False)
    assert not updated.detected