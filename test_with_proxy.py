"""Run irrigation test through mitmproxy to capture traffic."""
import asyncio
import os
import ssl

# Set proxy environment variables
os.environ['HTTP_PROXY'] = 'http://localhost:8080'
os.environ['HTTPS_PROXY'] = 'http://localhost:8080'
# Disable SSL verification for the proxy
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Also disable SSL verification in Python
import aiohttp
ssl._create_default_https_context = ssl._create_unverified_context

from tests.integration_test_irrigation import test_irrigation_integration

if __name__ == "__main__":
    print("Starting test with proxy at localhost:8080...")
    print("Make sure mitmdump is running!")
    asyncio.run(test_irrigation_integration())
