#!/usr/bin/env python3
"""
Example: Control a Switch/Outlet

This example demonstrates how to control YoLink switches and outlets,
including turning them on/off. It works with Switch, Outlet, and MultiOutlet
device types.

Required environment variables:
    YOLINK_UAID     - Your YoLink User Access ID
    YOLINK_SECRET_KEY - Your YoLink Secret Key

Optional environment variables:
    YOLINK_DEVICE_ID - The switch/outlet device ID to control

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
from yolink.client_request import ClientRequest
from yolink.device import YoLinkDevice, YoLinkDeviceMode
from yolink.endpoint import Endpoints
from yolink.outlet_request_builder import OutletRequestBuilder
from yolink.uac_auth_mgr import YoLinkUACAuthMgr


# Device types that can be controlled as switches
CONTROLLABLE_TYPES = ["Switch", "Outlet", "MultiOutlet", "Manipulator"]


async def main() -> None:
    """Main function demonstrating switch control."""
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
        client = YoLinkClient(auth_mgr)

        print("Connecting to YoLink API...")
        await auth_mgr.check_and_refresh_token()
        print("✓ Successfully authenticated!\n")

        # Fetch device list
        response = await client.execute(
            url=Endpoints.US.value.url,
            bsdp={"method": "Home.getDeviceList"}
        )
        devices = response.data.get("devices", [])

        # Filter to controllable devices
        controllable_devices = [
            d for d in devices if d.get("type") in CONTROLLABLE_TYPES
        ]

        if not controllable_devices:
            print("No controllable switch/outlet devices found in your account.")
            print(f"This example works with: {', '.join(CONTROLLABLE_TYPES)}")
            sys.exit(0)

        # If no device ID specified, list controllable devices
        if not device_id:
            print("Available controllable devices:")
            for i, dev in enumerate(controllable_devices, 1):
                print(f"  {i}. {dev.get('name')} ({dev.get('type')}) - {dev.get('deviceId')}")
            print()

            # Use the first controllable device for demonstration
            device_id = controllable_devices[0].get("deviceId")
            print(f"Using: {controllable_devices[0].get('name')}\n")

        # Find the device in the list
        device_data = None
        for dev in devices:
            if dev.get("deviceId") == device_id:
                device_data = dev
                break

        if not device_data:
            print(f"Error: Device with ID '{device_id}' not found.")
            sys.exit(1)

        if device_data.get("type") not in CONTROLLABLE_TYPES:
            print(f"Error: Device '{device_data.get('name')}' is not a controllable device.")
            print(f"Type: {device_data.get('type')}")
            print(f"This example works with: {', '.join(CONTROLLABLE_TYPES)}")
            sys.exit(1)

        # Create a YoLinkDevice instance
        device_mode = YoLinkDeviceMode(**device_data)
        device = YoLinkDevice(device_mode, client)

        print(f"Device: {device.device_name}")
        print(f"  Type: {device.device_type}")
        print(f"  Model: {device.device_model_name}")
        print()

        # Get current state
        print("Getting current state...")
        try:
            state_response = await device.get_state()
            current_state = state_response.data.get("state", {}).get("state", "unknown")
            print(f"  Current state: {current_state}")
        except Exception as e:
            print(f"  Could not get state: {e}")
            current_state = "unknown"

        print()

        # Toggle the switch
        new_state = "close" if current_state == "open" else "open"
        state_label = "ON" if new_state == "open" else "OFF"

        print(f"Turning switch {state_label}...")

        # Use the OutletRequestBuilder to create the request
        # For MultiOutlet devices, you can specify plug_indx (0-based) to control individual outlets
        # Pass None for plug_indx to control all outlets or for single outlet devices
        request = OutletRequestBuilder.set_state_request(state=new_state, plug_indx=None)

        try:
            result = await device.call_device(request)

            if result.code == "000000":
                print(f"✓ Successfully turned {state_label}!")

                # Get the new state from the response
                new_state_data = result.data.get("state", {})
                print(f"  New state: {new_state_data.get('state', 'unknown')}")
            else:
                print(f"✗ Failed to change state: {result.desc}")

        except Exception as e:
            print(f"✗ Error: {e}")

        print()
        print("Note: For MultiOutlet devices (power strips), you can control individual outlets")
        print("      by passing the outlet index (0-based) to OutletRequestBuilder.set_state_request()")


if __name__ == "__main__":
    asyncio.run(main())

