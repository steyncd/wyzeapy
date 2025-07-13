import pytest
from unittest.mock import AsyncMock, MagicMock

from wyzeapy.services.lock_service import LockService, Lock
from wyzeapy.types import DeviceTypes
from wyzeapy.exceptions import UnknownApiError
import urllib.parse

# Patch quote_plus globally as original tests
urllib.parse.quote_plus = MagicMock(return_value="mocked_quoted_string")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def lock_service(mock_auth_lib):
    service = LockService(auth_lib=mock_auth_lib)
    service._get_lock_info = AsyncMock()
    service._lock_control = AsyncMock()
    # Provide fake id/token response structure expected by tests
    service._auth_lib.get.return_value = {
        "ErrNo": 0,
        "token": {"id": "mock_id", "token": "0123456789abcdef0123456789abcdef"},
    }
    return service


def _lock_stub(mac: str, online: int = 1):
    return Lock(
        {
            "device_type": "Lock",
            "mac": mac,
            "onoff_line": online,
            "door_open_status": 0,
            "trash_mode": 0,
            "locker_status": {"hardlock": 2},
            "raw_dict": {},
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_lock_online(lock_service):
    lck = _lock_stub("LOCK_ON", online=1)
    lck.product_model = "YD_BT1"

    lock_service._get_lock_info.return_value = {
        "device": {
            "onoff_line": 1,
            "door_open_status": 0,
            "trash_mode": 0,
            "locker_status": {"hardlock": 2},
        }
    }

    updated = await lock_service.update(lck)

    assert updated.available
    assert not updated.door_open
    assert not updated.trash_mode
    assert updated.unlocked
    assert not updated.unlocking
    assert not updated.locking
    lock_service._get_lock_info.assert_awaited_once_with(lck)


@pytest.mark.asyncio
async def test_update_lock_offline(lock_service):
    lck = _lock_stub("LOCK_OFF", online=0)
    lck.product_model = "YD_BT1"

    lock_service._get_lock_info.return_value = {
        "device": {
            "onoff_line": 0,
            "door_open_status": 1,
            "trash_mode": 1,
            "locker_status": {"hardlock": 1},
        }
    }

    updated = await lock_service.update(lck)

    assert not updated.available
    assert updated.door_open
    assert updated.trash_mode
    assert not updated.unlocked
    assert not updated.unlocking
    assert not updated.locking
    lock_service._get_lock_info.assert_awaited_once_with(lck)


@pytest.mark.asyncio
async def test_get_locks(lock_service):
    dev = MagicMock()
    dev.type = DeviceTypes.LOCK
    dev.raw_dict = {"device_type": "Lock"}

    lock_service.get_object_list = AsyncMock(return_value=[dev])

    locks = await lock_service.get_locks()
    assert len(locks) == 1
    assert isinstance(locks[0], Lock)
    lock_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_lock_unlock(lock_service):
    lck = _lock_stub("MAC")

    await lock_service.lock(lck)
    lock_service._lock_control.assert_awaited_with(lck, "remoteLock")

    await lock_service.unlock(lck)
    lock_service._lock_control.assert_awaited_with(lck, "remoteUnlock")


@pytest.mark.asyncio
async def test_lock_control_error_handling(lock_service):
    lck = _lock_stub("ERR")
    lock_service._lock_control.side_effect = UnknownApiError("failure")

    with pytest.raises(UnknownApiError):
        await lock_service.lock(lck)
    with pytest.raises(UnknownApiError):
        await lock_service.unlock(lck) 