import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientOSError, ContentTypeError

from wyzeapy.exceptions import UnknownApiError
from wyzeapy.services.camera_service import CameraService, Camera
from wyzeapy.types import DeviceTypes, PropertyIDs, DeviceMgmtToggleProps
from wyzeapy.wyze_auth_lib import WyzeAuthLib


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def camera_service(mock_auth_lib):
    service = CameraService(auth_lib=mock_auth_lib)

    # Replace network-bound helpers with mocks
    service._get_property_list = AsyncMock()
    service._get_event_list = AsyncMock()
    service._run_action = AsyncMock()
    service._run_action_devicemgmt = AsyncMock()
    service._set_property = AsyncMock()
    service._set_property_list = AsyncMock()
    service._set_toggle = AsyncMock()
    service.get_updated_params = AsyncMock()
    service._get_iot_prop_devicemgmt = AsyncMock()
    service.get_object_list = AsyncMock(
        return_value=[
            MagicMock(type=DeviceTypes.CAMERA, raw_dict={"mac": "CAM1"}),
            MagicMock(type=DeviceTypes.CAMERA, raw_dict={"mac": "CAM2"}),
            MagicMock(type=DeviceTypes.LIGHT, raw_dict={"mac": "BULB1"}),
        ]
    )

    # Ensure global state is clean between tests
    CameraService._updater_thread = None
    CameraService._subscribers = []

    return service


# Helper to quickly build a Camera instance

def _camera_stub(mac: str, model: str = "WYZEC1"):
    return Camera(
        {
            "device_type": DeviceTypes.CAMERA.value,
            "product_model": model,
            "mac": mac,
            "nickname": "Test Camera",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


# Specialised camera stubs
_devicemgmt_camera = _camera_stub("TEST456", model="LD_CFP")
_bcp_camera = _camera_stub("TEST789", model="AN_RSCW")
_wco2_camera = _camera_stub("TEST012", model="HL_WCO2")


# ---------------------------------------------------------------------------
# Tests – Update helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_legacy_camera(camera_service):
    camera = _camera_stub("TEST123")

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

    updated = await camera_service.update(camera)

    assert updated.available
    assert updated.on
    assert not updated.siren
    assert not updated.floodlight
    assert updated.notify
    assert updated.motion
    assert updated.last_event_ts == 1234567890


@pytest.mark.asyncio
async def test_update_devicemgmt_camera(camera_service):
    camera = _devicemgmt_camera

    camera_service._get_iot_prop_devicemgmt.return_value = {
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

    updated = await camera_service.update(camera)

    assert updated.on
    assert updated.available
    assert updated.siren
    assert updated.floodlight
    assert updated.motion
    assert updated.notify


# ---------------------------------------------------------------------------
# On / Off helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_on_off_legacy_camera(camera_service):
    camera = _camera_stub("LEGACY1")

    await camera_service.turn_on(camera)
    camera_service._run_action.assert_awaited_with(camera, "power_on")

    await camera_service.turn_off(camera)
    camera_service._run_action.assert_awaited_with(camera, "power_off")


@pytest.mark.asyncio
async def test_turn_on_off_devicemgmt_camera(camera_service):
    camera = _devicemgmt_camera

    await camera_service.turn_on(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "power", "wakeup")

    await camera_service.turn_off(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "power", "sleep")


# ---------------------------------------------------------------------------
# Siren / Floodlight helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_siren_control_devicemgmt_camera(camera_service):
    camera = _devicemgmt_camera

    await camera_service.siren_on(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "siren", "siren-on")

    await camera_service.siren_off(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "siren", "siren-off")


@pytest.mark.asyncio
async def test_floodlight_control_bcp_camera(camera_service):
    camera = _bcp_camera

    await camera_service.floodlight_on(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "spotlight", "1")

    await camera_service.floodlight_off(camera)
    camera_service._run_action_devicemgmt.assert_awaited_with(camera, "spotlight", "0")


# ---------------------------------------------------------------------------
# Motion / Notification toggles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_control_devicemgmt_camera(camera_service):
    camera = _devicemgmt_camera

    await camera_service.turn_on_notifications(camera)
    camera_service._set_toggle.assert_awaited_with(
        camera, DeviceMgmtToggleProps.NOTIFICATION_TOGGLE.value, "1"
    )

    await camera_service.turn_off_notifications(camera)
    camera_service._set_toggle.assert_awaited_with(
        camera, DeviceMgmtToggleProps.NOTIFICATION_TOGGLE.value, "0"
    )


@pytest.mark.asyncio
async def test_motion_detection_control_wco2_camera(camera_service):
    camera = _wco2_camera

    with patch("wyzeapy.services.camera_service.create_pid_pair", side_effect=lambda x, y: (x, y)):
        await camera_service.turn_on_motion_detection(camera)
        camera_service._set_property_list.assert_awaited_with(
            camera, [(PropertyIDs.WCO_MOTION_DETECTION, "1")]
        )

        await camera_service.turn_off_motion_detection(camera)
        camera_service._set_property_list.assert_awaited_with(
            camera, [(PropertyIDs.WCO_MOTION_DETECTION, "0")]
        )


# ---------------------------------------------------------------------------
# Miscellaneous helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cameras(camera_service):
    cameras = await camera_service.get_cameras()

    macs = [c.mac for c in cameras]
    assert macs == ["CAM1", "CAM2"]


@pytest.mark.asyncio
async def test_register_and_deregister_for_updates(camera_service):
    camera = _camera_stub("SUBSCRIBER1")
    callback = MagicMock()

    # Register
    await camera_service.register_for_updates(camera, callback)
    assert len(camera_service._subscribers) == 1

    # Deregister
    await camera_service.deregister_for_updates(camera)
    assert not camera_service._subscribers


@pytest.mark.asyncio
async def test_update_worker_success(camera_service, monkeypatch):
    camera = _camera_stub("THREAD1")
    callback = MagicMock(return_value=None)

    camera_service.update = AsyncMock(return_value=camera)

    await camera_service.register_for_updates(camera, callback)

    # Allow the worker thread a moment to spin.
    await asyncio.sleep(0.2)

    # Stop the worker cleanly
    camera_service._subscribers = []
    camera_service._updater_thread.join(timeout=1)

    assert camera_service.update.call_count > 0
    assert callback.call_count > 0


@pytest.mark.asyncio
async def test_update_worker_exceptions(camera_service):
    camera = _camera_stub("ERR_THREAD")
    callback = MagicMock()

    exceptions_to_raise = [
        UnknownApiError("API Error"),
        ClientOSError(),
        ContentTypeError(request_info=MagicMock(), history=(), status=200, message=""),
    ]

    camera_service.update = AsyncMock(side_effect=exceptions_to_raise)

    with patch("wyzeapy.services.camera_service._LOGGER.warning") as warn_mock, patch(
        "wyzeapy.services.camera_service._LOGGER.error"
    ) as err_mock:
        await camera_service.register_for_updates(camera, callback)
        await asyncio.sleep(0.3)
        camera_service._subscribers = []
        camera_service._updater_thread.join(timeout=1)

        assert camera_service.update.call_count >= len(exceptions_to_raise)
        warn_mock.assert_called_with(
            "The update method detected an UnknownApiError: API Error"
        )
        assert err_mock.call_count >= 2