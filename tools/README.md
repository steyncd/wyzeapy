# Wyze API Traffic Capture Tools

This directory contains tools for capturing and analyzing Wyze API traffic using mitmproxy.

## Prerequisites

Install mitmproxy:
```bash
pip install mitmproxy
```

## Method 1: Simple Real-Time Capture (Recommended)

Use the mitmproxy addon for automatic capture and filtering:

```bash
# Start mitmproxy with the Wyze capture addon
mitmdump -s tools/wyze_capture_addon.py

# Or use mitmweb for a web interface
mitmweb -s tools/wyze_capture_addon.py
```

This will:
- Start a proxy on `localhost:8080`
- Automatically filter for Wyze API calls only
- Display requests/responses in real-time
- Save detailed JSON to `api_captures/wyze_api_calls_<timestamp>.json`
- Automatically redact sensitive information

### Configure Your Device/App

#### For Mobile Devices:
1. Go to WiFi settings
2. Configure HTTP proxy:
   - Host: `<your-computer-ip>`
   - Port: `8080`
3. Install mitmproxy certificate:
   - Visit http://mitm.it from your device
   - Install the certificate for your platform
4. Open Wyze app and perform actions

#### For Python Scripts:
```python
import os

# Set proxy environment variables
os.environ['HTTP_PROXY'] = 'http://localhost:8080'
os.environ['HTTPS_PROXY'] = 'http://localhost:8080'

# Then run your Wyze API code
```

## Method 2: Full Capture with Analysis

For more control, use the standalone capture script:

```bash
python tools/capture_api_traffic.py
```

This will:
- Start mitmproxy in capture mode
- Save all traffic to a flow file
- Press Ctrl+C when done capturing

Then analyze the capture:
```bash
python tools/analyze_captured_traffic.py api_captures/flows_<timestamp>.mitm
```

This will:
- Parse all HTTP flows
- Extract Wyze API calls
- Display detailed request/response information
- Generate a summary report
- Export to JSON

## Method 3: Using mitmproxy Directly

For manual inspection:

```bash
# Start with web interface
mitmweb

# Or use the terminal interface
mitmproxy

# Save flows to file
mitmdump -w flows.mitm
```

Then view later:
```bash
mitmweb -r flows.mitm
```

## Output Files

All captured data is saved to the `api_captures/` directory:

- `flows_<timestamp>.mitm` - Raw mitmproxy flow file
- `flows_<timestamp>.json` - Converted JSON export
- `wyze_api_calls_<timestamp>.json` - Filtered Wyze API calls with sanitized data
- `flows_<timestamp>_analyzed.json` - Detailed analysis output

## Security & Privacy

**Important Notes:**

1. **Sensitive Data**: The tools automatically redact:
   - Access tokens
   - Refresh tokens
   - Passwords
   - Email addresses
   - API keys
   - Authorization headers

2. **Certificate Trust**: When you install the mitmproxy certificate, you're allowing it to intercept HTTPS traffic. Only do this on devices you control and remove the certificate when done.

3. **Local Only**: By default, the proxy only listens on localhost. To allow remote devices:
   ```bash
   mitmdump --listen-host 0.0.0.0 -s tools/wyze_capture_addon.py
   ```

4. **Don't Commit Captures**: The `api_captures/` directory is in `.gitignore` to prevent accidentally committing sensitive data.

## Troubleshooting

### "SSL certificate verification failed"
- Make sure you've installed the mitmproxy certificate from http://mitm.it

### "Connection refused"
- Check that mitmproxy is running
- Verify the proxy host/port configuration

### "No traffic captured"
- Ensure your device/app is configured to use the proxy
- Check that you're performing actions that make API calls
- Verify you're looking for traffic to `*.wyze.com` or `*.wyzecam.com` domains

### Certificate Issues on Android
- Android 7+ requires manual certificate installation
- Go to Settings > Security > Install from storage
- Select the mitmproxy certificate

## Example Workflow

1. Start capture:
   ```bash
   mitmdump -s tools/wyze_capture_addon.py
   ```

2. Configure your Wyze app to use the proxy

3. Perform actions in the app (e.g., turn on a light, start irrigation)

4. Press Ctrl+C to stop capture

5. Review the output:
   ```bash
   cat api_captures/wyze_api_calls_<timestamp>.json
   ```

6. Use the data to understand API endpoints and implement new features!

## Integration with Development

When developing new features:

1. Capture the API traffic for the feature you want to implement
2. Analyze the requests/responses
3. Implement the corresponding methods in `wyzeapy`
4. Test against the real API
5. Add unit tests with mocked responses

## Advanced Usage

### Custom Filtering

Modify `wyze_capture_addon.py` to capture specific endpoints:

```python
def request(self, flow):
    request = flow.request

    # Only capture irrigation-related calls
    if 'irrigation' in request.path:
        # ... process
```

### Export to HAR Format

For use with other tools:

```bash
mitmdump -r flows.mitm --save-stream-file flows.har
```

### Real-time Processing

Add custom logic to the addon to process requests in real-time:

```python
def response(self, flow):
    # Custom processing
    if 'device/get_prop' in flow.request.path:
        # Extract device properties
        data = json.loads(flow.response.content)
        # ... process data
```
