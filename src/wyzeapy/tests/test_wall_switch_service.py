import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.wall_switch_service import (
    WallSwitchService,
    WallSwitch,
    SinglePressType,
    WallSwitchProps,
)
from wyzeapy.types import DeviceTypes
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
def wall_switch_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = WallSwitchService(auth_lib=mock_auth_lib)
    service._wall_switch_get_iot_prop = AsyncMock()
    service._wall_switch_set_iot_prop = AsyncMock()
    service.get_object_list = AsyncMock()
    return service


def _test_switch():
    return WallSwitch(
        {
            "device_type": DeviceTypes.COMMON.value,
            "product_model": "LD_SS1",
            "mac": "SWITCH123",
            "nickname": "Test Wall Switch",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "props, expected_power, expected_iot, expected_type",
    [
        (
            {
                "iot_state": "connected",
                "switch-power": True,
                "switch-iot": False,
                "single_press_type": 1,
            },
            True,
            False,
            SinglePressType.CLASSIC,
        ),
        (
            {
                "iot_state": "connected",
                "switch-power": False,
                "switch-iot": True,
                "single_press_type": 2,
            },
            False,
            True,
            SinglePressType.IOT,
        ),
    ],
)
async def test_update_wall_switch(wall_switch_service, props, expected_power, expected_iot, expected_type):
    test_switch = _test_switch()
    wall_switch_service._wall_switch_get_iot_prop.return_value = {"data": {"props": props}}

    updated_switch = await wall_switch_service.update(test_switch)

    assert updated_switch.available
    assert updated_switch.switch_power is expected_power
    assert updated_switch.switch_iot is expected_iot
    assert updated_switch.single_press_type == expected_type
    assert updated_switch.on  # derived property should be True in both cases


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

    other_device = MagicMock()
    other_device.type = DeviceTypes.COMMON
    other_device.product_model = "OTHER_MODEL"

    wall_switch_service.get_object_list.return_value = [mock_switch, other_device]

    switches = await wall_switch_service.get_switches()

    assert len(switches) == 1
    assert isinstance(switches[0], WallSwitch)
    wall_switch_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "press_type, prop",
    [
        (SinglePressType.CLASSIC, WallSwitchProps.SWITCH_POWER),
        (SinglePressType.IOT, WallSwitchProps.SWITCH_IOT),
    ],
)
async def test_turn_on_off_modes(wall_switch_service, press_type, prop):
    test_switch = _test_switch()
    test_switch.single_press_type = press_type

    await wall_switch_service.turn_on(test_switch)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(test_switch, prop, True)

    await wall_switch_service.turn_off(test_switch)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(test_switch, prop, False)


@pytest.mark.asyncio
async def test_set_single_press_type(wall_switch_service):
    test_switch = _test_switch()

    await wall_switch_service.set_single_press_type(test_switch, SinglePressType.IOT)
    wall_switch_service._wall_switch_set_iot_prop.assert_awaited_with(
        test_switch, WallSwitchProps.SINGLE_PRESS_TYPE, SinglePressType.IOT.value
    )


@pytest.mark.asyncio
async def test_update_with_invalid_property(wall_switch_service):
    test_switch = _test_switch()
    wall_switch_service._wall_switch_get_iot_prop.return_value = {
        "data": {"props": {"invalid_property": "some_value", "switch-power": True}}
    }

    updated_switch = await wall_switch_service.update(test_switch)
    assert updated_switch.switch_power
    assert updated_switch.single_press_type == SinglePressType.CLASSIC
    assert not updated_switch.switch_iot 