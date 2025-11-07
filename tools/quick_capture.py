"""
Quick start script for capturing Wyze API traffic.

This script makes it easy to capture API traffic with one command.

Usage:
    python tools/quick_capture.py

Then just use your Wyze app or run your Python scripts with the proxy configured.
"""
import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 80)
    print("WYZE API QUICK CAPTURE")
    print("=" * 80)
    print("\nThis will start mitmproxy to capture Wyze API traffic.")
    print("\nOptions:")
    print("  1. Capture with terminal output (recommended)")
    print("  2. Capture with web interface (http://127.0.0.1:8081)")
    print("  3. Exit")

    choice = input("\nSelect option (1-3): ").strip()

    addon_path = Path(__file__).parent / "wyze_capture_addon.py"

    if choice == "1":
        print("\nStarting mitmdump with terminal output...")
        print("Press Ctrl+C to stop capturing\n")
        try:
            subprocess.run([
                "mitmdump",
                "-s", str(addon_path),
                "--set", "console_eventlog_verbosity=warn"
            ])
        except KeyboardInterrupt:
            print("\n\nCapture stopped")

    elif choice == "2":
        print("\nStarting mitmweb...")
        print("Web interface will be available at: http://127.0.0.1:8081")
        print("Press Ctrl+C to stop capturing\n")
        try:
            subprocess.run([
                "mitmweb",
                "-s", str(addon_path),
                "--web-port", "8081"
            ])
        except KeyboardInterrupt:
            print("\n\nCapture stopped")

    elif choice == "3":
        print("\nExiting...")
        sys.exit(0)

    else:
        print("\nInvalid option. Exiting...")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("Capture files saved to: api_captures/")
    print("=" * 80)


if __name__ == "__main__":
    main()
