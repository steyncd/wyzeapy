"""
Tool to capture Wyze API traffic using mitmproxy.

This script:
1. Starts mitmproxy in the background
2. Captures all HTTP/HTTPS traffic
3. Saves flows to a file that can be analyzed
4. Provides easy-to-read output of captured requests

Requirements:
    pip install mitmproxy

Usage:
    python tools/capture_api_traffic.py

    Then configure your device/app to use proxy: localhost:8080
    Install mitmproxy certificate on your device if needed
    Perform actions in the Wyze app
    Press Ctrl+C to stop capturing
"""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


class ApiTrafficCapture:
    def __init__(self, output_dir="api_captures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.flow_file = self.output_dir / f"flows_{self.timestamp}.mitm"
        self.json_file = self.output_dir / f"flows_{self.timestamp}.json"
        self.process = None

    def start_capture(self):
        """Start mitmproxy in the background to capture traffic."""
        print("=" * 80)
        print("WYZE API TRAFFIC CAPTURE")
        print("=" * 80)
        print(f"\nCapturing traffic to: {self.flow_file}")
        print("\nProxy Configuration:")
        print("  Host: localhost")
        print("  Port: 8080")
        print("\nSetup Instructions:")
        print("  1. Configure your device to use the proxy (localhost:8080)")
        print("  2. If using HTTPS, install mitmproxy certificate:")
        print("     - Visit http://mitm.it from the proxied device")
        print("     - Install the certificate for your platform")
        print("  3. Perform actions in the Wyze app")
        print("  4. Press Ctrl+C when done capturing")
        print("\n" + "=" * 80)

        # Start mitmdump in the background
        cmd = [
            "mitmdump",
            "--set", f"flow_detail=3",
            "--save-stream-file", str(self.flow_file),
            "--set", "console_eventlog_verbosity=info"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # Wait a moment for proxy to start
            time.sleep(2)
            print("\n[OK] mitmproxy is running on localhost:8080")
            print("\nWaiting for traffic... (Press Ctrl+C to stop)\n")

            # Monitor output
            for line in self.process.stdout:
                print(f"  {line.rstrip()}")

        except FileNotFoundError:
            print("\n[ERROR] mitmproxy not found!")
            print("Install it with: pip install mitmproxy")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n[STOPPING] Capture interrupted by user")
            self.stop_capture()
        except Exception as e:
            print(f"\n[ERROR] Failed to start mitmproxy: {e}")
            sys.exit(1)

    def stop_capture(self):
        """Stop the mitmproxy capture."""
        if self.process:
            print("\nStopping mitmproxy...")
            self.process.terminate()
            self.process.wait(timeout=5)
            print("[OK] Capture stopped")

        # Convert flows to JSON for easier analysis
        print(f"\nConverting flows to JSON: {self.json_file}")
        self.export_flows_to_json()

    def export_flows_to_json(self):
        """Export captured flows to JSON format."""
        if not self.flow_file.exists():
            print("[WARNING] No flow file found")
            return

        try:
            cmd = [
                "mitmdump",
                "--quiet",
                "--rfile", str(self.flow_file),
                "--save-stream-file", str(self.json_file),
                "--set", "flow_detail=3"
            ]
            subprocess.run(cmd, check=True)
            print(f"[OK] Flows saved to: {self.json_file}")

            # Parse and display summary
            self.display_summary()

        except Exception as e:
            print(f"[ERROR] Failed to export flows: {e}")

    def display_summary(self):
        """Display a summary of captured traffic."""
        print("\n" + "=" * 80)
        print("CAPTURE SUMMARY")
        print("=" * 80)

        # Use mitmdump to read the flows
        try:
            cmd = [
                "mitmdump",
                "--quiet",
                "--rfile", str(self.flow_file),
                "--scripts", str(Path(__file__).parent / "analyze_flows.py")
            ]

            # If analyze script doesn't exist, just show basic info
            if not (Path(__file__).parent / "analyze_flows.py").exists():
                print(f"\nFlow file saved: {self.flow_file}")
                print(f"JSON file saved: {self.json_file}")
                print("\nTo analyze the capture manually:")
                print(f"  mitmweb -r {self.flow_file}")
                print("\nOr use Python:")
                print(f"  python tools/analyze_captured_traffic.py {self.flow_file}")
            else:
                subprocess.run(cmd)

        except Exception as e:
            print(f"[WARNING] Could not display summary: {e}")
            print(f"\nFiles saved:")
            print(f"  - Flow file: {self.flow_file}")
            print(f"  - JSON file: {self.json_file}")


def main():
    capture = ApiTrafficCapture()

    try:
        capture.start_capture()
    except KeyboardInterrupt:
        capture.stop_capture()
    finally:
        print("\n" + "=" * 80)
        print("CAPTURE COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    main()
