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
from datetime import datetime, timedelta, timezone

import aiohttp

# Add parent directory to path to import yolink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yolink.auth_mgr import YoLinkAuthMgr
from yolink.client import YoLinkClient
from yolink.const import OAUTH2_TOKEN
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
        auth_mgr = SimpleAuthManager(session, uaid, secret_key)
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

