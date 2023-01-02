"""YoLink Mqtt Client."""
import uuid
import logging
import asyncio
from pydantic import ValidationError
from paho.mqtt import client as mqtt
from .model import BRDP
from .auth_mgr import YoLinkAuthMgr
from .const import YOLINK_API_MQTT_BROKER, YOLINK_API_MQTT_BROKER_PORT
from .message_listener import MessageListener

_LOGGER = logging.getLogger(__name__)


class YoLinkMqttClient:
    """YoLink mqtt client."""

    def __init__(self, auth_manager: YoLinkAuthMgr) -> None:
        self.loop = asyncio.get_running_loop()
        self._home_topic = None
        self._mqtt_client = None
        self._message_listener = None
        self._auth_mgr = auth_manager

    async def connect(self, home_id: str, listener: MessageListener) -> None:
        """Connect to yolink mqtt broker."""

        self._home_topic = f"yl-home/{home_id}/+/report"
        self._message_listener = listener
        client_id = mqtt.base62(uuid.uuid4().int, padding=22)
        self._mqtt_client = mqtt.Client(client_id, mqtt.MQTTv31)
        self._mqtt_client.enable_logger()
        self._mqtt_client.on_connect = self._mqtt_on_connection
        self._mqtt_client.on_disconnect = self._mqtt_on_disconnection
        self._mqtt_client.on_message = self._mqtt_on_message

        # check and fresh access token
        await self._auth_mgr.check_and_refresh_token()
        # set connection options
        self._mqtt_client.username_pw_set(self._auth_mgr.access_token(), "")

        try:
            self._mqtt_client.connect_async(
                YOLINK_API_MQTT_BROKER, YOLINK_API_MQTT_BROKER_PORT, 60
            )
            self._mqtt_client.loop_start()
        except OSError as err:
            _LOGGER.error("Failed to connect to MQTT server due to exception: %s", err)

    async def disconnect(self):
        """Disconnect from yolink mqtt broker."""
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()

    def _mqtt_on_connection(self, _mqttc, _userdata, _flags, result_code: int) -> None:
        """On connect callback,resubscribe topic."""
        if result_code in [
            mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
            mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
        ]:
            _LOGGER.error(
                "Connect to YoLink mqtt borker failed, result_code: %s.",
                result_code,
            )
            # try to acquire new access token
            try:
                _LOGGER.info("access token has been expired, acquire a new one.")
                self._mqtt_client.disconnect()
                new_token = asyncio.run_coroutine_threadsafe(
                    self._auth_mgr.check_and_refresh_token(), self.loop
                ).result()
                self._mqtt_client.username_pw_set(new_token, "")
                self._mqtt_client.connect_async(
                    YOLINK_API_MQTT_BROKER, YOLINK_API_MQTT_BROKER_PORT, 60
                )
                return
            except Exception:
                _LOGGER.error("acquire new access token failed!")

        if result_code == mqtt.CONNACK_ACCEPTED:
            _LOGGER.info(
                "YoLink mqtt broker connected, receiving data from YoLink cloud message pushing."
            )
        if result_code != mqtt.CONNACK_ACCEPTED:
            _LOGGER.error(
                "Unable to connect to the MQTT broker: %s",
                mqtt.connack_string(result_code),
            )
            return
        # subscribe to home message topic with qos 0.
        _mqttc.subscribe(self._home_topic, 0)

    def _mqtt_on_disconnection(self, _mqttc, _userdata, result_code) -> None:
        """Mqtt disconnected."""
        _LOGGER.error("YoLink mqtt broker disconnected, result_code: %s", result_code)

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
                self._message_listener.on_message_receive(data)
            except ValidationError:
                # ignore invalidate message
                _LOGGER.debug("Message invalidate.")
