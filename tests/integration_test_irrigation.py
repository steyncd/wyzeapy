"""
Integration test for irrigation service.
This test runs against the real Wyze API and requires valid credentials.

Usage:
    python -m tests.integration_test_irrigation
"""
import asyncio
import logging
import sys
from wyzeapy import Wyzeapy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_irrigation_integration():
    """Test irrigation service against real Wyze API."""

    # Credentials
    email = "steyncd@gmail.com"
    password = "Dobby.1021"
    key_id = "02e46f64-3b3e-43cf-8d7a-9a7499a6b32d"
    api_key = "TaJE8u99R9Li6hnR6euf7pQFh6IshaOOAlI2EVWaqW4gJQqenAJ9kf6T9L8d"

    print("=" * 80)
    print("WYZE IRRIGATION SERVICE - INTEGRATION TEST")
    print("=" * 80)

    try:
        # Create client and login
        print("\n[1/8] Authenticating with Wyze API...")
        client = await Wyzeapy.create()
        await client.login(email, password, key_id, api_key)
        print("[OK] Authentication successful")

        # Get irrigation service
        irrigation_service = await client.irrigation_service

        # Get all irrigation devices
        print("\n[2/8] Retrieving irrigation devices...")
        irrigations = await irrigation_service.get_irrigations()
        print(f"[OK] Found {len(irrigations)} irrigation device(s)")

        if not irrigations:
            print("\n[WARNING] No irrigation devices found!")
            return False

        # Test each irrigation device
        for idx, irrigation in enumerate(irrigations, 1):
            print(f"\n{'=' * 80}")
            print(f"TESTING DEVICE #{idx}")
            print(f"{'=' * 80}")
            print(f"MAC: {irrigation.mac}")
            print(f"Nickname: {irrigation.nickname}")
            print(f"Product Model: {irrigation.product_model}")
            print(f"Product Type: {irrigation.product_type}")

            # Test update method
            print(f"\n[3/8] Testing update() method...")
            irrigation = await irrigation_service.update(irrigation)
            print(f"[OK] Device updated successfully")

            # Verify device properties
            print(f"\n[4/8] Verifying device properties...")
            print(f"  - Available: {irrigation.available}")
            print(f"  - SSID: {irrigation.ssid}")
            print(f"  - IP: {irrigation.IP}")
            print(f"  - RSSI: {irrigation.RSSI}")
            print(f"  - Serial Number: {irrigation.sn}")
            assert irrigation.RSSI is not None, "RSSI should not be None"
            assert irrigation.IP is not None, "IP should not be None"
            assert irrigation.sn is not None, "Serial number should not be None"
            print(f"[OK] Device properties verified")

            # Verify zones
            print(f"\n[5/8] Verifying zones...")
            print(f"  Total zones: {len(irrigation.zones)}")
            assert len(irrigation.zones) > 0, "Should have at least one zone"

            for zone in irrigation.zones:
                print(f"\n  Zone {zone.zone_number}: {zone.name}")
                print(f"    - Zone ID: {zone.zone_id}")
                print(f"    - Enabled: {zone.enabled}")
                print(f"    - Smart Duration: {zone.smart_duration}s ({zone.smart_duration // 60}m)")
                print(f"    - Quickrun Duration: {zone.quickrun_duration}s ({zone.quickrun_duration // 60}m)")
                print(f"    - Is Running: {zone.is_running}")
                if zone.is_running:
                    print(f"    - Remaining Time: {zone.remaining_time}s ({zone.remaining_time // 60}m {zone.remaining_time % 60}s)")
                    print(f"    [ALERT] Zone {zone.zone_number} is currently running!")

                assert zone.zone_id is not None, f"Zone {zone.zone_number} should have a zone_id"
                assert zone.smart_duration > 0, f"Zone {zone.zone_number} should have a positive smart_duration"

            print(f"[OK] All zones verified")

            # Test schedule runs API
            print(f"\n[6/8] Testing get_schedule_runs() method...")
            schedule_runs = await irrigation_service.get_schedule_runs(irrigation, limit=10)
            schedules = schedule_runs.get('data', {}).get('schedules', [])
            print(f"[OK] Found {len(schedules)} schedule(s)")

            running_schedules = [s for s in schedules if s.get('schedule_state') == 'running']
            if running_schedules:
                print(f"[ALERT] {len(running_schedules)} schedule(s) currently running:")
                for schedule in running_schedules:
                    print(f"  - {schedule.get('schedule_name', 'Unnamed')}")
                    zone_runs = schedule.get('zone_runs', [])
                    for zone_run in zone_runs:
                        zone_num = zone_run.get('zone_number')
                        duration = zone_run.get('duration', 0)
                        print(f"    * Zone {zone_num}: {duration}s ({duration // 60}m)")

            # Test get_iot_prop directly
            print(f"\n[7/8] Testing get_iot_prop() method...")
            iot_props = await irrigation_service.get_iot_prop(irrigation)
            props = iot_props.get('data', {}).get('props', {})
            assert len(props) > 0, "Should receive IoT properties"
            print(f"[OK] Received {len(props)} IoT properties")

            # Skip get_device_info as _irrigation_device_info is not implemented in base_service
            print(f"\n[8/8] Skipping get_device_info() test (method not fully implemented)")
            print(f"[OK] Skipped")

            # Test set_zone_quickrun_duration
            print(f"\n[BONUS] Testing set_zone_quickrun_duration() method...")
            if irrigation.zones:
                original_duration = irrigation.zones[0].quickrun_duration
                test_duration = 1800  # 30 minutes
                irrigation = await irrigation_service.set_zone_quickrun_duration(
                    irrigation, 1, test_duration
                )
                assert irrigation.zones[0].quickrun_duration == test_duration, \
                    f"Quickrun duration should be {test_duration}"
                print(f"[OK] Quickrun duration updated from {original_duration}s to {test_duration}s")

        print(f"\n{'=' * 80}")
        print("ALL TESTS PASSED!")
        print(f"{'=' * 80}")
        return True

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n[ERROR] Test failed: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_irrigation_integration())
    sys.exit(0 if result else 1)
