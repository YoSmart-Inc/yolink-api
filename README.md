# YoLink API

A Python library for interacting with [YoLink](https://www.yolink.com) smart home devices. This library provides async support for authenticating with YoLink's cloud API, managing devices, and receiving real-time MQTT events.

## Features

- **OAuth2 Authentication**: Secure token-based authentication with automatic refresh
- **Device Management**: Enumerate and control all YoLink devices in your home
- **Real-time Events**: Subscribe to MQTT events for instant device state updates
- **Multi-region Support**: Works with both US and EU YoLink endpoints
- **Async/Await**: Fully asynchronous design using `aiohttp` and `aiomqtt`

## Installation

```bash
# Using pip
pip install yolink-api

# Using uv
uv add yolink-api
```

### From Source

```bash
git clone https://github.com/YoSmart-Inc/yolink-api.git
cd yolink-api
uv sync
```

## Project Structure

```
yolink-api/
├── examples/                    # Example scripts for common tasks
│   ├── 01_connect_to_api.py    # Basic API connection
│   ├── 02_enumerate_devices.py # List all devices
│   ├── 03_get_device_state.py  # Query device state
│   ├── 04_control_switch.py    # Control switches/outlets
│   └── 05_mqtt_events.py       # Subscribe to real-time events
├── yolink/                      # Main package
│   ├── auth_mgr.py             # Abstract authentication manager and access token manager
│   ├── client.py               # HTTP client for API requests
│   ├── client_request.py       # Request model for device commands
│   ├── const.py                # Constants and device type definitions
│   ├── device.py               # YoLinkDevice class and models
│   ├── device_helper.py        # Device utility functions
│   ├── endpoint.py             # API endpoint definitions (US/EU)
│   ├── exception.py            # Custom exception classes
│   ├── home_manager.py         # YoLinkHome manager class
│   ├── message_listener.py     # Abstract MQTT message listener
│   ├── message_resolver.py     # Device-specific message parsing
│   ├── model.py                # BRDP/BSDP data models
│   ├── mqtt_client.py          # MQTT client for real-time events
│   ├── outlet_request_builder.py    # Builder for outlet/switch commands
│   ├── thermostat_request_builder.py # Builder for thermostat commands
│   ├── uac_auth_mgr.py         # Authentication manager for User Access Credentials
│   └── unit_helper.py          # Unit conversion utilities
├── pyproject.toml              # Project metadata and dependencies
└── README.md
```

## Getting Started

### 1. Obtain API Credentials

To use the YoLink API, you need a User Access ID (UAID) and Secret Key:

1. Log into your YoLink account at [yosmart.com](https://www.yosmart.com)
2. Navigate to **Settings** → **Account** → **Advanced Settings** → **User Access Credentials**
3. Click **Generate** to create a new UAID/Secret Key pair
4. Save these credentials securely - you'll need them for API access

### 2. Set Environment Variables

Export your credentials as environment variables:

```bash
export YOLINK_UAID="your_user_access_id"
export YOLINK_SECRET_KEY="your_secret_key"
```

### 3. Run an Example

```bash
# Connect to the API and verify credentials
python examples/01_connect_to_api.py

# List all your devices
python examples/02_enumerate_devices.py
```

## Quickstart

### Connect to the API

```python
import asyncio

import aiohttp

from yolink.client import YoLinkClient
from yolink.endpoint import Endpoints
from yolink.uac_auth_mgr import YoLinkUACAuthMgr


async def main():
    uaid = "your_uaid"
    secret_key = "your_secret_key"
    
    async with aiohttp.ClientSession() as session:
        auth_mgr = YoLinkUACAuthMgr(session, uaid, secret_key)
        client = YoLinkClient(auth_mgr)
        
        # Authenticate
        await auth_mgr.check_and_refresh_token()
        print("Connected!")

asyncio.run(main())
```

### Get Home Information

```python
from yolink.auth_mgr import YoLinkAuthMgr
from yolink.home_manager import async_get_home_info

async def show_home(auth_mgr: YoLinkAuthMgr):
    home = await async_get_home_info(auth_mgr)
    print(f"{home.name or 'Unknown'} ({home.id})")
```

### Enumerate Devices

```python
async def list_devices(client: YoLinkClient):
    response = await client.execute(
        url=Endpoints.US.value.url,
        bsdp={"method": "Home.getDeviceList"}
    )
    
    for device in response.data.get("devices", []):
        print(f"{device['name']} ({device['type']}) - {device['deviceId']}")
```

### Get Device State

```python
from yolink.device import YoLinkDevice, YoLinkDeviceMode

async def get_device_state(client: YoLinkClient, device_data: dict):
    # Create a device instance from the device data
    device_mode = YoLinkDeviceMode(**device_data)
    device = YoLinkDevice(device_mode, client)
    
    # Get current state
    state = await device.get_state()
    print(f"State: {state.data}")
```

### Control a Switch

```python
from yolink.outlet_request_builder import OutletRequestBuilder

async def toggle_switch(device: YoLinkDevice, turn_on: bool):
    # "open" = ON, "close" = OFF
    state = "open" if turn_on else "close"
    request = OutletRequestBuilder.set_state_request(state=state, plug_indx=None)
    result = await device.call_device(request)
    
    if result.code == "000000":
        print("Success!")
    else:
        print(f"Failed: {result.desc}")
```

### Subscribe to MQTT Events

```python
import aiomqtt

async def listen_for_events(auth_mgr: YoLinkUACAuthMgr, home_id: str):
    topic = f"yl-home/{home_id}/+/report"
    
    async with aiomqtt.Client(
        hostname=Endpoints.US.value.mqtt_broker_host,
        port=Endpoints.US.value.mqtt_broker_port,
        username=auth_mgr.access_token(),
        password="",
        keepalive=60,
    ) as client:
        await client.subscribe(topic)
        
        async for message in client.messages:
            print(f"Event: {message.payload.decode()}")
```

## Supported Devices

This library supports a wide range of YoLink devices including:

| Category               | Device Types                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Hubs**               | Hub (YS1603-UC), SpeakerHub (YS1604-UC)                                                                                   |
| **Sensors**            | Door Sensor, Motion Sensor, Water Leak Sensor, Temperature/Humidity Sensor, Vibration Sensor, CO/Smoke Alarm, Soil Sensor |
| **Switches & Outlets** | In-Wall Switch, Outlet, Multi-Outlet, Smart Plug, Power Strip                                                             |
| **Controllers**        | Thermostat, Garage Door Controller, Water Valve, Sprinkler Controller                                                     |
| **Locks**              | Smart Lock M1, Smart Lock M2                                                                                              |
| **Remotes**            | KeyFob, On/Off Fob, DimmerFob, SirenFob, FlexFob                                                                          |
| **Alarms**             | Siren Alarm, Outdoor Alarm, Power Fail Alarm                                                                              |

See the [full device list](#device-models) below for specific model numbers.

## API Reference

### YoLinkAuthMgr (Abstract Base Class)

The authentication manager handles OAuth2 token management. You must implement:

- `access_token() -> str`: Return the current access token
- `check_and_refresh_token() -> str`: Ensure token is valid, refresh if needed

### YoLinkUACAuthMgr

A ready-made `YoLinkAuthMgr` for User Access Credentials (UAID and Secret Key):

- `YoLinkUACAuthMgr(session, uaid, secret_key)`: Create the manager with an `aiohttp.ClientSession`
- `check_and_refresh_token() -> str`: Fetch the token on first use and refresh it at half of its lifetime. A failed refresh, other than refused credentials, keeps the cached token until it expires
- `access_token() -> str | None`: Return the current token, or `None` before the first fetch

It raises `YoLinkAuthFailError` when the credentials are refused and `YoLinkClientError` for any other failure (network error, timeout, malformed response).

### YoLinkAccessTokenAuthMgr

A `YoLinkAuthMgr` (in `yolink.auth_mgr`) for callers that already hold a valid access token, for example right after an OAuth exchange:

- `YoLinkAccessTokenAuthMgr(session, access_token)`: Create the manager with an `aiohttp.ClientSession` and the token
- `access_token() -> str` and `check_and_refresh_token() -> str`: Both return the token, which cannot be refreshed

### YoLinkClient

The HTTP client for making API requests:

- `execute(url, bsdp, **kwargs) -> BRDP`: Execute an API request. A response body that fails validation raises `YoLinkClientError` with the code `invalid_response`
- `get(url, **kwargs) -> ClientResponse`: Make a GET request
- `post(url, **kwargs) -> ClientResponse`: Make a POST request

### YoLinkDevice

Represents a single YoLink device:

- `get_state() -> BRDP`: Get real-time device state
- `fetch_state() -> BRDP`: Fetch cached device state
- `call_device(request: ClientRequest) -> BRDP`: Send a command to the device

### async_get_home_info

`async_get_home_info(auth_mgr) -> YoLinkHomeInfo` (in `yolink.home_manager`) makes the `Home.getGeneralInfo` call, without loading devices or connecting to MQTT. `YoLinkHomeInfo` is a frozen dataclass with `id: str` and `name: str | None` (the name is not documented by the API, but is returned in practice). It raises `YoLinkAuthFailError` when the API refuses the token (code `000103`), `asyncio.TimeoutError` when the request exceeds its total timeout, and `YoLinkClientError` otherwise, for example `-1003` for HTTP and connection errors (including connection and socket timeouts), or `invalid_response` when the response is unusable (it fails validation or has no usable home id).

### YoLinkHome

High-level manager for your YoLink home (used for Home Assistant integration):

- `async_setup(auth_mgr, listener)`: Initialize the home manager
- `async_unload()`: Clean up resources
- `get_devices() -> list[YoLinkDevice]`: Get all devices
- `get_device(device_id) -> YoLinkDevice`: Get a specific device

## Device Models

<details>
<summary>Click to expand full device list</summary>

- YS1603-UC (Hub)
- YS1604-UC (SpeakerHub)
- YS3604-UC (YoLink KeyFob)
- YS3605-UC (YoLink On/OffFob)
- YS3606-UC (YoLink DimmerFob)
- YS3607-UC (YoLink SirenFob)
- YS3614-UC (YoLink Mini FlexFob)
- YS4002-UC (YoLink Thermostat)
- YS4003-UC (YoLink Thermostat Heatpump)
- YS4906-UC + YS7706-UC (Garage Door Kit 1)
- YS4908-UC + YS7706-UC (Garage Door Kit 2 (Finger))
- YS4909-UC (Water Valve Controller)
- YS5001-UC (X3 Water Valve Controller)
- YS5002-UC (YoLink Motorized Ball Valve)
- YS5003-UC (Water Valve Controller 2)
- YS5705-UC (In-Wall Switch)
- YS5706-UC (YoLink Relay)
- YS5707-UC (Dimmer Switch)
- YS5708-UC (In-Wall Switch 2)
- YS6602-UC (YoLink Energy Plug)
- YS6604-UC (YoLink Plug Mini)
- YS6704-UC (In-wall Outlet)
- YS6801-UC (Smart Power Strip)
- YS6802-UC (Smart Outdoor Power Strip)
- YS6803-UC (Outdoor Energy Plug)
- YS7103-UC (Siren Alarm)
- YS7104-UC (Outdoor Alarm Controller)
- YS7105-UC (X3 Outdoor Alarm Controller)
- YS7106-UC (Power Fail Alarm)
- YS7107-UC (Outdoor Alarm Controller 2)
- YS7201-UC (Vibration Sensor)
- YS7606-UC (YoLink Smart Lock M1)
- YS7607-UC (YoLink Smart Lock M2)
- YS7704-UC (Door Sensor)
- YS7706-UC (Garage Door Sensor)
- YS7707-UC (Contact Sensor)
- YS7804-UC (Motion Sensor)
- YS7805-UC (Outdoor Motion Sensor)
- YS7903-UC (Water Leak Sensor)
- YS7904-UC (Water Leak Sensor 2)
- YS7906-UC (Water Leak Sensor 4)
- YS7916-UC (Water Leak Sensor 4 MoveAlert)
- YS7905-UC (WaterDepthSensor)
- YS7A01-UC (Smart Smoke/CO Alarm)
- YS8003-UC (Temperature Humidity Sensor)
- YS8004-UC (Weatherproof Temperature Sensor)
- YS8005-UC (Weatherproof Temperature & Humidity Sensor)
- YS8006-UC (X3 Temperature & Humidity Sensor)
- YS8014-UC (X3 Outdoor Temperature Sensor)
- YS8015-UC (X3 Outdoor Temperature & Humidity Sensor)
- YS5006-UC (FlowSmart Control)
- YS5007-UC (FlowSmart Meter)
- YS5008-UC (FlowSmart All-in-One)
- YS8017-UC (Thermometer)
- YS5009-UC (LeakStop Controller)
- YS5029-UC (LeakStop Controller 2 Channel)
- YS8009-UC (Soil Temperature & Humidity Sensor)
- YS4102-UC (Smart Sprinkler Controller)
- YS4103-UC (Smart Sprinkler Controller V2)
- YS7A12-UC (Smoke Alarm)
- YS7A06-UC (Smart CO Alarm)

</details>

## Error Handling

The library defines several exception types:

- `YoLinkError`: Base exception class
- `YoLinkClientError`: API request errors
- `YoLinkAuthFailError`: Authentication failures
- `YoLinkDeviceConnectionFailed`: Device communication errors
- `YoLinkUnSupportedMethodError`: Unsupported device operations

```python
from yolink.exception import YoLinkClientError, YoLinkAuthFailError

try:
    await device.get_state()
except YoLinkAuthFailError:
    print("Authentication failed - check your credentials")
except YoLinkClientError as e:
    print(f"API error {e.code}: {e.message}")
```

## Dependencies

- `aiohttp>=3.8.1` - Async HTTP client
- `aiomqtt>=2.0.0,<3.0.0` - Async MQTT client
- `pydantic>=2.0.0` - Data validation
- `tenacity>=8.1.0` - Retry logic

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Source Code](https://github.com/YoSmart-Inc/yolink-api)
- [Bug Tracker](https://github.com/YoSmart-Inc/yolink-api/issues)
- [YoLink Official Site](https://www.yosmart.com)
