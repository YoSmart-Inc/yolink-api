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

import aiohttp

# Add parent directory to path to import yolink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yolink.endpoint import Endpoints
from yolink.http_client import YoLinkHttpClient
from yolink.uac_auth_mgr import YoLinkUACAuthMgr


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
        auth_mgr = YoLinkUACAuthMgr(session, uaid, secret_key)

        # Authenticate and get token
        print("Connecting to YoLink API...")
        await auth_mgr.check_and_refresh_token()
        print("✓ Successfully authenticated!")

        # Create a client and make a test request
        client = YoLinkHttpClient(auth_mgr)

        # Fetch home info to verify connection
        print("\nFetching home information...")
        response = await client.execute(
            url=Endpoints.US.value.url, bsdp={"method": "Home.getGeneralInfo"}
        )

        print(f"✓ Connected to home: {response.data.get('name', 'Unknown')}")
        print(f"  Home ID: {response.data.get('id')}")


if __name__ == "__main__":
    asyncio.run(main())
