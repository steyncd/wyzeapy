# Wyze API Endpoints Documentation

This document details the Wyze API endpoints discovered through traffic capture and implementation.

## Base URLs

- **Irrigation Service**: `https://wyze-lockwood-service.wyzecam.com`
- **Platform Service**: `https://wyze-platform-service.wyzecam.com` (uses certificate pinning)
- **Membership Service**: `https://wyze-membership-service.wyzecam.com` (uses certificate pinning)
- **Earth Service**: `https://wyze-earth-service.wyzecam.com` (uses certificate pinning)

## Important Note: Certificate Pinning

Most Wyze services use **certificate pinning** for security, which prevents MITM debugging with tools like mitmproxy. However, the **irrigation service does NOT use certificate pinning**, making it the easiest service to debug and monitor.

## Irrigation Endpoints

### Authentication
All irrigation endpoints require standard Wyze authentication headers:
- `Authorization: Bearer <access_token>`
- `apikey`: API key
- `keyid`: Key ID

### Device Status

#### GET /plugin/irrigation/get_iot_prop
**Purpose**: Get device IoT properties including connection status, signal strength, IP address, etc.

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "props": {
      "RSSI": "-41",
      "IP": "192.168.0.99",
      "sn": "7C78B20702C7",
      "ssid": "YourNetwork",
      "iot_state": "connected"
    }
  }
}
```

**Key Fields**:
- `RSSI`: WiFi signal strength (dBm)
- `IP`: Device local IP address
- `sn`: Serial number
- `ssid`: WiFi network name
- `iot_state`: Connection status (`connected`, `disconnected`)

### Zone Management

#### GET /plugin/irrigation/zone
**Purpose**: Get all zone configurations for a device

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "zones": [
      {
        "zone_number": 1,
        "zone_id": "zone_abc123",
        "name": "Front Lawn",
        "enabled": true,
        "smart_duration": 1200,
        "quickrun_duration": 600
      }
    ]
  }
}
```

**Key Fields**:
- `zone_number`: Zone number (1-6)
- `zone_id`: Unique zone identifier
- `name`: User-defined zone name
- `enabled`: Whether zone is enabled
- `smart_duration`: Default watering duration in seconds
- `quickrun_duration`: Quick run duration in seconds

#### POST /plugin/irrigation/set_zone_quickrun_duration
**Purpose**: Update the quickrun duration for a specific zone

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7",
  "zone_number": 1,
  "quickrun_duration": 1800
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed"
}
```

### Schedule Management

#### GET /plugin/irrigation/schedule_runs
**Purpose**: Get schedule run history (past, running, upcoming schedules)

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7",
  "limit": 20,
  "offset": 0
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "schedules": [
      {
        "schedule_id": "sched_xyz789",
        "schedule_name": "Morning Watering",
        "schedule_state": "past",
        "schedule_type": "smart",
        "start_utc": "2025-11-07T08:00:00Z",
        "end_utc": "2025-11-07T08:30:00Z",
        "zone_runs": [
          {
            "zone_number": 1,
            "zone_id": "zone_abc123",
            "zone_name": "Front Lawn",
            "start_utc": "2025-11-07T08:00:00Z",
            "end_utc": "2025-11-07T08:10:00Z",
            "duration": 600
          }
        ]
      }
    ],
    "total": 45
  }
}
```

**Key Fields**:
- `schedule_state`: `past`, `running`, `upcoming`, or `skipped`
- `schedule_type`: `smart`, `manual`, `quickrun`
- `start_utc`/`end_utc`: ISO 8601 UTC timestamps
- `zone_runs`: Array of individual zone runs within the schedule
- `duration`: Actual run duration in seconds

**Usage Notes**:
- Use `schedule_state: "running"` to detect currently active zones
- Use `schedule_state: "past"` to populate `last_watered` timestamps
- Increase `limit` to get more history (we use 20 to get sufficient past runs)

#### GET /plugin/irrigation/schedule
**Purpose**: Get configured schedules (not the run history, but the schedule definitions)

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "schedules": [
      {
        "schedule_id": "sched_xyz789",
        "schedule_name": "Morning Watering",
        "enabled": true,
        "schedule_type": "smart",
        "schedule_time": "08:00",
        "days_of_week": [1, 3, 5],
        "zones": [1, 2, 3]
      }
    ]
  }
}
```

### Zone Control

#### POST /plugin/irrigation/quickrun
**Purpose**: Manually start a zone with quickrun duration

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7",
  "zone_number": 1
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "schedule_id": "quickrun_abc123"
  }
}
```

#### POST /plugin/irrigation/pause
**Purpose**: Pause a currently running zone

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed"
}
```

#### POST /plugin/irrigation/resume
**Purpose**: Resume a paused zone

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed"
}
```

#### POST /plugin/irrigation/stop
**Purpose**: Stop/cancel a currently running schedule

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed"
}
```

### Device Information

#### GET /plugin/irrigation/device_info
**Purpose**: Get detailed device information

**Request**:
```json
{
  "device_mac": "BS_WK1_7C78B20702C7"
}
```

**Response**:
```json
{
  "code": "0",
  "msg": "succeed",
  "data": {
    "device_mac": "BS_WK1_7C78B20702C7",
    "device_model": "BS_WK1",
    "firmware_version": "1.0.42",
    "hardware_version": "1.0"
  }
}
```

## Implementation Notes

### Running Zone Detection

To determine which zones are currently running:

1. Call `GET /plugin/irrigation/schedule_runs` with appropriate limit
2. Filter schedules where `schedule_state == "running"`
3. For each running schedule, iterate through `zone_runs`
4. Calculate remaining time: `end_utc - current_time`

### Last Watered Tracking

To populate `last_watered` for each zone:

1. Call `GET /plugin/irrigation/schedule_runs` with limit=20 (or higher)
2. Filter schedules where `schedule_state == "past"`
3. For each zone, find the most recent past schedule containing that zone
4. Use the `end_utc` timestamp from the zone_run as `last_watered`

### Timestamp Format

All timestamps use **ISO 8601 UTC format**: `2025-11-07T08:30:00Z`

### Error Codes

Common response codes:
- `"0"`: Success
- `"1000"`: Authentication error
- `"1001"`: Invalid parameters
- `"2000"`: Device offline
- `"2001"`: Device not found

## Traffic Capture Findings

Based on real traffic captures:

1. **No Certificate Pinning**: The irrigation service can be debugged with mitmproxy
2. **Regular Polling**: Apps poll `get_iot_prop` and `schedule_runs` every 5-10 seconds
3. **Efficient Updates**: Only changed data is sent in responses
4. **Schedule Types**:
   - `smart`: AI-optimized schedules based on weather
   - `manual`: User-defined schedules
   - `quickrun`: One-time manual activation

## Testing with mitmproxy

To capture irrigation traffic:

```bash
# Start capture
mitmdump -s tools/wyze_capture_addon.py

# Run test through proxy
python test_with_proxy.py

# Captured data saved to: api_captures/wyze_api_calls_<timestamp>.json
```

See [tools/README.md](../tools/README.md) for detailed capture instructions.
