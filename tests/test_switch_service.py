import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.switch_service import SwitchService, SwitchUsageService, Switch
from wyzeapy.types import DeviceTypes, PropertyIDs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def switch_service(mock_auth_lib):
    service = SwitchService(auth_lib=mock_auth_lib)
    service._get_property_list = AsyncMock()
    service.get_updated_params = AsyncMock()
    service.get_object_list = AsyncMock()
    service._set_property = AsyncMock()
    return service


@pytest.fixture
async def usage_service(mock_auth_lib):
    service = SwitchUsageService(auth_lib=mock_auth_lib)
    service._get_plug_history = AsyncMock()
    return service


def _switch_stub(mac="SWITCH123"):
    return Switch(
        {
            "device_type": DeviceTypes.PLUG.value,
            "product_type": DeviceTypes.PLUG.value,
            "product_model": "WLPP1",
            "mac": mac,
            "nickname": "Test Switch",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


# ---------------------------------------------------------------------------
# SwitchService tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_switch_on(switch_service):
    sw = _switch_stub()
    switch_service._get_property_list.return_value = [
        (PropertyIDs.ON, "1"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated = await switch_service.update(sw)

    assert updated.on
    assert updated.available


@pytest.mark.asyncio
async def test_update_switch_off(switch_service):
    sw = _switch_stub()
    switch_service._get_property_list.return_value = [
        (PropertyIDs.ON, "0"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated = await switch_service.update(sw)

    assert not updated.on
    assert updated.available


@pytest.mark.asyncio
async def test_get_switches(switch_service):
    mock_plug = MagicMock()
    mock_plug.type = DeviceTypes.PLUG
    mock_plug.raw_dict = {
        "device_type": DeviceTypes.PLUG.value,
        "product_model": "WLPP1",
        "mac": "PLUG123",
    }

    mock_outdoor = MagicMock()
    mock_outdoor.type = DeviceTypes.OUTDOOR_PLUG
    mock_outdoor.raw_dict = {
        "device_type": DeviceTypes.OUTDOOR_PLUG.value,
        "product_model": "WLPPO",
        "mac": "OUTPLUG456",
    }

    switch_service.get_object_list.return_value = [mock_plug, mock_outdoor]

    switches = await switch_service.get_switches()

    assert len(switches) == 2
    assert all(isinstance(s, Switch) for s in switches)
    switch_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_turn_on(switch_service):
    sw = _switch_stub()
    await switch_service.turn_on(sw)
    switch_service._set_property.assert_awaited_with(sw, PropertyIDs.ON.value, "1")


@pytest.mark.asyncio
async def test_turn_off(switch_service):
    sw = _switch_stub()
    await switch_service.turn_off(sw)
    switch_service._set_property.assert_awaited_with(sw, PropertyIDs.ON.value, "0")


# ---------------------------------------------------------------------------
# SwitchUsageService tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_usage_history(usage_service):
    sw = _switch_stub()
    mock_usage = {
        "total_power": 100,
        "time_series": [
            {"power": 10, "timestamp": 1234567890},
            {"power": 20, "timestamp": 1234567891},
        ],
    }
    usage_service._get_plug_history.return_value = mock_usage

    now = datetime.now()
    expected_end = int(datetime.timestamp(now.astimezone(timezone.utc)) * 1000)
    expected_start = int(
        datetime.timestamp((now - timedelta(hours=25)).astimezone(timezone.utc)) * 1000
    )

    updated = await usage_service.update(sw)
    assert updated.usage_history == mock_usage

    # Validate call parameters with small tolerance
    args, _ = usage_service._get_plug_history.call_args
    assert args[0] == sw
    assert abs(args[1] - expected_start) <= 2
    assert abs(args[2] - expected_end) <= 2 