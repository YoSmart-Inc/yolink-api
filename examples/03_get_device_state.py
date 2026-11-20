#!/usr/bin/env python3
"""
Example: Get Device State

This example demonstrates how to retrieve the current state of a specific
YoLink device. It shows how to query device status including online/offline
state, sensor readings, or switch states depending on the device type.

Required environment variables:
    YOLINK_UAID     - Your YoLink User Access ID
    YOLINK_SECRET_KEY - Your YoLink Secret Key

Optional environment variables:
    YOLINK_DEVICE_ID - The device ID to query (if not set, prompts user to select)

To obtain credentials:
    1. Go to https://www.yosmart.com and log into your account
    2. Navigate to Settings -> Account -> Advanced Settings -> User Access Credentials
    3. Generate a new UAID/Secret Key pair
"""

import asyncio
import json
import os
import sys

import aiohttp

# Add parent directory to path to import yolink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yolink.device import YoLinkDevice, YoLinkDeviceMode
from yolink.endpoint import Endpoints
from yolink.http_client import YoLinkHttpClient
from yolink.uac_auth_mgr import YoLinkUACAuthMgr


async def main() -> None:
    """Main function demonstrating device state retrieval."""
    # Get credentials from environment variables
    uaid = os.environ.get("YOLINK_UAID")
    secret_key = os.environ.get("YOLINK_SECRET_KEY")
    device_id = os.environ.get("YOLINK_DEVICE_ID")

    if not uaid or not secret_key:
        print("Error: Missing credentials!")
        print("Please set the following environment variables:")
        print("  YOLINK_UAID     - Your YoLink User Access ID")
        print("  YOLINK_SECRET_KEY - Your YoLink Secret Key")
        sys.exit(1)

    # Create an aiohttp session and auth manager
    async with aiohttp.ClientSession() as session:
        auth_mgr = YoLinkUACAuthMgr(session, uaid, secret_key)
        client = YoLinkHttpClient(auth_mgr)

        print("Connecting to YoLink API...")
        await auth_mgr.check_and_refresh_token()
        print("✓ Successfully authenticated!\n")

        # Fetch device list
        response = await client.execute(
            url=Endpoints.US.value.url, bsdp={"method": "Home.getDeviceList"}
        )
        devices = response.data.get("devices", [])

        if not devices:
            print("No devices found in your account.")
            sys.exit(0)

        # If no device ID specified, list devices and let user choose
        if not device_id:
            print("Available devices:")
            for i, dev in enumerate(devices, 1):
                print(
                    f"  {i}. {dev.get('name')} ({dev.get('type')}) - {dev.get('deviceId')}"
                )
            print()

            # Use the first device for demonstration
            device_id = devices[0].get("deviceId")
            print(f"Using first device: {devices[0].get('name')}\n")

        # Find the device in the list
        device_data = None
        for dev in devices:
            if dev.get("deviceId") == device_id:
                device_data = dev
                break

        if not device_data:
            print(f"Error: Device with ID '{device_id}' not found.")
            sys.exit(1)

        # Create a YoLinkDevice instance
        device_mode = YoLinkDeviceMode(**device_data)
        device = YoLinkDevice(device_mode, client)

        print(f"Device: {device.name}")
        print(f"  Type: {device.type}")
        print(f"  Model: {device.model_name}")
        print(f"  ID: {device.id}")
        print()

        # Get device state
        print("Fetching device state...")
        try:
            state_response = await device.get_state()

            print("✓ Device state retrieved:\n")
            # Pretty print the state data
            state_data = state_response.data
            print(json.dumps(state_data, indent=2))

        except Exception as e:
            print(f"Error fetching state: {e}")
            print("\nNote: Some devices (like hubs) may not support getState.")
            print("Try running this example with a sensor or switch device.")


if __name__ == "__main__":
    asyncio.run(main())
