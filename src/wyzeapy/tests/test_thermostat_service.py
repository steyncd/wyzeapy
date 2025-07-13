import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.thermostat_service import (
    ThermostatService,
    Thermostat,
    HVACMode,
    FanMode,
    TemperatureUnit,
    Preset,
    HVACState,
    ThermostatProps,
)
from wyzeapy.types import DeviceTypes
from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture()
def thermostat_service():
    mock_auth_lib = MagicMock(spec=WyzeAuthLib)
    service = ThermostatService(auth_lib=mock_auth_lib)
    service._thermostat_get_iot_prop = AsyncMock()
    service._thermostat_set_iot_prop = AsyncMock()
    service.get_object_list = AsyncMock()
    return service


def _test_thermostat():
    return Thermostat(
        {
            "device_type": DeviceTypes.THERMOSTAT.value,
            "product_model": "WLPTH1",
            "mac": "THERM123",
            "nickname": "Test Thermostat",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
async def test_update_thermostat(thermostat_service):
    test_thermostat = _test_thermostat()

    thermostat_service._thermostat_get_iot_prop.return_value = {
        "data": {
            "props": {
                "temp_unit": "F",
                "cool_sp": "74",
                "heat_sp": "64",
                "fan_mode": "auto",
                "mode_sys": "auto",
                "current_scenario": "home",
                "temperature": "71.5",
                "iot_state": "connected",
                "humidity": "50",
                "working_state": "idle",
            }
        }
    }

    updated_thermostat = await thermostat_service.update(test_thermostat)

    assert updated_thermostat.temp_unit == TemperatureUnit.FAHRENHEIT
    assert updated_thermostat.cool_set_point == 74
    assert updated_thermostat.heat_set_point == 64
    assert updated_thermostat.fan_mode == FanMode.AUTO
    assert updated_thermostat.hvac_mode == HVACMode.AUTO
    assert updated_thermostat.preset == Preset.HOME
    assert updated_thermostat.temperature == 71.5
    assert updated_thermostat.available
    assert updated_thermostat.humidity == 50
    assert updated_thermostat.hvac_state == HVACState.IDLE


@pytest.mark.asyncio
async def test_get_thermostats(thermostat_service):
    mock_thermostat_device = MagicMock()
    mock_thermostat_device.type = DeviceTypes.THERMOSTAT
    mock_thermostat_device.raw_dict = {
        "device_type": DeviceTypes.THERMOSTAT.value,
        "product_model": "WLPTH1",
        "mac": "THERM123",
    }

    thermostat_service.get_object_list.return_value = [mock_thermostat_device]

    thermostats = await thermostat_service.get_thermostats()

    assert len(thermostats) == 1
    assert isinstance(thermostats[0], Thermostat)
    thermostat_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_points_and_modes(thermostat_service):
    test_thermostat = _test_thermostat()

    await thermostat_service.set_cool_point(test_thermostat, 75)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(
        test_thermostat, ThermostatProps.COOL_SP, 75
    )

    await thermostat_service.set_heat_point(test_thermostat, 68)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(
        test_thermostat, ThermostatProps.HEAT_SP, 68
    )

    await thermostat_service.set_hvac_mode(test_thermostat, HVACMode.COOL)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(
        test_thermostat, ThermostatProps.MODE_SYS, HVACMode.COOL.value
    )

    await thermostat_service.set_fan_mode(test_thermostat, FanMode.ON)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(
        test_thermostat, ThermostatProps.FAN_MODE, FanMode.ON.value
    )

    await thermostat_service.set_preset(test_thermostat, Preset.AWAY)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(
        test_thermostat, ThermostatProps.CURRENT_SCENARIO, Preset.AWAY.value
    )


@pytest.mark.asyncio
async def test_update_with_invalid_property(thermostat_service):
    test_thermostat = _test_thermostat()

    thermostat_service._thermostat_get_iot_prop.return_value = {
        "data": {
            "props": {"invalid_property": "some_value", "temperature": "71.5"}
        }
    }

    updated_thermostat = await thermostat_service.update(test_thermostat)

    assert updated_thermostat.temperature == 71.5
    # Defaults unchanged
    assert updated_thermostat.temp_unit == TemperatureUnit.FAHRENHEIT
    assert updated_thermostat.cool_set_point == 74
    assert updated_thermostat.heat_set_point == 64 