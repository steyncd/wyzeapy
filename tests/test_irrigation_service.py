import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from wyzeapy.services.irrigation_service import IrrigationService, Irrigation, Zone
from wyzeapy.types import DeviceTypes, IrrigationProps


class TestIrrigationService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        mock_auth_lib = MagicMock()
        self.irrigation_service = IrrigationService(auth_lib=mock_auth_lib)
        self.irrigation_service.get_iot_prop = AsyncMock()
        self.irrigation_service.get_zone_by_device = AsyncMock()
        self.irrigation_service.get_schedule_runs = AsyncMock()

    async def test_update_irrigation_basic_properties(self):
        mock_irrigation = Irrigation({
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "mac": "TEST123",
            "raw_dict": {},
            "product_type": DeviceTypes.IRRIGATION.value,
        })

        # Mock the IoT property response
        self.irrigation_service.get_iot_prop.return_value = {
            'data': {
                'props': {
                    'RSSI': -45,
                    'IP': '192.168.1.50',
                    'sn': 'SN987654321',
                    'ssid': 'MyNetwork',
                    IrrigationProps.IOT_STATE.value: 'connected'
                }
            }
        }

        # Mock the zones response
        self.irrigation_service.get_zone_by_device.return_value = {
            'data': {
                'zones': [
                    {
                        'zone_number': 1,
                        'name': 'Front Yard',
                        'enabled': True,
                        'zone_id': 'zone_1',
                        'smart_duration': 900
                    },
                    {
                        'zone_number': 2,
                        'name': 'Back Yard',
                        'enabled': True,
                        'zone_id': 'zone_2',
                        'smart_duration': 1200
                    }
                ]
            }
        }

        # Mock schedule runs response (no running schedules)
        self.irrigation_service.get_schedule_runs.return_value = {
            'data': {
                'schedules': []
            }
        }

        updated_irrigation = await self.irrigation_service.update(mock_irrigation)

        self.assertEqual(updated_irrigation.RSSI, -45)
        self.assertEqual(updated_irrigation.IP, '192.168.1.50')
        self.assertEqual(updated_irrigation.sn, 'SN987654321')
        self.assertEqual(updated_irrigation.ssid, 'MyNetwork')
        self.assertTrue(updated_irrigation.available)
        self.assertEqual(len(updated_irrigation.zones), 2)
        self.assertEqual(updated_irrigation.zones[0].name, 'Front Yard')
        self.assertEqual(updated_irrigation.zones[1].name, 'Back Yard')

    async def test_update_irrigation_with_running_zone(self):
        mock_irrigation = Irrigation({
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "mac": "TEST456",
            "raw_dict": {},
            "product_type": DeviceTypes.IRRIGATION.value,
        })

        # Mock the IoT property response
        self.irrigation_service.get_iot_prop.return_value = {
            'data': {
                'props': {
                    'RSSI': -50,
                    'IP': '192.168.1.51',
                    'sn': 'SN123456789',
                    'ssid': 'TestNetwork',
                    IrrigationProps.IOT_STATE.value: 'connected'
                }
            }
        }

        # Mock the zones response
        self.irrigation_service.get_zone_by_device.return_value = {
            'data': {
                'zones': [
                    {
                        'zone_number': 1,
                        'name': 'Zone 1',
                        'enabled': True,
                        'zone_id': 'zone_1',
                        'smart_duration': 600
                    },
                    {
                        'zone_number': 2,
                        'name': 'Zone 2',
                        'enabled': True,
                        'zone_id': 'zone_2',
                        'smart_duration': 600
                    }
                ]
            }
        }

        # Mock schedule runs response with a running schedule
        now = datetime.now(timezone.utc)
        future_time = now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')

        # Calculate a time 5 minutes in the future
        from datetime import timedelta
        end_time = (now + timedelta(minutes=5)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

        self.irrigation_service.get_schedule_runs.return_value = {
            'data': {
                'schedules': [
                    {
                        'schedule_state': 'running',
                        'schedule_name': 'Morning Watering',
                        'start_utc': future_time,
                        'end_utc': end_time,
                        'zone_runs': [
                            {
                                'zone_number': 1,
                                'start_utc': future_time,
                                'end_utc': end_time,
                                'duration': 300
                            }
                        ]
                    }
                ]
            }
        }

        updated_irrigation = await self.irrigation_service.update(mock_irrigation)

        # Check that zone 1 is marked as running
        self.assertTrue(updated_irrigation.zones[0].is_running)
        self.assertGreater(updated_irrigation.zones[0].remaining_time, 0)

        # Check that zone 2 is not running
        self.assertFalse(updated_irrigation.zones[1].is_running)
        self.assertEqual(updated_irrigation.zones[1].remaining_time, 0)

    async def test_get_irrigations(self):
        mock_device = MagicMock()
        mock_device.type = DeviceTypes.IRRIGATION
        mock_device.product_model = "BS_WK1"
        mock_device.raw_dict = {
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "product_type": DeviceTypes.IRRIGATION.value,
        }

        self.irrigation_service.get_object_list = AsyncMock(return_value=[mock_device])

        irrigations = await self.irrigation_service.get_irrigations()

        self.assertEqual(len(irrigations), 1)
        self.assertIsInstance(irrigations[0], Irrigation)
        self.irrigation_service.get_object_list.assert_awaited_once()

    async def test_set_zone_quickrun_duration(self):
        mock_irrigation = Irrigation({
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "mac": "TEST789",
            "raw_dict": {},
            "product_type": DeviceTypes.IRRIGATION.value,
        })

        # Add zones
        mock_irrigation.zones = [
            Zone({'zone_number': 1, 'name': 'Zone 1', 'enabled': True, 'zone_id': 'zone_1', 'smart_duration': 600}),
            Zone({'zone_number': 2, 'name': 'Zone 2', 'enabled': True, 'zone_id': 'zone_2', 'smart_duration': 600})
        ]

        # Set quickrun duration for zone 1
        updated_irrigation = await self.irrigation_service.set_zone_quickrun_duration(
            mock_irrigation, 1, 1800
        )

        self.assertEqual(updated_irrigation.zones[0].quickrun_duration, 1800)
        self.assertEqual(updated_irrigation.zones[1].quickrun_duration, 600)  # Unchanged

    async def test_zone_initialization(self):
        zone_data = {
            'zone_number': 3,
            'name': 'Garden',
            'enabled': False,
            'zone_id': 'zone_3',
            'smart_duration': 1200
        }

        zone = Zone(zone_data)

        self.assertEqual(zone.zone_number, 3)
        self.assertEqual(zone.name, 'Garden')
        self.assertFalse(zone.enabled)
        self.assertEqual(zone.zone_id, 'zone_3')
        self.assertEqual(zone.smart_duration, 1200)
        self.assertEqual(zone.quickrun_duration, 1200)  # Should default to smart_duration
        self.assertFalse(zone.is_running)
        self.assertEqual(zone.remaining_time, 0)
        self.assertIsNone(zone.last_watered)

    async def test_update_irrigation_with_last_watered(self):
        mock_irrigation = Irrigation({
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "mac": "TEST789",
            "raw_dict": {},
            "product_type": DeviceTypes.IRRIGATION.value,
        })

        # Mock the IoT property response
        self.irrigation_service.get_iot_prop.return_value = {
            'data': {
                'props': {
                    'RSSI': -50,
                    'IP': '192.168.1.52',
                    'sn': 'SN789',
                    'ssid': 'TestNetwork',
                    IrrigationProps.IOT_STATE.value: 'connected'
                }
            }
        }

        # Mock the zones response
        self.irrigation_service.get_zone_by_device.return_value = {
            'data': {
                'zones': [
                    {
                        'zone_number': 1,
                        'name': 'Zone 1',
                        'enabled': True,
                        'zone_id': 'zone_1',
                        'smart_duration': 600
                    },
                    {
                        'zone_number': 2,
                        'name': 'Zone 2',
                        'enabled': True,
                        'zone_id': 'zone_2',
                        'smart_duration': 600
                    }
                ]
            }
        }

        # Mock schedule runs response with past schedules
        self.irrigation_service.get_schedule_runs.return_value = {
            'data': {
                'schedules': [
                    {
                        'schedule_state': 'past',
                        'schedule_name': 'Morning Watering',
                        'start_utc': '2025-11-07T08:00:00Z',
                        'end_utc': '2025-11-07T08:20:00Z',
                        'zone_runs': [
                            {
                                'zone_number': 1,
                                'start_utc': '2025-11-07T08:00:00Z',
                                'end_utc': '2025-11-07T08:10:00Z',
                                'duration': 600
                            },
                            {
                                'zone_number': 2,
                                'start_utc': '2025-11-07T08:10:00Z',
                                'end_utc': '2025-11-07T08:20:00Z',
                                'duration': 600
                            }
                        ]
                    }
                ]
            }
        }

        updated_irrigation = await self.irrigation_service.update(mock_irrigation)

        # Check that last_watered is set for both zones
        self.assertEqual(updated_irrigation.zones[0].last_watered, '2025-11-07T08:10:00Z')
        self.assertEqual(updated_irrigation.zones[1].last_watered, '2025-11-07T08:20:00Z')

    async def test_update_device_props(self):
        mock_irrigation = Irrigation({
            "device_type": "Irrigation",
            "product_model": "BS_WK1",
            "mac": "TEST999",
            "raw_dict": {},
            "product_type": DeviceTypes.IRRIGATION.value,
        })

        # Mock the IoT property response
        self.irrigation_service.get_iot_prop.return_value = {
            'data': {
                'props': {
                    'RSSI': -55,
                    'IP': '192.168.1.99',
                    'sn': 'SNTEST999',
                    'ssid': 'TestSSID',
                    IrrigationProps.IOT_STATE.value: 'disconnected'
                }
            }
        }

        updated_irrigation = await self.irrigation_service.update_device_props(mock_irrigation)

        self.assertEqual(updated_irrigation.RSSI, -55)
        self.assertEqual(updated_irrigation.IP, '192.168.1.99')
        self.assertEqual(updated_irrigation.sn, 'SNTEST999')
        self.assertEqual(updated_irrigation.ssid, 'TestSSID')
        self.assertFalse(updated_irrigation.available)  # disconnected
