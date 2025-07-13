import pytest
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.hms_service import HMSService, HMSMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def hms_service(mock_auth_lib):
    svc = await HMSService.create(mock_auth_lib)
    svc._get_plan_binding_list_by_user = AsyncMock()
    svc._monitoring_profile_state_status = AsyncMock()
    svc._monitoring_profile_active = AsyncMock()
    svc._disable_reme_alarm = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# Tests – update helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message, expected_mode",
    [
        ("changing", HMSMode.CHANGING),
        ("disarm", HMSMode.DISARMED),
        ("away", HMSMode.AWAY),
        ("home", HMSMode.HOME),
    ],
)
async def test_update_modes(hms_service, message, expected_mode):
    hms_service._monitoring_profile_state_status.return_value = {"message": message}
    mode = await hms_service.update("hms_id")
    assert mode == expected_mode


# ---------------------------------------------------------------------------
# set_mode helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_mode_disarmed(hms_service):
    hms_service._hms_id = "test_hms_id"
    await hms_service.set_mode(HMSMode.DISARMED)
    hms_service._disable_reme_alarm.assert_awaited_with("test_hms_id")
    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 0, 0)


@pytest.mark.asyncio
async def test_set_mode_away_home(hms_service):
    hms_service._hms_id = "test_hms_id"
    await hms_service.set_mode(HMSMode.AWAY)
    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 0, 1)

    await hms_service.set_mode(HMSMode.HOME)
    hms_service._monitoring_profile_active.assert_awaited_with("test_hms_id", 1, 0)


# ---------------------------------------------------------------------------
# _get_hms_id helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_hms_id_existing(hms_service):
    hms_service._hms_id = "existing"
    assert await hms_service._get_hms_id() == "existing"


@pytest.mark.asyncio
async def test_get_hms_id_no_hms(hms_service):
    hms_service._hms_id = None
    hms_service._get_plan_binding_list_by_user.return_value = {"data": []}
    assert await hms_service._get_hms_id() is None


@pytest.mark.asyncio
async def test_get_hms_id_finds_id(hms_service):
    hms_service._hms_id = None
    hms_service._get_plan_binding_list_by_user.return_value = {
        "data": [{"deviceList": [{"device_id": "found"}]}]
    }
    assert await hms_service._get_hms_id() == "found"
    assert hms_service._hms_id == "found" 