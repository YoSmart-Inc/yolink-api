#!/usr/bin/env python3
"""
Example: Enumerate YoLink Devices

This example demonstrates how to list all devices registered to your
YoLink account. It shows device details including ID, name, type, and model.

Required environment variables:
    YOLINK_UAID     - Your YoLink User Access ID
    YOLINK_SECRET_KEY - Your YoLink Secret Key

To obtain credentials:
    1. Go to https://www.yosmart.com and log into your account
    2. Navigate to Settings -> Account -> Advanced Settings -> User Access Credentials
    3. Generate a new UAID/Secret Key pair
"""

import asyncio
import os
import sys

import aiohttp

# Add parent directory to path to import yolink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yolink.client import YoLinkClient
from yolink.endpoint import Endpoints
from yolink.uac_auth_mgr import YoLinkUACAuthMgr


async def main() -> None:
    """Main function demonstrating device enumeration."""
    # Get credentials from environment variables
    uaid = os.environ.get("YOLINK_UAID")
    secret_key = os.environ.get("YOLINK_SECRET_KEY")

    if not uaid or not secret_key:
        print("Error: Missing credentials!")
        print("Please set the following environment variables:")
        print("  YOLINK_UAID     - Your YoLink User Access ID")
        print("  YOLINK_SECRET_KEY - Your YoLink Secret Key")
        sys.exit(1)

    # Create an aiohttp session and auth manager
    async with aiohttp.ClientSession() as session:
        auth_mgr = YoLinkUACAuthMgr(session, uaid, secret_key)
        client = YoLinkClient(auth_mgr)

        print("Connecting to YoLink API...")
        await auth_mgr.check_and_refresh_token()
        print("✓ Successfully authenticated!\n")

        # Fetch device list
        print("Fetching device list...")
        response = await client.execute(
            url=Endpoints.US.value.url,
            bsdp={"method": "Home.getDeviceList"}
        )

        devices = response.data.get("devices", [])
        print(f"✓ Found {len(devices)} device(s)\n")

        # Display device information
        print("-" * 80)
        print(f"{'Name':<25} {'Type':<20} {'Model':<15} {'Device ID':<20}")
        print("-" * 80)

        for device in devices:
            name = device.get("name", "Unknown")[:24]
            device_type = device.get("type", "Unknown")[:19]
            model = device.get("modelName", "Unknown")[:14]
            device_id = device.get("deviceId", "Unknown")[:19]

            print(f"{name:<25} {device_type:<20} {model:<15} {device_id:<20}")

        print("-" * 80)

        # Group devices by type
        print("\nDevices by type:")
        device_types: dict[str, int] = {}
        for device in devices:
            dtype = device.get("type", "Unknown")
            device_types[dtype] = device_types.get(dtype, 0) + 1

        for dtype, count in sorted(device_types.items()):
            print(f"  {dtype}: {count}")


if __name__ == "__main__":
    asyncio.run(main())

