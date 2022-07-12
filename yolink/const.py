"""Const for YoLink Client."""
YOLINK_HOST = "api.yosmart.com"
YOLINK_HTTP_HOST = f"https://{YOLINK_HOST}"
OAUTH2_AUTHORIZE = f"{YOLINK_HTTP_HOST}/oauth/v2/authorization.htm"
OAUTH2_TOKEN = f"{YOLINK_HTTP_HOST}/open/yolink/token"
YOLINK_API_GATE = f"{YOLINK_HTTP_HOST}/open/yolink/v2/api"
YOLINK_API_MQTT_BROKER = YOLINK_HOST
YOLINK_API_MQTT_BROKER_POER = 8003

ATTR_DEVICE_ID = "deviceId"
ATTR_DEVICE_NAME = "name"
ATTR_DEVICE_TYPE = "type"
ATTR_DEVICE_TOKEN = "token"
ATTR_DEVICE_PARENT_ID = "parentDeviceId"
