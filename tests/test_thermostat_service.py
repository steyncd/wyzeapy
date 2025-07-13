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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def thermostat_service(mock_auth_lib):
    svc = ThermostatService(auth_lib=mock_auth_lib)
    svc._thermostat_get_iot_prop = AsyncMock()
    svc._thermostat_set_iot_prop = AsyncMock()
    svc.get_object_list = AsyncMock()
    return svc


def _thermostat_stub(mac="THERM123"):
    return Thermostat(
        {
            "device_type": DeviceTypes.THERMOSTAT.value,
            "product_model": "WLPTH1",
            "mac": mac,
            "nickname": "Test Thermostat",
            "device_params": {"ip": "192.168.1.100"},
            "raw_dict": {},
        }
    )


# ---------------------------------------------------------------------------
# Update helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_thermostat(thermostat_service):
    th = _thermostat_stub()
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
    updated = await thermostat_service.update(th)
    assert updated.temp_unit == TemperatureUnit.FAHRENHEIT
    assert updated.cool_set_point == 74
    assert updated.heat_set_point == 64
    assert updated.fan_mode == FanMode.AUTO
    assert updated.hvac_mode == HVACMode.AUTO
    assert updated.preset == Preset.HOME
    assert updated.temperature == 71.5
    assert updated.available
    assert updated.humidity == 50
    assert updated.hvac_state == HVACState.IDLE


# ---------------------------------------------------------------------------
# get_thermostats helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_thermostats(thermostat_service):
    mock_th = MagicMock()
    mock_th.type = DeviceTypes.THERMOSTAT
    mock_th.raw_dict = {
        "device_type": DeviceTypes.THERMOSTAT.value,
        "product_model": "WLPTH1",
        "mac": "THERM123",
    }
    thermostat_service.get_object_list.return_value = [mock_th]
    ths = await thermostat_service.get_thermostats()
    assert len(ths) == 1
    assert isinstance(ths[0], Thermostat)
    thermostat_service.get_object_list.assert_awaited_once()


# ---------------------------------------------------------------------------
# Set point / mode helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_points_and_modes(thermostat_service):
    th = _thermostat_stub()

    await thermostat_service.set_cool_point(th, 75)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(th, ThermostatProps.COOL_SP, 75)

    await thermostat_service.set_heat_point(th, 68)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(th, ThermostatProps.HEAT_SP, 68)

    await thermostat_service.set_hvac_mode(th, HVACMode.COOL)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(th, ThermostatProps.MODE_SYS, HVACMode.COOL.value)

    await thermostat_service.set_fan_mode(th, FanMode.ON)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(th, ThermostatProps.FAN_MODE, FanMode.ON.value)

    await thermostat_service.set_preset(th, Preset.AWAY)
    thermostat_service._thermostat_set_iot_prop.assert_awaited_with(th, ThermostatProps.CURRENT_SCENARIO, Preset.AWAY.value)


# ---------------------------------------------------------------------------
# Invalid property handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_with_invalid_property(thermostat_service):
    th = _thermostat_stub()
    thermostat_service._thermostat_get_iot_prop.return_value = {
        "data": {"props": {"invalid_property": "some_value", "temperature": "71.5"}}
    }
    updated = await thermostat_service.update(th)
    assert updated.temperature == 71.5
    assert updated.temp_unit == TemperatureUnit.FAHRENHEIT
    assert updated.cool_set_point == 74
    assert updated.heat_set_point == 64 