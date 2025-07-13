import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.hms_service import HMSService, HMSMode
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
async def hms_service():
    """Return an HMSService instance with its network calls mocked out."""
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = await HMSService.create(mock_auth_lib)

    # Patch out I/O heavy internals
    service._get_plan_binding_list_by_user = AsyncMock()
    service._monitoring_profile_state_status = AsyncMock()
    service._monitoring_profile_active = AsyncMock()
    service._disable_reme_alarm = AsyncMock()

    return service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "api_message, expected_mode",
    [
        ("changing", HMSMode.CHANGING),
        ("disarm", HMSMode.DISARMED),
        ("away", HMSMode.AWAY),
        ("home", HMSMode.HOME),
    ],
)
async def test_update_modes(hms_service, api_message, expected_mode):
    """Verify that update() returns the correct HMSMode for various API messages."""
    hms_service._monitoring_profile_state_status.return_value = {"message": api_message}

    mode = await hms_service.update("test_hms_id")

    assert mode == expected_mode


@pytest.mark.asyncio
async def test_set_mode_disarmed(hms_service):
    hms_service._hms_id = "test_hms_id"

    await hms_service.set_mode(HMSMode.DISARMED)

    hms_service._disable_reme_alarm.assert_awaited_with("test_hms_id")
    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 0, 0)


@pytest.mark.asyncio
async def test_set_mode_away(hms_service):
    hms_service._hms_id = "test_hms_id"

    await hms_service.set_mode(HMSMode.AWAY)

    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 0, 1)


@pytest.mark.asyncio
async def test_set_mode_home(hms_service):
    hms_service._hms_id = "test_hms_id"

    await hms_service.set_mode(HMSMode.HOME)

    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 1, 0)


@pytest.mark.asyncio
async def test_get_hms_id_with_existing_id(hms_service):
    hms_service._hms_id = "existing_hms_id"
    hms_id = await hms_service._get_hms_id()
    assert hms_id == "existing_hms_id"


@pytest.mark.asyncio
async def test_get_hms_id_with_no_hms(hms_service):
    hms_service._hms_id = None
    hms_service._get_plan_binding_list_by_user.return_value = {"data": []}

    hms_id = await hms_service._get_hms_id()
    assert hms_id is None


@pytest.mark.asyncio
async def test_get_hms_id_finds_id(hms_service):
    hms_service._hms_id = None
    hms_service._get_plan_binding_list_by_user.return_value = {
        "data": [
            {"deviceList": [{"device_id": "found_hms_id"}]}
        ]
    }

    hms_id = await hms_service._get_hms_id()
    assert hms_id == "found_hms_id"
    assert hms_service._hms_id == "found_hms_id" 