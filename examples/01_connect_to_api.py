#!/usr/bin/env python3
"""
Example: Connect to YoLink API

This example demonstrates how to establish a connection to the YoLink API
using OAuth2 credentials. It shows the basic setup required to authenticate
and make API requests.

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
    """Main function demonstrating API connection."""
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

        # Authenticate and get token
        print("Connecting to YoLink API...")
        await auth_mgr.check_and_refresh_token()
        print(f"✓ Successfully authenticated!")
        print(f"  Token expires at: {auth_mgr._token_expires_at}")

        # Create a client and make a test request
        client = YoLinkClient(auth_mgr)

        # Fetch home info to verify connection
        print("\nFetching home information...")
        response = await client.execute(
            url=Endpoints.US.value.url,
            bsdp={"method": "Home.getGeneralInfo"}
        )

        print(f"✓ Connected to home: {response.data.get('name', 'Unknown')}")
        print(f"  Home ID: {response.data.get('id')}")


if __name__ == "__main__":
    asyncio.run(main())

