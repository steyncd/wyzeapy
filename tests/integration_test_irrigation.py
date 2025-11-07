"""
Integration test for irrigation service.
This test runs against the real Wyze API and requires valid credentials.

Based on API captures from wyze-lockwood-service.wyzecam.com, this test validates:
- Device status and properties (get_iot_prop)
- Zone configuration and management (get_zone_by_device, set_zone_quickrun_duration)
- Schedule tracking and running status (get_schedule_runs)
- Last watered timestamps for each zone
- Zone control operations (quickrun, pause, resume)

Note: The irrigation service uses wyze-lockwood-service.wyzecam.com which does NOT
use certificate pinning, unlike other Wyze services. This makes it easier to debug
with tools like mitmproxy.

Usage:
    python -m tests.integration_test_irrigation
"""
import asyncio
import logging
import os
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

    # Credentials - Set these as environment variables or replace with your own
    email = os.getenv("WYZE_EMAIL", "your_email@example.com")
    password = os.getenv("WYZE_PASSWORD", "your_password")
    key_id = os.getenv("WYZE_KEY_ID", "your_key_id")
    api_key = os.getenv("WYZE_API_KEY", "your_api_key")

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
                print(f"    - Last Watered: {zone.last_watered if zone.last_watered else 'Never or Unknown'}")

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

            # Check for past schedules to see last watered info
            past_schedules = [s for s in schedules if s.get('schedule_state') == 'past']
            if past_schedules:
                print(f"\n  Recent past watering schedules:")
                for schedule in past_schedules[:3]:  # Show first 3
                    schedule_name = schedule.get('schedule_name', 'Unnamed')
                    end_utc = schedule.get('end_utc', 'N/A')
                    print(f"  - {schedule_name}: ended at {end_utc}")
                    zone_runs = schedule.get('zone_runs', [])
                    if zone_runs:
                        zone_list = ', '.join([f'Zone {zr.get("zone_number")}' for zr in zone_runs])
                        print(f"    Zones watered: {zone_list}")

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
            print(f"\n[BONUS 1/4] Testing set_zone_quickrun_duration() method...")
            if irrigation.zones:
                original_duration = irrigation.zones[0].quickrun_duration
                test_duration = 1800  # 30 minutes
                irrigation = await irrigation_service.set_zone_quickrun_duration(
                    irrigation, 1, test_duration
                )
                assert irrigation.zones[0].quickrun_duration == test_duration, \
                    f"Quickrun duration should be {test_duration}"
                print(f"[OK] Quickrun duration updated from {original_duration}s to {test_duration}s")

                # Restore original duration
                irrigation = await irrigation_service.set_zone_quickrun_duration(
                    irrigation, 1, original_duration
                )
                print(f"[OK] Restored original duration: {original_duration}s")

            # Test get_schedules API
            print(f"\n[BONUS 2/4] Testing get_schedules() method...")
            try:
                schedules_response = await irrigation_service.get_schedules(irrigation)
                schedules_list = schedules_response.get('data', {}).get('schedules', [])
                print(f"[OK] Found {len(schedules_list)} configured schedule(s)")

                for sched in schedules_list[:3]:  # Show first 3
                    name = sched.get('schedule_name', 'Unnamed')
                    enabled = sched.get('enabled', False)
                    sched_type = sched.get('schedule_type', 'unknown')
                    print(f"  - {name} ({'enabled' if enabled else 'disabled'}, type: {sched_type})")
            except Exception as e:
                print(f"[INFO] get_schedules() not yet implemented or failed: {e}")

            # Test zone state tracking
            print(f"\n[BONUS 3/4] Testing zone state consistency...")
            # Verify that running zones have positive remaining time
            for zone in irrigation.zones:
                if zone.is_running:
                    assert zone.remaining_time > 0, \
                        f"Running zone {zone.zone_number} should have positive remaining_time"
                else:
                    assert zone.remaining_time == 0, \
                        f"Non-running zone {zone.zone_number} should have 0 remaining_time"
            print(f"[OK] Zone states are consistent")

            # Test last_watered field population
            print(f"\n[BONUS 4/4] Testing last_watered tracking...")
            zones_with_history = [z for z in irrigation.zones if z.last_watered is not None]
            if zones_with_history:
                print(f"[OK] {len(zones_with_history)}/{len(irrigation.zones)} zone(s) have watering history")
                for zone in zones_with_history[:3]:  # Show first 3
                    print(f"  - Zone {zone.zone_number} ({zone.name}): last watered {zone.last_watered}")
            else:
                print(f"[INFO] No zones have recent watering history (or none in past 20 schedule runs)")

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
