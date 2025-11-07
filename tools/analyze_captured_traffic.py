"""
Analyze captured mitmproxy flows and extract Wyze API information.

Usage:
    python tools/analyze_captured_traffic.py <flow_file>

This will:
- Parse all captured HTTP requests/responses
- Extract Wyze API calls
- Show headers, payloads, and responses
- Generate a summary report
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def load_flows_from_mitm(flow_file: str) -> List[Dict[Any, Any]]:
    """Load flows from mitmproxy flow file using Python API."""
    try:
        from mitmproxy import io, http
        from mitmproxy.exceptions import FlowReadException

        flows = []
        with open(flow_file, "rb") as f:
            flow_reader = io.FlowReader(f)
            try:
                for flow in flow_reader.stream():
                    if isinstance(flow, http.HTTPFlow):
                        flows.append(flow)
            except FlowReadException as e:
                print(f"[WARNING] Error reading some flows: {e}")

        return flows

    except ImportError:
        print("[ERROR] mitmproxy Python library not found")
        print("Install it with: pip install mitmproxy")
        sys.exit(1)


def extract_wyze_api_calls(flows) -> List[Dict[str, Any]]:
    """Extract Wyze-related API calls from flows."""
    wyze_calls = []

    for flow in flows:
        request = flow.request
        response = flow.response

        # Check if this is a Wyze API call
        if not any(domain in request.pretty_host for domain in [
            'wyze.com', 'wyzecam.com', 'wyze.io'
        ]):
            continue

        # Extract request info
        call_info = {
            'timestamp': flow.request.timestamp_start,
            'method': request.method,
            'url': request.pretty_url,
            'host': request.pretty_host,
            'path': request.path,
            'headers': dict(request.headers),
            'body': None,
            'response_status': None,
            'response_headers': None,
            'response_body': None
        }

        # Extract request body
        if request.content:
            try:
                call_info['body'] = request.content.decode('utf-8')
                # Try to parse as JSON
                try:
                    call_info['body_json'] = json.loads(call_info['body'])
                except:
                    pass
            except:
                call_info['body'] = f"<binary data, {len(request.content)} bytes>"

        # Extract response info
        if response:
            call_info['response_status'] = response.status_code
            call_info['response_headers'] = dict(response.headers)

            if response.content:
                try:
                    call_info['response_body'] = response.content.decode('utf-8')
                    # Try to parse as JSON
                    try:
                        call_info['response_json'] = json.loads(call_info['response_body'])
                    except:
                        pass
                except:
                    call_info['response_body'] = f"<binary data, {len(response.content)} bytes>"

        wyze_calls.append(call_info)

    return wyze_calls


def sanitize_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from data."""
    sensitive_keys = [
        'access_token', 'refresh_token', 'password', 'email',
        'phone', 'apikey', 'key_id', 'authorization'
    ]

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '**REDACTED**'
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_sensitive_data(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    else:
        return data


def display_api_call(call: Dict[str, Any], index: int):
    """Display a single API call in a readable format."""
    print(f"\n{'=' * 80}")
    print(f"API CALL #{index}")
    print(f"{'=' * 80}")
    print(f"Time: {call['timestamp']}")
    print(f"Method: {call['method']}")
    print(f"URL: {call['url']}")

    print(f"\nRequest Headers:")
    for key, value in call['headers'].items():
        if 'token' in key.lower() or 'authorization' in key.lower():
            print(f"  {key}: **REDACTED**")
        else:
            print(f"  {key}: {value}")

    if call.get('body_json'):
        print(f"\nRequest Body (JSON):")
        sanitized = sanitize_sensitive_data(call['body_json'])
        print(json.dumps(sanitized, indent=2))
    elif call.get('body') and not call['body'].startswith('<binary'):
        print(f"\nRequest Body:")
        print(call['body'][:500])  # First 500 chars

    if call.get('response_status'):
        print(f"\nResponse Status: {call['response_status']}")

        if call.get('response_json'):
            print(f"\nResponse Body (JSON):")
            sanitized = sanitize_sensitive_data(call['response_json'])
            print(json.dumps(sanitized, indent=2))
        elif call.get('response_body') and not call['response_body'].startswith('<binary'):
            print(f"\nResponse Body:")
            print(call['response_body'][:500])  # First 500 chars


def generate_summary(calls: List[Dict[str, Any]]):
    """Generate a summary of captured API calls."""
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    # Group by endpoint
    endpoints = defaultdict(int)
    for call in calls:
        endpoint = f"{call['method']} {call['path']}"
        endpoints[endpoint] += 1

    print(f"\nTotal API calls captured: {len(calls)}")
    print(f"\nEndpoints called:")
    for endpoint, count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count:3d}x  {endpoint}")

    # Unique hosts
    hosts = set(call['host'] for call in calls)
    print(f"\nHosts contacted:")
    for host in sorted(hosts):
        print(f"  - {host}")


def export_to_json(calls: List[Dict[str, Any]], output_file: str):
    """Export API calls to JSON file."""
    sanitized_calls = [sanitize_sensitive_data(call) for call in calls]

    with open(output_file, 'w') as f:
        json.dump(sanitized_calls, f, indent=2, default=str)

    print(f"\n[OK] Exported to: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_captured_traffic.py <flow_file>")
        sys.exit(1)

    flow_file = sys.argv[1]

    if not Path(flow_file).exists():
        print(f"[ERROR] Flow file not found: {flow_file}")
        sys.exit(1)

    print(f"Loading flows from: {flow_file}")
    flows = load_flows_from_mitm(flow_file)
    print(f"[OK] Loaded {len(flows)} flows")

    print("\nExtracting Wyze API calls...")
    wyze_calls = extract_wyze_api_calls(flows)
    print(f"[OK] Found {len(wyze_calls)} Wyze API calls")

    if not wyze_calls:
        print("\n[WARNING] No Wyze API calls found in capture")
        return

    # Display each call
    for i, call in enumerate(wyze_calls, 1):
        display_api_call(call, i)

    # Generate summary
    generate_summary(wyze_calls)

    # Export to JSON
    output_file = Path(flow_file).parent / f"{Path(flow_file).stem}_analyzed.json"
    export_to_json(wyze_calls, str(output_file))

    print(f"\n{'=' * 80}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
