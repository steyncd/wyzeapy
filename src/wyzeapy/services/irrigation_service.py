import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from .base_service import BaseService
from ..types import Device, IrrigationProps, DeviceTypes

_LOGGER = logging.getLogger(__name__)


class CropType(Enum):
    COOL_SEASON_GRASS = "cool_season_grass"
    WARM_SEASON_GRASS = "warm_season_grass"
    SHRUBS = "shrubs"
    TREES = "trees"
    ANNUALS = "annuals"
    PERENNIALS = "perennials"
    XERISCAPE = "xeriscape"
    GARDEN = "garden"


class ExposureType(Enum):
    LOTS_OF_SUN = "lots_of_sun"
    SOME_SHADE = "some_shade"


class NozzleType(Enum):
    FIXED_SPRAY_HEAD = "fixed_spray_head"
    ROTOR_HEAD = "rotor_head"
    ROTARY_NOZZLE = "rotary_nozzle"
    MISTER = "mister"
    BUBBLER = "bubbler"
    EMITTER = "emitter"
    DRIP_LINE = "drip_line"


class SlopeType(Enum):
    FLAT = "flat"
    SLIGHT = "slight"
    MODERATE = "moderate"
    STEEP = "steep"


class SoilType(Enum):
    CLAY_LOAM = 'clay_loam'
    CLAY = 'clay'
    SILTY_CLAY = 'silty_clay'
    LOAM = 'loam'
    SANDY_LOAM = 'sandy_loam'
    LOAMY_SAND = 'loamy_sand'
    SAND = 'sand'


class Zone:
    """Represents a single irrigation zone."""
    def __init__(self, dictionary: Dict[Any, Any]):
        self.zone_number: int = dictionary.get('zone_number', 1)
        self.name: str = dictionary.get('name', 'Zone 1')
        self.enabled: bool = dictionary.get('enabled', True)
        self.zone_id: str = dictionary.get('zone_id', 'zone_id')
        self.smart_duration: int = dictionary.get('smart_duration', 600)

        # this quickrun duration is used only for running a zone manually
        # the wyze api has no such value, but takes a duration as part of the api call
        # the default value grabs the wyze smart_duration but all further updates
        # are managed through the home assistant state
        self.quickrun_duration: int = dictionary.get('smart_duration', 600)

        # Running status - updated by get_schedule_runs()
        self.is_running: bool = False
        self.remaining_time: int = 0  # seconds remaining

        # Last watered timestamp - updated by get_schedule_runs()
        self.last_watered: str | None = None  # ISO format UTC timestamp when zone last finished watering

class Irrigation(Device):
    def __init__(self, dictionary: Dict[Any, Any]):
        super().__init__(dictionary)

        # the below comes from the get_iot_prop call
        self.RSSI: int = 0
        self.IP: str = "192.168.1.100"
        self.sn: str = "SN123456789"
        self.available: bool = False
        self.ssid: str = "ssid"
        # the below comes from the device_info call
        self.zones: List[Zone] = []

        # Schedule information - updated by get_schedule_runs()
        self.next_scheduled_run: str | None = None  # ISO format UTC timestamp of next scheduled run
        self.last_run_end_time: str | None = None  # ISO format UTC timestamp when last run completed
        self.current_running_zone: str | None = None  # name of the zone currently watering, else None
        self.last_run_duration: int = 0  # duration of the most recent completed run, in seconds
        self.active_schedules_count: int = 0  # number of enabled configured schedules

        # Smart-skip settings - updated by get_device_info() (weather intelligence)
        # These reflect whether the device is configured to skip watering for each condition.
        self.skip_rain: bool = False
        self.skip_wind: bool = False
        self.skip_low_temp: bool = False  # freeze protection
        self.skip_saturation: bool = False


