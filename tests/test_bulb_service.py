import pytest
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.bulb_service import BulbService, Bulb
from wyzeapy.types import DeviceTypes, PropertyIDs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def bulb_service(mock_auth_lib):
    """Return a BulbService instance with its network-bound methods mocked."""
    service = BulbService(auth_lib=mock_auth_lib)
    service._get_property_list = AsyncMock()
    service.get_updated_params = AsyncMock()
    return service


# Helper factory to build a Bulb quickly

def _bulb_stub(mac: str, model: str = "WLPA19", product_type=DeviceTypes.MESH_LIGHT):
    return Bulb(
        {
            "device_type": "Light",
            "product_model": model,
            "mac": mac,
            "raw_dict": {},
            "device_params": {"ip": "192.168.1.100"},
            "prop_map": {},
            "product_type": product_type.value,
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_bulb_basic_properties(bulb_service):
    mock_bulb = _bulb_stub("TEST123")

    bulb_service._get_property_list.return_value = [
        (PropertyIDs.BRIGHTNESS, "75"),
        (PropertyIDs.COLOR_TEMP, "4000"),
        (PropertyIDs.ON, "1"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated_bulb = await bulb_service.update(mock_bulb)

    assert updated_bulb.brightness == 75
    assert updated_bulb.color_temp == 4000
    assert updated_bulb.on
    assert updated_bulb.available


@pytest.mark.asyncio
async def test_update_bulb_lightstrip_properties(bulb_service):
    mock_bulb = _bulb_stub(
        "TEST456", model="WLST19", product_type=DeviceTypes.LIGHTSTRIP
    )

    bulb_service._get_property_list.return_value = [
        (PropertyIDs.COLOR, "FF0000"),  # Already stripped of the '#'
        (PropertyIDs.COLOR_MODE, "1"),
        (PropertyIDs.LIGHTSTRIP_EFFECTS, "rainbow"),
        (PropertyIDs.LIGHTSTRIP_MUSIC_MODE, "1"),
        (PropertyIDs.ON, "1"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated_bulb = await bulb_service.update(mock_bulb)

    assert updated_bulb.color == "FF0000"
    assert updated_bulb.color_mode == "1"
    assert updated_bulb.effects == "rainbow"
    assert updated_bulb.music_mode
    assert updated_bulb.on
    assert updated_bulb.available


@pytest.mark.asyncio
async def test_update_bulb_sun_match(bulb_service):
    mock_bulb = _bulb_stub("TEST789")

    bulb_service._get_property_list.return_value = [
        (PropertyIDs.SUN_MATCH, "1"),
        (PropertyIDs.ON, "1"),
        (PropertyIDs.AVAILABLE, "1"),
    ]

    updated_bulb = await bulb_service.update(mock_bulb)

    assert updated_bulb.sun_match
    assert updated_bulb.on
    assert updated_bulb.available


@pytest.mark.asyncio
async def test_update_bulb_invalid_color_temp(bulb_service):
    mock_bulb = _bulb_stub("TEST101")

    bulb_service._get_property_list.return_value = [
        (PropertyIDs.COLOR_TEMP, "invalid"),
        (PropertyIDs.ON, "1"),
    ]

    updated_bulb = await bulb_service.update(mock_bulb)

    # Should default to 2700K when invalid
    assert updated_bulb.color_temp == 2700
    assert updated_bulb.on


@pytest.mark.asyncio
async def test_get_bulbs(bulb_service):
    mock_device = MagicMock()
    mock_device.type = DeviceTypes.LIGHT
    mock_device.raw_dict = {
        "device_type": "Light",
        "product_model": "WLPA19",
        "device_params": {"ip": "192.168.1.104"},
        "prop_map": {},
        "product_type": DeviceTypes.MESH_LIGHT.value,
    }

    bulb_service.get_object_list = AsyncMock(return_value=[mock_device])

    bulbs = await bulb_service.get_bulbs()

    assert len(bulbs) == 1
    assert isinstance(bulbs[0], Bulb)
    bulb_service.get_object_list.assert_awaited_once()