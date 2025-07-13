import pytest
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.wall_switch_service import (
    WallSwitchService,
    WallSwitch,
    SinglePressType,
    WallSwitchProps,
)
from wyzeapy.types import DeviceTypes

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def wall_switch_service(mock_auth_lib):
    svc = WallSwitchService(auth_lib=mock_auth_lib)
    svc._wall_switch_get_iot_prop = AsyncMock()
    svc._wall_switch_set_iot_prop = AsyncMock()
    svc.get_object_list = AsyncMock()
    return svc


def _switch_stub(mac="SWITCH123"):
    return WallSwitch(
        {
            "device_type": DeviceTypes.COMMON.value,
            "product_model": "LD_SS1",
            "mac": mac,
            "nickname": "Test Wall Switch",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_wall_switch_classic(wall_switch_service):
    sw = _switch_stub()
    wall_switch_service._wall_switch_get_iot_prop.return_value = {
        "data": {
            "props": {
                "iot_state": "connected",
                "switch-power": True,
                "switch-iot": False,
                "single_press_type": 1,
            }
        }
    }
    updated = await wall_switch_service.update(sw)
    assert updated.available
    assert updated.switch_power is True
    assert updated.switch_iot is False
    assert updated.single_press_type == SinglePressType.CLASSIC
    assert updated.on


@pytest.mark.asyncio
async def test_update_wall_switch_iot_mode(wall_switch_service):
    sw = _switch_stub()
    wall_switch_service._wall_switch_get_iot_prop.return_value = {
        "data": {
            "props": {
                "iot_state": "connected",
                "switch-power": False,
                "switch-iot": True,
                "single_press_type": 2,
            }
        }
    }
    updated = await wall_switch_service.update(sw)
    assert updated.available
    assert not updated.switch_power
    assert updated.switch_iot
    assert updated.single_press_type == SinglePressType.IOT
    assert updated.on


# ---------------------------------------------------------------------------
# get_switches helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_switches(wall_switch_service):
    mock_switch = MagicMock()
    mock_switch.type = DeviceTypes.COMMON
    mock_switch.product_model = "LD_SS1"
    mock_switch.raw_dict = {
        "device_type": DeviceTypes.COMMON.value,
        "product_model": "LD_SS1",
        "mac": "SWITCH123",
    }
    other = MagicMock()
    other.type = DeviceTypes.COMMON
    other.product_model = "OTHER_MODEL"

    wall_switch_service.get_object_list.return_value = [mock_switch, other]
    switches = await wall_switch_service.get_switches()
    assert len(switches) == 1
    assert isinstance(switches[0], WallSwitch)
    wall_switch_service.get_object_list.assert_awaited_once()


# ---------------------------------------------------------------------------
# Turn on/off helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_on_off_classic(wall_switch_service):
    sw = _switch_stub()
    sw.single_press_type = SinglePressType.CLASSIC

    await wall_switch_service.turn_on(sw)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(sw, WallSwitchProps.SWITCH_POWER, True)

    await wall_switch_service.turn_off(sw)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(sw, WallSwitchProps.SWITCH_POWER, False)


@pytest.mark.asyncio
async def test_turn_on_off_iot(wall_switch_service):
    sw = _switch_stub()
    sw.single_press_type = SinglePressType.IOT

    await wall_switch_service.turn_on(sw)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(sw, WallSwitchProps.SWITCH_IOT, True)

    await wall_switch_service.turn_off(sw)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(sw, WallSwitchProps.SWITCH_IOT, False)


# ---------------------------------------------------------------------------
# Other helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_single_press_type(wall_switch_service):
    sw = _switch_stub()
    await wall_switch_service.set_single_press_type(sw, SinglePressType.IOT)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(
        sw, WallSwitchProps.SINGLE_PRESS_TYPE, SinglePressType.IOT.value
    )


@pytest.mark.asyncio
async def test_update_with_invalid_property(wall_switch_service):
    sw = _switch_stub()
    wall_switch_service._wall_switch_get_iot_prop.return_value = {
        "data": {"props": {"invalid_property": "x", "switch-power": True}}
    }
    updated = await wall_switch_service.update(sw)
    assert updated.switch_power is True
    assert updated.single_press_type == SinglePressType.CLASSIC
    assert not updated.switch_iot 