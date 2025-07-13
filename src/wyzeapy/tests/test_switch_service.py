import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.switch_service import SwitchService, SwitchUsageService, Switch
from wyzeapy.types import DeviceTypes, PropertyIDs
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
def switch_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = SwitchService(auth_lib=mock_auth_lib)
    service._get_property_list = AsyncMock()
    service.get_updated_params = AsyncMock()
    service.get_object_list = AsyncMock()
    service._set_property = AsyncMock()
    return service


def _test_switch():
    return Switch(
        {
            "device_type": DeviceTypes.PLUG.value,
            "product_model": "WLPP1",
            "mac": "SWITCH123",
            "nickname": "Test Switch",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("is_on", [True, False])
async def test_update_switch_on_off(switch_service, is_on):
    test_switch = _test_switch()
    switch_service._get_property_list.return_value = [
        (PropertyIDs.ON, "1" if is_on else "0"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated_switch = await switch_service.update(test_switch)

    assert updated_switch.on is is_on
    assert updated_switch.available


@pytest.mark.asyncio
async def test_get_switches(switch_service):
    mock_plug = MagicMock()
    mock_plug.type = DeviceTypes.PLUG
    mock_plug.raw_dict = {
        "device_type": DeviceTypes.PLUG.value,
        "product_model": "WLPP1",
        "mac": "PLUG123",
    }

    mock_outdoor_plug = MagicMock()
    mock_outdoor_plug.type = DeviceTypes.OUTDOOR_PLUG
    mock_outdoor_plug.raw_dict = {
        "device_type": DeviceTypes.OUTDOOR_PLUG.value,
        "product_model": "WLPPO",
        "mac": "OUTPLUG456",
    }

    switch_service.get_object_list.return_value = [mock_plug, mock_outdoor_plug]

    switches = await switch_service.get_switches()

    assert len(switches) == 2
    assert all(isinstance(s, Switch) for s in switches)
    switch_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_turn_on_off(switch_service):
    test_switch = _test_switch()

    await switch_service.turn_on(test_switch)
    switch_service._set_property.assert_awaited_with(test_switch, PropertyIDs.ON.value, "1")

    await switch_service.turn_off(test_switch)
    switch_service._set_property.assert_awaited_with(test_switch, PropertyIDs.ON.value, "0")


# ==== SwitchUsageService tests ====

@pytest.fixture()
def usage_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = SwitchUsageService(auth_lib=mock_auth_lib)
    service._get_plug_history = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_update_usage_history(usage_service):
    test_switch = _test_switch()

    mock_usage_data = {
        "total_power": 100,
        "time_series": [
            {"power": 10, "timestamp": 1234567890},
            {"power": 20, "timestamp": 1234567891},
        ],
    }
    usage_service._get_plug_history.return_value = mock_usage_data

    now = datetime.now()
    expected_end_time = int(datetime.timestamp(now) * 1000)
    expected_start_time = int(datetime.timestamp(now - timedelta(hours=25)) * 1000)

    updated_switch = await usage_service.update(test_switch)

    assert updated_switch.usage_history == mock_usage_data
    usage_service._get_plug_history.assert_awaited_with(
        test_switch, expected_start_time, expected_end_time
    ) 