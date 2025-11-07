# Wyze Irrigation Service Implementation

## Overview

Complete implementation of the Wyze Irrigation (Sprinkler) service for the `wyzeapy` library. This implementation provides full control and monitoring of Wyze irrigation controllers through the Wyze API.

## Features Implemented

### ✓ Device Management
- **Device Discovery**: Retrieve all irrigation devices on the account
- **Device Status**: Real-time connection status, signal strength, IP address
- **Device Properties**: Serial number, firmware version, network info

### ✓ Zone Control
- **Zone Configuration**: Get all 6 zones with names, durations, and settings
- **Zone Status**: Track running zones with remaining time
- **Last Watered**: Historical timestamp of last watering for each zone
- **Quick Run**: Start zones manually with configurable duration
- **Pause/Resume**: Control running irrigation sessions
- **Stop**: Cancel active watering schedules

### ✓ Schedule Management
- **Schedule Configuration**: Get configured schedules (FIXED/SMART types)
- **Schedule Runs**: Track past, running, and upcoming irrigation schedules
- **Running Detection**: Real-time detection of active zones
- **Schedule History**: Access past watering events for analytics

### ✓ Configuration
- **Quickrun Duration**: Adjust per-zone manual run durations
- **Zone Settings**: Manage individual zone configurations

## Key Classes

### `Irrigation` (Device Model)
Located in: `src/wyzeapy/types.py`

Represents a Wyze irrigation controller with:
- Device properties (MAC, nickname, model, connection status)
- Network info (IP, RSSI, SSID)
- List of `Zone` objects

### `Zone` (Zone Model)
Located in: `src/wyzeapy/types.py`

Represents an individual sprinkler zone with:
- `zone_number`: Zone identifier (1-6)
- `zone_id`: Unique zone ID for API calls
- `name`: User-defined zone name
- `enabled`: Whether zone is active
- `smart_duration`: AI-optimized watering duration
- `quickrun_duration`: Manual run duration
- `is_running`: Real-time running status
- `remaining_time`: Seconds remaining (if running)
- `last_watered`: ISO 8601 UTC timestamp of last watering

### `IrrigationService`
Located in: `src/wyzeapy/services/irrigation_service.py`

Main service class providing:
- `get_irrigations()`: Get all irrigation devices
- `update(irrigation)`: Refresh device status and zones
- `get_iot_prop(irrigation)`: Get device properties
- `get_zone_by_device(irrigation)`: Get zone configurations
- `get_schedule_runs(irrigation, limit)`: Get schedule run history (past/running/upcoming)
- `get_schedules(irrigation)`: Get configured schedules (FIXED/SMART definitions)
- `set_zone_quickrun_duration(irrigation, zone, duration)`: Update zone duration
- `start_zone(irrigation, zone, duration)`: Start zone manually
- `pause_irrigation(irrigation)`: Pause running schedule
- `resume_irrigation(irrigation)`: Resume paused schedule
- `stop_running_schedule(irrigation)`: Stop active watering

## API Details

### Base URL
`https://wyze-lockwood-service.wyzecam.com`

**Important**: The irrigation service does NOT use certificate pinning, unlike other Wyze services. This makes it easier to debug and monitor.

### Key Endpoints

1. **GET /plugin/irrigation/get_iot_prop** - Device status ✅
2. **GET /plugin/irrigation/zone** - Zone configurations ✅
3. **GET /plugin/irrigation/schedule_runs** - Schedule run history ✅
4. **GET /plugin/irrigation/schedule** - Configured schedules ✅
5. **POST /plugin/irrigation/quickrun** - Start zone manually ✅
6. **POST /plugin/irrigation/pause** - Pause watering ✅
7. **POST /plugin/irrigation/resume** - Resume watering ✅
8. **POST /plugin/irrigation/runningschedule** (action: STOP) - Stop watering ✅

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for complete endpoint documentation.

## Running Zone Detection Algorithm

The service detects running zones by:

1. Calling `GET /plugin/irrigation/schedule_runs` with limit=20
2. Filtering for schedules with `schedule_state == "running"`
3. Iterating through `zone_runs` in running schedules
4. Calculating remaining time: `end_utc - current_time`
5. Setting `zone.is_running = True` and `zone.remaining_time = seconds`

## Last Watered Tracking Algorithm

The service populates `last_watered` by:

1. Calling `GET /plugin/irrigation/schedule_runs` with limit=20
2. Filtering for schedules with `schedule_state == "past"`
3. For each zone, finding the most recent past schedule
4. Extracting `end_utc` timestamp from the zone_run
5. Setting `zone.last_watered = end_utc` (ISO 8601 format)

## Testing

### Unit Tests
Located in: `tests/test_irrigation_service.py`

```bash
python -m unittest tests.test_irrigation_service
```

**Coverage**: 7 tests
- Device creation and initialization
- Zone parsing and management
- Running status updates
- Last watered tracking
- Property updates

### Integration Tests
Located in: `tests/integration_test_irrigation.py`

```bash
python -m tests.integration_test_irrigation
```

**Tests**:
1. Authentication
2. Device retrieval
3. Device updates
4. Property verification
5. Zone verification
6. Schedule runs API
7. IoT properties
8. Quickrun duration updates
9. Zone state consistency
10. Last watered tracking