class IrrigationService(BaseService):
    async def update(self, irrigation: Irrigation) -> Irrigation:
        """Update the irrigation device with latest data from Wyze API."""
        # Get IoT properties
        properties = (await self.get_iot_prop(irrigation))['data']['props']

        # Update device properties
        irrigation.RSSI = properties.get('RSSI', -65)
        irrigation.IP = properties.get('IP', '192.168.1.100')
        irrigation.sn = properties.get('sn', 'SN123456789')
        irrigation.ssid = properties.get('ssid', 'ssid')
        irrigation.available = (properties.get(IrrigationProps.IOT_STATE.value) == 'connected')

        # Get zones
        zones = (await self.get_zone_by_device(irrigation))['data']['zones']

        # Update zones
        irrigation.zones = []
        for zone in zones:
            irrigation.zones.append(Zone(zone))

        # Get running status from schedule_runs API
        try:
            await self._update_running_status(irrigation)
        except Exception as e:
            _LOGGER.warning(f"Failed to update running status: {e}")

        # Get smart-skip settings (rain/wind/freeze/saturation). Optional - never fatal.
        try:
            await self._update_device_settings(irrigation)
        except Exception as e:
            _LOGGER.debug(f"Failed to update device settings: {e}")

        # Get count of enabled configured schedules. Optional - never fatal.
        try:
            await self._update_active_schedules(irrigation)
        except Exception as e:
            _LOGGER.debug(f"Failed to update active schedules: {e}")

        return irrigation
    async def update_device_props(self, irrigation: Irrigation) -> Irrigation:
        """Update the irrigation device with latest data from Wyze API."""
        # Get IoT properties
        properties = (await self.get_iot_prop(irrigation))['data']['props']
        # Update device properties
        irrigation.RSSI = properties.get('RSSI')
        irrigation.IP = properties.get('IP')
        irrigation.sn = properties.get('sn')
        irrigation.ssid = properties.get('ssid')
        irrigation.available = (properties.get(IrrigationProps.IOT_STATE.value) == 'connected')

        return irrigation

    async def get_irrigations(self) -> List[Irrigation]:
        if self._devices is None:
            self._devices = await self.get_object_list()

        irrigations = [device for device in self._devices if device.type == DeviceTypes.IRRIGATION and "BS_WK1" in device.product_model]

        return [Irrigation(irrigation.raw_dict) for irrigation in irrigations]

    async def start_zone(self, irrigation: Device, zone_number: int, quickrun_duration: int) -> Dict[Any, Any]:
        """Start a zone with the specified duration.
        
        Args:
            irrigation: The irrigation device
            zone_number: The zone number to start
            quickrun_duration: Duration in seconds to run the zone
            
        Returns:
            Dict containing the API response
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/quickrun"
        return await self._start_zone(url, irrigation, zone_number, quickrun_duration)

    async def stop_running_schedule(self, device: Device) -> Dict[Any, Any]:
        """Stop any currently running irrigation schedule.

        Args:
            device: The irrigation device

        Returns:
            Dict containing the API response
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/runningschedule"
        action = "STOP"
        return await self._stop_running_schedule(url, device, action)

    async def pause_irrigation(self, device: Device) -> Dict[Any, Any]:
        """Pause currently running irrigation.

        Args:
            device: The irrigation device

        Returns:
            Dict containing the API response
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/pause"
        return await self._pause_irrigation(url, device)

    async def resume_irrigation(self, device: Device) -> Dict[Any, Any]:
        """Resume paused irrigation.

        Args:
            device: The irrigation device

        Returns:
            Dict containing the API response
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/resume"
        return await self._resume_irrigation(url, device)

    async def set_zone_quickrun_duration(self, irrigation: Irrigation, zone_number: int, duration: int) -> Irrigation:
        """Set the quickrun duration for a specific zone.
        
        Args:
            irrigation: The irrigation device
            zone_number: The zone number to configure
            duration: Duration in seconds for quickrun
        """
        for zone in irrigation.zones:
            if zone.zone_number == zone_number:
                zone.quickrun_duration = duration
                break
        return irrigation

    # Private implementation methods
    async def get_iot_prop(self, device: Device) -> Dict[Any, Any]:
        """Get IoT properties for a device."""
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/get_iot_prop"
        keys = 'zone_state,iot_state,iot_state_update_time,app_version,RSSI,' \
            'wifi_mac,sn,device_model,ssid,IP'
        return await self._get_iot_prop(url, device, keys)

    async def get_device_info(self, device: Device) -> Dict[Any, Any]:
        """Get device info from Wyze API."""
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/device_info"
        keys = 'wiring,sensor,enable_schedules,notification_enable,notification_watering_begins,' \
            'notification_watering_ends,notification_watering_is_skipped,skip_low_temp,skip_wind,' \
            'skip_rain,skip_saturation'
        return await self._irrigation_device_info(url, device, keys)

    async def get_zone_by_device(self, device: Device) -> List[Dict[Any, Any]]:
        """Get zones for a device."""
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/zone"
        return await self._get_zone_by_device(url, device)

    async def get_schedule_runs(self, device: Device, limit: int = 10) -> Dict[Any, Any]:
        """Get schedule runs (past, current, and upcoming).

        Args:
            device: The irrigation device
            limit: Number of schedule runs to return (default: 10)

        Returns:
            Dict containing schedules with state 'past', 'running', or 'upcoming'
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/schedule_runs"
        return await self._get_schedule_runs(url, device, limit)

    async def get_schedules(self, device: Device) -> Dict[Any, Any]:
        """Get configured schedules for the device.

        Args:
            device: The irrigation device

        Returns:
            Dict containing configured schedules (not run history, but schedule definitions)
        """
        url = "https://wyze-lockwood-service.wyzecam.com/plugin/irrigation/schedule"
        return await self._get_schedules(url, device)

    async def _update_running_status(self, irrigation: Irrigation) -> None:
        """Update running status for all zones by checking schedule_runs API.

        This method:
        1. Calls schedule_runs API to get current running schedules
        2. Updates is_running and remaining_time for each zone
        3. Updates last_watered timestamp from most recent past schedule
        """
        # Reset all zones to not running
        for zone in irrigation.zones:
            zone.is_running = False
            zone.remaining_time = 0
        irrigation.current_running_zone = None

        # Get schedule runs (increase limit to get more past runs)
        try:
            response = await self.get_schedule_runs(irrigation, limit=20)
            schedules = response.get('data', {}).get('schedules', [])

            # Find running schedule
            now = datetime.now(timezone.utc)
            for schedule in schedules:
                if schedule.get('schedule_state') == 'running':
                    # Parse end time
                    end_utc_str = schedule.get('end_utc')
                    if end_utc_str:
                        # Remove 'Z' suffix and parse
                        end_time = datetime.fromisoformat(end_utc_str.replace('Z', '+00:00'))

                        # Check zone_runs to find which zones are running
                        zone_runs = schedule.get('zone_runs', [])
                        for zone_run in zone_runs:
                            zone_number = zone_run.get('zone_number')
                            zone_end_utc = zone_run.get('end_utc')

                            if zone_end_utc:
                                zone_end_time = datetime.fromisoformat(zone_end_utc.replace('Z', '+00:00'))
                                zone_remaining = int((zone_end_time - now).total_seconds())

                                # Find matching zone and update status
                                for zone in irrigation.zones:
                                    if zone.zone_number == zone_number:
                                        # Only mark as running if end time is in the future
                                        if zone_remaining > 0:
                                            zone.is_running = True
                                            zone.remaining_time = zone_remaining
                                            irrigation.current_running_zone = zone.name
                                        break

            # Update last_watered timestamps from past schedules
            # Find the most recent completed watering for each zone
            past_schedules = [s for s in schedules if s.get('schedule_state') == 'past']
            for zone in irrigation.zones:
                # Look through past schedules for this zone (most recent first)
                for schedule in past_schedules:
                    zone_runs = schedule.get('zone_runs', [])
                    for zone_run in zone_runs:
                        if zone_run.get('zone_number') == zone.zone_number:
                            # Found a past run for this zone, use its end time
                            zone_end_utc = zone_run.get('end_utc')
                            if zone_end_utc:
                                zone.last_watered = zone_end_utc
                                break  # Use the first (most recent) match
                    if zone.last_watered:
                        break  # Stop searching once we found the most recent

            # Update device-level schedule information
            upcoming_schedules = [s for s in schedules if s.get('schedule_state') == 'upcoming']
            if upcoming_schedules:
                # Get the first (next) upcoming schedule
                irrigation.next_scheduled_run = upcoming_schedules[0].get('start_utc')

            if past_schedules:
                # Get the most recent past schedule end time
                irrigation.last_run_end_time = past_schedules[0].get('end_utc')
                # Derive the duration of the most recent completed run (seconds).
                irrigation.last_run_duration = self._schedule_duration_seconds(past_schedules[0])

        except Exception as e:
            _LOGGER.debug(f"Could not update running status: {e}")
            # Silently fail - running status is optional

    @staticmethod
    def _schedule_duration_seconds(schedule: Dict[Any, Any]) -> int:
        """Return the total run duration of a schedule in seconds.

        Prefers the sum of each zone_run's reported ``duration``; falls back to
        ``end_utc - start_utc`` when per-zone durations are absent.
        """
        zone_runs = schedule.get('zone_runs', []) or []
        total = 0
        for zone_run in zone_runs:
            dur = zone_run.get('duration')
            if isinstance(dur, (int, float)):
                total += int(dur)
        if total > 0:
            return total

        start_utc = schedule.get('start_utc')
        end_utc = schedule.get('end_utc')
        if start_utc and end_utc:
            try:
                start = datetime.fromisoformat(start_utc.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_utc.replace('Z', '+00:00'))
                return max(0, int((end - start).total_seconds()))
            except (ValueError, AttributeError):
                pass
        return 0

    async def _update_device_settings(self, irrigation: Irrigation) -> None:
        """Populate smart-skip settings (rain/wind/freeze/saturation) from device_info.

        The Wyze irrigation ``device_info`` endpoint returns the configured
        weather-intelligence skip toggles. The exact nesting of the response is
        parsed defensively across the common shapes (``data.settings`` /
        ``data.props`` / ``data``) so it survives minor API differences.
        """
        response = await self.get_device_info(irrigation)
        data = response.get('data', {}) if isinstance(response, dict) else {}
        # Flatten the plausible containers into one lookup dict.
        settings: Dict[str, Any] = {}
        for container in (data, data.get('settings'), data.get('props'), data.get('device_info')):
            if isinstance(container, dict):
                settings.update(container)

        def _as_bool(value: Any) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                return value.strip().lower() in ('1', 'true', 'yes', 'on', 'enabled')
            return False

        if 'skip_rain' in settings:
            irrigation.skip_rain = _as_bool(settings.get('skip_rain'))
        if 'skip_wind' in settings:
            irrigation.skip_wind = _as_bool(settings.get('skip_wind'))
        if 'skip_low_temp' in settings:
            irrigation.skip_low_temp = _as_bool(settings.get('skip_low_temp'))
        if 'skip_saturation' in settings:
            irrigation.skip_saturation = _as_bool(settings.get('skip_saturation'))

        _LOGGER.debug("Irrigation device_info settings keys: %s", list(settings.keys()))

    async def _update_active_schedules(self, irrigation: Irrigation) -> None:
        """Populate the count of enabled configured schedules from get_schedules."""
        response = await self.get_schedules(irrigation)
        data = response.get('data', {}) if isinstance(response, dict) else {}
        schedules = data.get('schedules', []) or []
        # Count schedules that are enabled (treat missing 'enabled' as enabled).
        irrigation.active_schedules_count = sum(
            1 for s in schedules if s.get('enabled', True)
        )
