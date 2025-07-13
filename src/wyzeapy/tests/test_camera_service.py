import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.camera_service import CameraService, Camera
from wyzeapy.types import DeviceTypes, PropertyIDs
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
def camera_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = CameraService(auth_lib=mock_auth_lib)
    service._get_property_list = AsyncMock()
    service._get_event_list = AsyncMock()
    service._run_action = AsyncMock()
    service._run_action_devicemgmt = AsyncMock()
    service._set_property = AsyncMock()
    service._set_property_list = AsyncMock()
    service._set_toggle = AsyncMock()
    service.get_updated_params = AsyncMock()
    return service


def _legacy_camera():
    return Camera(
        {
            "device_type": DeviceTypes.CAMERA.value,
            "product_model": "WYZEC1",
            "mac": "TEST123",
            "nickname": "Test Camera",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
async def test_update_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    camera_service._get_event_list.return_value = {
        "data": {
            "event_list": [
                {"event_ts": 1234567890, "device_mac": "TEST123", "event_type": "motion"}
            ]
        }
    }

    camera_service._get_property_list.return_value = [
        (PropertyIDs.AVAILABLE, "1"),
        (PropertyIDs.ON, "1"),
        (PropertyIDs.CAMERA_SIREN, "0"),
        (PropertyIDs.ACCESSORY, "0"),
        (PropertyIDs.NOTIFICATION, "1"),
        (PropertyIDs.MOTION_DETECTION, "1"),
    ]

    updated_camera = await camera_service.update(test_camera)

    assert updated_camera.available
    assert updated_camera.on
    assert not updated_camera.siren
    assert not updated_camera.floodlight
    assert updated_camera.notify
    assert updated_camera.motion
    assert updated_camera.last_event is not None
    assert updated_camera.last_event_ts == 1234567890


@pytest.fixture()
def devicemgmt_camera():
    return Camera(
        {
            "device_type": DeviceTypes.CAMERA.value,
            "product_model": "LD_CFP",
            "mac": "TEST456",
            "nickname": "Test DeviceMgmt Camera",
            "device_params": {"ip": "192.168.1.101"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
async def test_update_devicemgmt_camera(camera_service, devicemgmt_camera):
    camera_service._get_iot_prop_devicemgmt = AsyncMock(
        return_value={
            "data": {
                "capabilities": [
                    {"name": "camera", "properties": {"motion-detect-recording": True}},
                    {"name": "floodlight", "properties": {"on": True}},
                    {"name": "siren", "properties": {"state": True}},
                    {
                        "name": "iot-device",
                        "properties": {
                            "push-switch": True,
                            "iot-power": True,
                            "iot-state": True,
                        },
                    },
                ]
            }
        }
    )

    updated_camera = await camera_service.update(devicemgmt_camera)

    assert updated_camera.available
    assert updated_camera.on
    assert updated_camera.siren
    assert updated_camera.floodlight
    assert updated_camera.notify
    assert updated_camera.motion


@pytest.mark.asyncio
async def test_turn_on_off_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    await camera_service.turn_on(test_camera)
    camera_service._run_action.assert_awaited_with(test_camera, "power_on")

    await camera_service.turn_off(test_camera)
    camera_service._run_action.assert_awaited_with(test_camera, "power_off")


@pytest.mark.asyncio
async def test_siren_control_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    await camera_service.siren_on(test_camera)
    camera_service._run_action.assert_awaited_with(test_camera, "siren_on")

    await camera_service.siren_off(test_camera)
    camera_service._run_action.assert_awaited_with(test_camera, "siren_off")


@pytest.mark.asyncio
async def test_floodlight_control_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    await camera_service.floodlight_on(test_camera)
    camera_service._set_property.assert_awaited_with(
        test_camera, PropertyIDs.ACCESSORY.value, "1"
    )

    await camera_service.floodlight_off(test_camera)
    camera_service._set_property.assert_awaited_with(
        test_camera, PropertyIDs.ACCESSORY.value, "2"
    )


@pytest.mark.asyncio
async def test_notification_control_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    await camera_service.turn_on_notifications(test_camera)
    camera_service._set_property.assert_awaited_with(
        test_camera, PropertyIDs.NOTIFICATION.value, "1"
    )

    await camera_service.turn_off_notifications(test_camera)
    camera_service._set_property.assert_awaited_with(
        test_camera, PropertyIDs.NOTIFICATION.value, "0"
    )


@pytest.mark.asyncio
async def test_motion_detection_control_legacy_camera(camera_service):
    test_camera = _legacy_camera()

    await camera_service.turn_on_motion_detection(test_camera)
    camera_service._set_property.assert_any_await(
        test_camera, PropertyIDs.MOTION_DETECTION.value, "1"
    )
    camera_service._set_property.assert_any_await(
        test_camera, PropertyIDs.MOTION_DETECTION_TOGGLE.value, "1"
    )

    await camera_service.turn_off_motion_detection(test_camera)
    camera_service._set_property.assert_any_await(
        test_camera, PropertyIDs.MOTION_DETECTION.value, "0"
    )
    camera_service._set_property.assert_any_await(
        test_camera, PropertyIDs.MOTION_DETECTION_TOGGLE.value, "0"
    ) 