**Results**: All tests passing ✓

## Usage Examples

### Basic Usage

```python
from wyzeapy import Wyzeapy

# Login
client = await Wyzeapy.create()
await client.login(email, password, key_id, api_key)

# Get irrigation service
irrigation_service = await client.irrigation_service

# Get all irrigation devices
irrigations = await irrigation_service.get_irrigations()

# Update device status
irrigation = await irrigation_service.update(irrigations[0])

# Check zones
for zone in irrigation.zones:
    print(f"Zone {zone.zone_number}: {zone.name}")
    print(f"  Running: {zone.is_running}")
    if zone.is_running:
        print(f"  Time remaining: {zone.remaining_time}s")
    print(f"  Last watered: {zone.last_watered}")
```

### Start Zone Manually

```python
# Start zone 1 with quickrun duration
await irrigation_service.quickrun(irrigation, 1)

# Or update duration first
irrigation = await irrigation_service.set_zone_quickrun_duration(
    irrigation, 1, 1800  # 30 minutes
)
await irrigation_service.quickrun(irrigation, 1)
```

### Control Running Zones

```python
# Pause
await irrigation_service.pause_irrigation(irrigation)

# Resume
await irrigation_service.resume_irrigation(irrigation)

# Stop
await irrigation_service.stop_irrigation(irrigation)
```

### Monitor Running Status

```python
while True:
    irrigation = await irrigation_service.update(irrigation)

    for zone in irrigation.zones:
        if zone.is_running:
            minutes = zone.remaining_time // 60
            seconds = zone.remaining_time % 60
            print(f"Zone {zone.zone_number} running: {minutes}m {seconds}s left")

    await asyncio.sleep(10)  # Poll every 10 seconds
```

## Home Assistant Integration

This implementation is designed for use in Home Assistant through the `wyzeapy` integration.

### Entity Types

**Device**: `irrigation.wyze_sprinkler_<mac>`
- State: Connected/Disconnected
- Attributes: IP, RSSI, SSID, Serial Number

**Zones**: `switch.wyze_sprinkler_zone_<number>`
- State: On/Off (running/stopped)
- Attributes:
  - `remaining_time`: Seconds remaining
  - `last_watered`: Last watering timestamp
  - `smart_duration`: Default duration
  - `quickrun_duration`: Manual run duration

**Services**:
- `irrigation.start_zone`: Start manual watering
- `irrigation.pause`: Pause watering
- `irrigation.resume`: Resume watering
- `irrigation.stop`: Stop watering
- `irrigation.set_zone_duration`: Update zone duration

## Traffic Capture Tools

Located in: `tools/`

### Quick Capture
```bash
python tools/quick_capture.py
```
Interactive menu for capturing API traffic.

### Manual Capture
```bash
# Start capture
mitmdump -s tools/wyze_capture_addon.py

# Run tests through proxy
python test_with_proxy.py

# Output: api_captures/wyze_api_calls_<timestamp>.json
```

See [tools/README.md](../tools/README.md) for detailed instructions.

## Implementation Timeline

1. **Phase 1**: Basic device and zone retrieval ✓
2. **Phase 2**: Running zone detection ✓
3. **Phase 3**: Last watered tracking ✓
4. **Phase 4**: Traffic capture tools ✓
5. **Phase 5**: Comprehensive testing ✓

## Known Limitations

1. **Schedule Management**: `get_schedules()` endpoint exists but not yet implemented in service
2. **Device Info**: `get_device_info()` requires base service enhancement
3. **Weather Integration**: Smart schedule details not fully exposed by API
4. **Historical Analytics**: Limited to recent 20 schedule runs (API limitation)

## Future Enhancements

- [ ] Implement `get_schedules()` for configured schedules
- [ ] Add schedule creation/editing capabilities
- [ ] Implement rain delay functionality
- [ ] Add weather-based schedule adjustments
- [ ] Support zone group operations
- [ ] Add moisture sensor integration (if hardware supports)

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Capture API Traffic
```bash
# Start proxy
mitmdump -s tools/wyze_capture_addon.py

# Configure environment
export HTTPS_PROXY=http://localhost:8080

# Run code
python your_script.py
```

### Common Issues

**"Device not found"**
- Verify device is online in Wyze app
- Check MAC address matches device

**"TLS handshake failed"**
- Most Wyze services use certificate pinning
- Irrigation service does NOT (this is expected behavior)

**"No zones running"**
- Zones update every 10-30 seconds
- Schedule may have just completed

## Contributing

When adding new features:

1. Check [API_ENDPOINTS.md](API_ENDPOINTS.md) for endpoint details
2. Add unit tests in `tests/test_irrigation_service.py`
3. Update integration tests in `tests/integration_test_irrigation.py`
4. Document new endpoints in API_ENDPOINTS.md
5. Update this document with new features

## Credits

Implementation based on API traffic analysis using:
- mitmproxy for traffic capture
- Real Wyze irrigation device (BS_WK1)
- Wyze mobile app behavior analysis

Developed for the `wyzeapy` library to provide Home Assistant integration.

## License

Part of the `wyzeapy` project. See main repository for license details.
