#!/usr/bin/env python3
"""
Example: Subscribe to MQTT Events

This example demonstrates how to connect to YoLink's MQTT broker to receive
real-time device events. It shows:
- How to retrieve your home ID (required for MQTT subscription)
- How to connect to the MQTT broker using your access token
- How to process incoming device events

Required environment variables:
    YOLINK_UAID     - Your YoLink User Access ID
    YOLINK_SECRET_KEY - Your YoLink Secret Key

To obtain credentials:
    1. Go to https://www.yosmart.com and log into your account
    2. Navigate to Settings -> Account -> Advanced Settings -> User Access Credentials
    3. Generate a new UAID/Secret Key pair

Note: This example uses the aiomqtt library which is included in the yolink-api
dependencies. Events will be displayed as they are received from your devices.
Press Ctrl+C to stop listening.
"""

import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timedelta, timezone

import aiohttp
import aiomqtt

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


# Global flag for graceful shutdown
running = True


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\n\nShutting down...")
    running = False


async def main() -> None:
    """Main function demonstrating MQTT event subscription."""
    global running

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

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

        # Step 1: Get home ID (required for MQTT topic subscription)
        print("Retrieving home information...")
        home_response = await client.execute(
            url=Endpoints.US.value.url,
            bsdp={"method": "Home.getGeneralInfo"}
        )
        home_id = home_response.data.get("id")
        home_name = home_response.data.get("name", "Unknown")
        print(f"✓ Home: {home_name}")
        print(f"  Home ID: {home_id}\n")

        # Step 2: Get device list for reference when events come in
        device_response = await client.execute(
            url=Endpoints.US.value.url,
            bsdp={"method": "Home.getDeviceList"}
        )
        devices = {
            d.get("deviceId"): d.get("name", "Unknown")
            for d in device_response.data.get("devices", [])
        }
        print(f"Loaded {len(devices)} device(s) for event lookup\n")

        # Step 3: Connect to MQTT broker and subscribe to events
        # The topic format is: yl-home/{home_id}/+/report
        # The + is a wildcard that matches any device ID
        mqtt_topic = f"yl-home/{home_id}/+/report"

        print("Connecting to MQTT broker...")
        print(f"  Broker: {Endpoints.US.value.mqtt_broker_host}:{Endpoints.US.value.mqtt_broker_port}")
        print(f"  Topic: {mqtt_topic}")
        print()

        try:
            async with aiomqtt.Client(
                hostname=Endpoints.US.value.mqtt_broker_host,
                port=Endpoints.US.value.mqtt_broker_port,
                username=auth_mgr.access_token(),
                password="",  # Password is not used, only the token as username
                keepalive=60,
            ) as mqtt_client:
                print("✓ Connected to MQTT broker!")
                await mqtt_client.subscribe(mqtt_topic)
                print("✓ Subscribed to device events\n")
                print("=" * 60)
                print("Listening for events... Press Ctrl+C to stop")
                print("=" * 60)
                print()

                # Process incoming messages
                async for message in mqtt_client.messages:
                    if not running:
                        break

                    try:
                        # Parse the topic to extract device ID
                        # Topic format: yl-home/{home_id}/{device_id}/report
                        topic_parts = str(message.topic).split("/")
                        device_id = topic_parts[2] if len(topic_parts) >= 4 else "unknown"
                        device_name = devices.get(device_id, "Unknown Device")

                        # Parse the message payload
                        payload = json.loads(message.payload.decode("UTF-8"))

                        # Extract event information
                        event = payload.get("event", "unknown")
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Display the event
                        print(f"[{timestamp}] {device_name} ({device_id})")
                        print(f"  Event: {event}")

                        # Show relevant data based on event type
                        if "data" in payload:
                            data = payload["data"]

                            # Show state if present
                            if "state" in data:
                                print(f"  State: {json.dumps(data['state'], indent=4)}")

                            # Show other data fields
                            for key, value in data.items():
                                if key not in ["state", "loraInfo", "deviceId"]:
                                    print(f"  {key}: {value}")

                        print()

                    except json.JSONDecodeError:
                        print(f"Could not parse message: {message.payload[:100]}")
                    except Exception as e:
                        print(f"Error processing message: {e}")

        except aiomqtt.MqttError as e:
            print(f"MQTT Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

