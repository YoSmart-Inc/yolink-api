"""YoLink Mqtt Client."""
from typing import Callable

from pydantic import ValidationError
from .exception import YoLinkClientError
from .model import BRDP
from .auth_mgr import YoLinkAuthMgr
from .const import YOLINK_API_MQTT_BROKER, YOLINK_API_MQTT_BROKER_POER
import uuid
import logging
import asyncio


_LOGGER = logging.getLogger(__name__)


class MqttClient:
    """Mqtt Client"""

    def __init__(self, authManager: YoLinkAuthMgr) -> None:
        self._auth_mgr = authManager
        self.loop = asyncio.get_running_loop()
        self._topic = None
        self._callback = None

    async def init_home_connection(self, home_id: str, callback: Callable) -> None:
        """Connect to Mqtt broker."""
        if home_id is None:
            raise YoLinkClientError("-1", "home not set!")

        if callback is None:
            raise YoLinkClientError("-1", "error message listener")
        self._callback = callback

        from paho.mqtt import client as mqtt

        client_id = mqtt.base62(uuid.uuid4().int, padding=22)
        self._mqttc = mqtt.Client(client_id, mqtt.MQTTv31)
        self._mqttc.enable_logger()
        self._mqttc.on_connect = self._mqtt_on_connection
        self._mqttc.on_disconnect = self._mqtt_on_disconnection
        self._mqttc.on_message = self._mqtt_on_message

        # check and fresh access token
        await self._auth_mgr.check_and_refresh_token()
        # set mqtt
        self._mqttc.username_pw_set(self._auth_mgr.access_token(), "")
        self._topic = f"yl-home/{home_id}/+/report"
        self._mqttc.subscribe(self._topic, 0)
        result = None
        try:
            result = await self.loop.run_in_executor(
                None,
                self._mqttc.connect,
                YOLINK_API_MQTT_BROKER,
                YOLINK_API_MQTT_BROKER_POER,
                600,
            )
        except OSError as err:
            _LOGGER.error(
                "Failed to connect to MQTT server due to exception: %s", err)
        if result is not None and result != 0:
            _LOGGER.error(
                "Failed to connect to MQTT server: %s", mqtt.error_string(
                    result)
            )
        self._mqttc.loop_start()

    def _mqtt_on_connection(self, _mqttc, _userdata, _flags, result_code: int) -> None:
        """On connect callback,resubscribe topic."""
        import paho.mqtt.client as mqtt

        if result_code != mqtt.CONNACK_ACCEPTED:
            _LOGGER.error(
                "Unable to connect to the MQTT broker: %s",
                mqtt.connack_string(result_code),
            )
            return
        # re-subscribe topic.
        _mqttc.subscribe(self._topic, 0)

    def _mqtt_on_disconnection(self, _mqttc, _userdata, result_code) -> None:
        """Mqtt On disconnection, try to fresh token and reconnect"""
        try:
            access_token = asyncio.run_coroutine_threadsafe(
                self._auth_mgr.check_and_refresh_token(), self.loop
            ).result()
            _mqttc.username_pw_set(access_token, "")
        except Exception as e:
            print(e)

    def _mqtt_on_message(self, _mqttc, _userdata, msg) -> None:
        """Mqtt on message."""
        _LOGGER.debug(
            "Received message on %s%s: %s",
            msg.topic,
            " (retained)" if msg.retain else "",
            msg.payload[0:8192],
        )
        keys = msg.topic.split("/")
        if len(keys) == 4 and keys[3] == "report":
            try:
                data = (keys[2], BRDP.parse_raw(msg.payload.decode("UTF-8")))
            except ValidationError:
                # fix sometimes report empty data
                _LOGGER.debug("Validation Error.")
            self._callback(data)
