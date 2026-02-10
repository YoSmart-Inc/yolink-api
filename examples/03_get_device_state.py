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
from datetime import datetime, timedelta, timezone

import aiohttp

# Add parent directory to path to import yolink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yolink.auth_mgr import YoLinkAuthMgr
from yolink.client import YoLinkClient
from yolink.const import OAUTH2_TOKEN
from yolink.device import YoLinkDevice, YoLinkDeviceMode
from yolink.endpoint import Endpoints


class SimpleAuthManager(YoLinkAuthMgr):
    """
    A simple authentication manager that handles OAuth2 token management.

    This implementation fetches and refreshes access tokens using the
    client credentials grant type with UAID and Secret Key.
    """

    def __init__(self, session: aiohttp.ClientSession, uaid: str, secret_key: str) -> None:
        """
        Initialize the auth manager.

        Args:
            session: An aiohttp ClientSession for making HTTP requests
            uaid: Your YoLink User Access ID
            secret_key: Your YoLink Secret Key
        """
        super().__init__(session)
        self._uaid = uaid
        self._secret_key = secret_key
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def access_token(self) -> str:
        """Return the current access token."""
        return self._access_token or ""

    async def check_and_refresh_token(self) -> str:
        """
        Check if token is valid and refresh if necessary.

        Returns:
            The current valid access token
        """
        # Refresh if no token or token expires within 5 minutes
        if (
            self._access_token is None
            or self._token_expires_at is None
            or datetime.now(timezone.utc) >= self._token_expires_at - timedelta(minutes=5)
        ):
            await self._fetch_token()
        return self._access_token

    async def _fetch_token(self) -> None:
        """Fetch a new access token from YoLink OAuth2 endpoint."""
        async with self._session.post(
            OAUTH2_TOKEN,
            data={
                "grant_type": "client_credentials",
                "client_id": self._uaid,
                "client_secret": self._secret_key,
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()

            self._access_token = data["access_token"]
            # Token typically expires in 7200 seconds (2 hours)
            expires_in = data.get("expires_in", 7200)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)


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
        auth_mgr = SimpleAuthManager(session, uaid, secret_key)
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

        if not devices:
            print("No devices found in your account.")
            sys.exit(0)

        # If no device ID specified, list devices and let user choose
        if not device_id:
            print("Available devices:")
            for i, dev in enumerate(devices, 1):
                print(f"  {i}. {dev.get('name')} ({dev.get('type')}) - {dev.get('deviceId')}")
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

        print(f"Device: {device.device_name}")
        print(f"  Type: {device.device_type}")
        print(f"  Model: {device.device_model_name}")
        print(f"  ID: {device.device_id}")
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

