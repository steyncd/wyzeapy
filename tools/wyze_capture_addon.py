"""
mitmproxy addon to capture and display Wyze API traffic in real-time.

Usage:
    mitmdump -s tools/wyze_capture_addon.py

This addon:
- Filters for Wyze API calls only
- Displays requests/responses in real-time
- Saves detailed info to a JSON file
- Automatically redacts sensitive information
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class WyzeApiCapture:
    def __init__(self):
        self.output_dir = Path("api_captures")
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = self.output_dir / f"wyze_api_calls_{self.timestamp}.json"
        self.calls = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.logger.info("=" * 80)
        self.logger.info("WYZE API CAPTURE - ACTIVE")
        self.logger.info("=" * 80)
        self.logger.info(f"Saving to: {self.output_file}")
        self.logger.info("Waiting for Wyze API traffic...")
        self.logger.info("=" * 80)

    def request(self, flow):
        """Called when a request is received."""
        request = flow.request

        # Filter for Wyze domains only
        if not any(domain in request.pretty_host for domain in [
            'wyze.com', 'wyzecam.com', 'wyze.io'
        ]):
            return

        self.logger.info(f"\n[REQUEST] {request.method} {request.pretty_url}")

    def response(self, flow):
        """Called when a response is received."""
        request = flow.request
        response = flow.response

        # Filter for Wyze domains only
        if not any(domain in request.pretty_host for domain in [
            'wyze.com', 'wyzecam.com', 'wyze.io'
        ]):
            return

        # Extract call information
        call_info = {
            'timestamp': datetime.fromtimestamp(flow.request.timestamp_start).isoformat(),
            'method': request.method,
            'url': request.pretty_url,
            'host': request.pretty_host,
            'path': request.path,
            'request': {
                'headers': self._sanitize_headers(dict(request.headers)),
                'body': self._extract_body(request.content)
            },
            'response': {
                'status': response.status_code,
                'headers': dict(response.headers),
                'body': self._extract_body(response.content)
            }
        }

        self.calls.append(call_info)

        # Display summary
        self.logger.info(f"[RESPONSE] {response.status_code} - {request.method} {request.path}")

        # Show interesting details
        if call_info['request']['body'] and isinstance(call_info['request']['body'], dict):
            self.logger.info(f"  Request: {self._get_summary(call_info['request']['body'])}")

        if call_info['response']['body'] and isinstance(call_info['response']['body'], dict):
            self.logger.info(f"  Response: {self._get_summary(call_info['response']['body'])}")

    def done(self):
        """Called when mitmproxy is shutting down."""
        if self.calls:
            self._save_calls()
            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"CAPTURE COMPLETE - {len(self.calls)} API calls saved")
            self.logger.info(f"Output file: {self.output_file}")
            self.logger.info("=" * 80)
        else:
            self.logger.info("\nNo Wyze API calls captured")

    def _extract_body(self, content: Optional[bytes]) -> any:
        """Extract and parse request/response body."""
        if not content:
            return None

        try:
            body_str = content.decode('utf-8')
            try:
                # Try to parse as JSON
                return json.loads(body_str)
            except json.JSONDecodeError:
                # Return as string if not JSON
                return body_str if len(body_str) < 1000 else f"{body_str[:1000]}..."
        except UnicodeDecodeError:
            return f"<binary data, {len(content)} bytes>"

    def _sanitize_headers(self, headers: dict) -> dict:
        """Sanitize sensitive information from headers."""
        sensitive_keys = ['authorization', 'access_token', 'apikey', 'key_id', 'signature2']
        sanitized = {}

        for key, value in headers.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '**REDACTED**'
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_data(self, data: any) -> any:
        """Recursively sanitize sensitive data."""
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = ['access_token', 'refresh_token', 'password', 'email', 'phone']

            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = '**REDACTED**'
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    def _get_summary(self, data: dict) -> str:
        """Get a brief summary of the data."""
        if not isinstance(data, dict):
            return str(data)[:100]

        # Show first few keys
        keys = list(data.keys())[:5]
        summary = ", ".join(keys)
        if len(data) > 5:
            summary += f", ... ({len(data)} keys total)"
        return summary

    def _save_calls(self):
        """Save captured calls to JSON file."""
        # Sanitize all calls before saving
        sanitized_calls = [
            {
                **call,
                'request': {
                    **call['request'],
                    'body': self._sanitize_data(call['request']['body'])
                },
                'response': {
                    **call['response'],
                    'body': self._sanitize_data(call['response']['body'])
                }
            }
            for call in self.calls
        ]

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_calls, f, indent=2, ensure_ascii=False)


# This is the entry point for mitmproxy
addons = [WyzeApiCapture()]
