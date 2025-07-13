
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import threading
import logging
from wyzeapy.services.update_manager import DeviceUpdater, UpdateManager, INTERVAL, MAX_SLOTS
from wyzeapy.types import Device


class TestDeviceUpdater:
    def setup_method(self):
        self.mock_service = MagicMock()
        self.mock_device = MagicMock(spec=Device)
        self.mock_device.nickname = "TestDevice"
        self.mock_device.callback_function = AsyncMock()

    def test_init(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        assert updater.service == self.mock_service
        assert updater.device == self.mock_device
        assert updater.update_in == 0
        assert updater.updates_per_interval == 5  # ceil(300/60)

    @pytest.mark.asyncio
    async def test_update_when_ready(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        updater.update_in = 0
        self.mock_service.update = AsyncMock(return_value=self.mock_device)
        mock_mutex = MagicMock()
        mock_mutex.acquire = MagicMock()
        mock_mutex.release = MagicMock()

        await updater.update(mock_mutex)

        self.mock_service.update.assert_awaited_once_with(self.mock_device)
        self.mock_device.callback_function.assert_called_once_with(self.mock_device)
        mock_mutex.acquire.assert_called_once()
        mock_mutex.release.assert_called_once()
        assert updater.update_in == 60  # Reset to ceil(INTERVAL / updates_per_interval)

    @pytest.mark.asyncio
    async def test_update_when_not_ready(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        updater.update_in = 3
        self.mock_service.update = AsyncMock()
        mock_mutex = MagicMock()
        mock_mutex.acquire = MagicMock()
        mock_mutex.release = MagicMock()

        await updater.update(mock_mutex)

        self.mock_service.update.assert_not_awaited()
        self.mock_device.callback_function.assert_not_called()
        mock_mutex.acquire.assert_not_called()
        mock_mutex.release.assert_not_called()
        assert updater.update_in == 2  # update_in reduced by 1

    @pytest.mark.asyncio
    async def test_update_exception_handling(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        updater.update_in = 0
        self.mock_service.update = AsyncMock(side_effect=Exception("Test Exception"))
        mock_mutex = MagicMock()
        mock_mutex.acquire = MagicMock()
        mock_mutex.release = MagicMock()

        await updater.update(mock_mutex)

        self.mock_service.update.assert_awaited_once_with(self.mock_device)
        self.mock_device.callback_function.assert_not_called()
        mock_mutex.acquire.assert_called_once()
        mock_mutex.release.assert_called_once()
        assert updater.update_in == 60  # Still resets update_in

    def test_tick_tock(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        updater.update_in = 5
        updater.tick_tock()
        assert updater.update_in == 4

        updater.update_in = 0
        updater.tick_tock()
        assert updater.update_in == 0  # Should not go below 0

    def test_delay(self):
        updater = DeviceUpdater(self.mock_service, self.mock_device, 60)
        updater.updates_per_interval = 5
        updater.delay()
        assert updater.updates_per_interval == 4

        updater.updates_per_interval = 1
        updater.delay()
        assert updater.updates_per_interval == 1  # Should not go below 1


class TestUpdateManager:
    def setup_method(self):
        # Reset the class-level attributes before each test
        UpdateManager.updaters = []
        UpdateManager.removed_updaters = []
        self.update_manager = UpdateManager()
        # For logging assertions
        self.caplog = logging.getLogger('wyzeapy.services.update_manager')
        self.caplog.setLevel(logging.DEBUG)

    def test_check_if_removed(self):
        mock_updater1 = MagicMock()
        mock_updater2 = MagicMock()
        self.update_manager.removed_updaters.append(mock_updater1)

        assert self.update_manager.check_if_removed(mock_updater1) is True
        assert self.update_manager.check_if_removed(mock_updater2) is False

    @patch('asyncio.sleep', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_update_next_no_updaters(self, mock_sleep, caplog):
        with caplog.at_level(logging.DEBUG, logger='wyzeapy.services.update_manager'):
            await self.update_manager.update_next()
            assert "No devices to update in queue" in caplog.text
        mock_sleep.assert_not_awaited()

    def test_filled_slots(self):
        updater1 = DeviceUpdater(MagicMock(), MagicMock(), 60)  # updates_per_interval = 5
        updater2 = DeviceUpdater(MagicMock(), MagicMock(), 150)  # updates_per_interval = 2
        self.update_manager.updaters.extend([updater1, updater2])
        assert self.update_manager.filled_slots() == 7

    def test_decrease_updates_per_interval(self):
        updater1 = DeviceUpdater(MagicMock(), MagicMock(), 60)  # updates_per_interval = 5
        updater2 = DeviceUpdater(MagicMock(), MagicMock(), 150)  # updates_per_interval = 2
        self.update_manager.updaters.extend([updater1, updater2])

        self.update_manager.decrease_updates_per_interval()
        assert updater1.updates_per_interval == 4
        assert updater2.updates_per_interval == 1

    def test_tick_tock_manager(self):
        updater1 = DeviceUpdater(MagicMock(), MagicMock(), 60)
        updater1.update_in = 5
        updater2 = DeviceUpdater(MagicMock(), MagicMock(), 150)
        updater2.update_in = 2
        self.update_manager.updaters.extend([updater1, updater2])

        self.update_manager.tick_tock()
        assert updater1.update_in == 4
        assert updater2.update_in == 1

    def test_add_updater_success(self):
        updater = DeviceUpdater(MagicMock(), MagicMock(), 60)  # updates_per_interval = 5
        self.update_manager.add_updater(updater)
        assert updater in self.update_manager.updaters
        assert self.update_manager.filled_slots() == 5

    def test_add_updater_exceeds_max_slots(self):
        # Directly set updaters to exceed MAX_SLOTS
        UpdateManager.updaters = [MagicMock()] * (MAX_SLOTS + 1)

        new_updater = DeviceUpdater(MagicMock(), MagicMock(), 1)  # updates_per_interval = 300

        with pytest.raises(Exception) as exc_info:
            self.update_manager.add_updater(new_updater)
        assert "No more devices can be updated within the rate limit" in str(exc_info.value)

    def test_add_updater_reduces_frequency(self):
        # Add updaters that will cause overflow, forcing frequency reduction
        updater1 = DeviceUpdater(MagicMock(), MagicMock(), 1)  # 300 updates/interval
        updater2 = DeviceUpdater(MagicMock(), MagicMock(), 1)  # 300 updates/interval
        updater3 = DeviceUpdater(MagicMock(), MagicMock(), 1)  # 300 updates/interval

        # Set MAX_SLOTS to a small number for easier testing of overflow
        with patch('wyzeapy.services.update_manager.MAX_SLOTS', 500):
            self.update_manager.add_updater(updater1)
            self.update_manager.add_updater(updater2)
            self.update_manager.add_updater(updater3)

            # Check that updates_per_interval has been reduced for existing updaters
            assert updater1.updates_per_interval < 300
            assert updater2.updates_per_interval < 300
            assert updater3.updates_per_interval < 300

    def test_del_updater(self, caplog):
        updater = DeviceUpdater(MagicMock(), MagicMock(), 60)
        self.update_manager.updaters.append(updater)
        assert updater in self.update_manager.updaters

        with caplog.at_level(logging.DEBUG, logger='wyzeapy.services.update_manager'):
            self.update_manager.del_updater(updater)
            assert "Removing device from update queue" in caplog.text

