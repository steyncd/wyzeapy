import pytest
from unittest.mock import AsyncMock, MagicMock
from wyzeapy.services.hms_service import HMSService, HMSMode
from wyzeapy.wyze_auth_lib import WyzeAuthLib


class TestHMSService:
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        self.mock_auth_lib = MagicMock(spec=WyzeAuthLib)
        self.hms_service = await HMSService.create(self.mock_auth_lib)
        self.hms_service._get_plan_binding_list_by_user = AsyncMock()
        self.hms_service._monitoring_profile_state_status = AsyncMock()
        self.hms_service._monitoring_profile_active = AsyncMock()
        self.hms_service._disable_reme_alarm = AsyncMock()

    @pytest.mark.asyncio
    async def test_update_changing_mode(self):
        self.hms_service._monitoring_profile_state_status.return_value = {'message': 'changing'}

        mode = await self.hms_service.update('test_hms_id')
        assert mode == HMSMode.CHANGING

    @pytest.mark.asyncio
    async def test_update_disarmed_mode(self):
        self.hms_service._monitoring_profile_state_status.return_value = {'message': 'disarm'}

        mode = await self.hms_service.update('test_hms_id')
        assert mode == HMSMode.DISARMED

    @pytest.mark.asyncio
    async def test_update_away_mode(self):
        self.hms_service._monitoring_profile_state_status.return_value = {'message': 'away'}

        mode = await self.hms_service.update('test_hms_id')
        assert mode == HMSMode.AWAY

    @pytest.mark.asyncio
    async def test_update_home_mode(self):
        self.hms_service._monitoring_profile_state_status.return_value = {'message': 'home'}

        mode = await self.hms_service.update('test_hms_id')
        assert mode == HMSMode.HOME

    @pytest.mark.asyncio
    async def test_set_mode_disarmed(self):
        self.hms_service._hms_id = 'test_hms_id'

        await self.hms_service.set_mode(HMSMode.DISARMED)

        self.hms_service._disable_reme_alarm.assert_awaited_with('test_hms_id')
        self.hms_service._monitoring_profile_active.assert_awaited_with('test_hms_id', 0, 0)

    @pytest.mark.asyncio
    async def test_set_mode_away(self):
        self.hms_service._hms_id = 'test_hms_id'

        await self.hms_service.set_mode(HMSMode.AWAY)

        self.hms_service._monitoring_profile_active.assert_awaited_with('test_hms_id', 0, 1)

    @pytest.mark.asyncio
    async def test_set_mode_home(self):
        self.hms_service._hms_id = 'test_hms_id'

        await self.hms_service.set_mode(HMSMode.HOME)

        self.hms_service._monitoring_profile_active.assert_awaited_with('test_hms_id', 1, 0)

    @pytest.mark.asyncio
    async def test_get_hms_id_with_existing_id(self):
        self.hms_service._hms_id = 'existing_hms_id'
        hms_id = await self.hms_service._get_hms_id()
        assert hms_id == 'existing_hms_id'

    @pytest.mark.asyncio
    async def test_get_hms_id_with_no_hms(self):
        self.hms_service._hms_id = None
        self.hms_service._get_plan_binding_list_by_user.return_value = {'data': []}

        hms_id = await self.hms_service._get_hms_id()
        assert hms_id is None

    @pytest.mark.asyncio
    async def test_get_hms_id_finds_id(self):
        self.hms_service._hms_id = None
        self.hms_service._get_plan_binding_list_by_user.return_value = {
            'data': [
                {
                    'deviceList': [
                        {'device_id': 'found_hms_id'}
                    ]
                }
            ]
        }

        hms_id = await self.hms_service._get_hms_id()
        assert hms_id == 'found_hms_id'
        assert self.hms_service._hms_id == 'found_hms_id' 