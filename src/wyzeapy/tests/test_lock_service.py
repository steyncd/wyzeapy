import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.lock_service import LockService, Lock
from wyzeapy.types import DeviceTypes
from wyzeapy.exceptions import UnknownApiError


@pytest.fixture()
def lock_service():
    mock_auth_lib = MagicMock()
    service = LockService(auth_lib=mock_auth_lib)
    service._get_lock_info = AsyncMock()
    service._lock_control = AsyncMock()
    return service


def _lock(onoff_line=1, mac="LOCK123", door_open_status=0, trash_mode=0, hardlock=2):
    return Lock(
        {
            "device_type": "Lock",
            "onoff_line": onoff_line,
            "door_open_status": door_open_status,
            "trash_mode": trash_mode,
            "locker_status": {"hardlock": hardlock},
            "raw_dict": {},
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "online, door_open, trash, hardlock, available, unlocked",
    [
        (1, 0, 0, 2, True, True),  # Online/unlocked
        (0, 1, 1, 1, False, False),  # Offline/locked
    ],
)
async def test_update_lock_states(lock_service, online, door_open, trash, hardlock, available, unlocked):
    mock_lock = _lock(onoff_line=online, door_open_status=door_open, trash_mode=trash, hardlock=hardlock)

    lock_service._get_lock_info.return_value = {
        "device": {
            "onoff_line": online,
            "door_open_status": door_open_status,
            "trash_mode": trash,
            "locker_status": {"hardlock": hardlock},
        }
    }

    updated_lock = await lock_service.update(mock_lock)

    assert updated_lock.available is available
    assert updated_lock.door_open is bool(door_open)
    assert updated_lock.trash_mode is bool(trash)
    assert updated_lock.unlocked is unlocked
    assert not updated_lock.unlocking
    assert not updated_lock.locking
    lock_service._get_lock_info.assert_awaited_once_with(mock_lock)


@pytest.mark.asyncio
async def test_get_locks(lock_service):
    mock_device = AsyncMock()
    mock_device.type = DeviceTypes.LOCK
    mock_device.raw_dict = {"device_type": "Lock"}

    lock_service.get_object_list = AsyncMock(return_value=[mock_device])

    locks = await lock_service.get_locks()

    assert len(locks) == 1
    assert isinstance(locks[0], Lock)
    lock_service.get_object_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_lock_unlock(lock_service):
    mock_lock = _lock()

    await lock_service.lock(mock_lock)
    lock_service._lock_control.assert_awaited_with(mock_lock, "remoteLock")

    await lock_service.unlock(mock_lock)
    lock_service._lock_control.assert_awaited_with(mock_lock, "remoteUnlock")


@pytest.mark.asyncio
async def test_lock_control_error_handling(lock_service):
    mock_lock = _lock()
    lock_service._lock_control.side_effect = UnknownApiError("Failed to lock/unlock")

    with pytest.raises(UnknownApiError):
        await lock_service.lock(mock_lock)

    with pytest.raises(UnknownApiError):
        await lock_service.unlock(mock_lock) 