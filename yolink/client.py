"""YoLink client."""
from typing import Any, Dict

from aiohttp import ClientError, ClientResponse
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from .const import YOLINK_API_GATE, YOLINK_API_GATE_EU, Endpoints
from .auth_mgr import YoLinkAuthMgr
from .exception import YoLinkClientError, YoLinkDeviceDisconnectedError
from .model import BRDP


class YoLinkClient:
    """YoLink client."""

    def __init__(self, auth_mgr: YoLinkAuthMgr) -> None:
        """Init YoLink client"""
        self._auth_mgr = auth_mgr

    async def request(
        self, method: str, url: str, auth_required: bool = True, **kwargs: Any
    ) -> ClientResponse:
        """Proxy Request and add Auth/CV headers."""
        headers = kwargs.pop("headers", {})
        params = kwargs.pop("params", None)
        data = kwargs.pop("data", None)

        # Extra, user supplied values
        extra_headers = kwargs.pop("extra_headers", None)
        extra_params = kwargs.pop("extra_params", None)
        extra_data = kwargs.pop("extra_data", None)
        if auth_required:
            # Ensure token valid
            await self._auth_mgr.check_and_refresh_token()
            # Set auth header
            headers["Authorization"] = self._auth_mgr.http_auth_header()
        # Extend with optionally supplied values
        if extra_headers:
            headers.update(extra_headers)
        if extra_params:
            # Query parameters
            params = params or {}
            params.update(extra_params)
        if extra_data:
            # form encoded post data
            data = data or {}
            data.update(extra_data)
        return await self._auth_mgr.client_session().request(
            method, url, **kwargs, headers=headers, params=params, data=data, timeout=8
        )

    async def post(self, url: str, **kwargs: Any) -> ClientResponse:
        """Call Http Request with POST Method"""
        return await self.request("POST", url, True, **kwargs)

    @retry(
        retry=retry_if_exception_type(YoLinkDeviceDisconnectedError),
        stop=stop_after_attempt(2),
    )
    async def execute(self, endpoint: Endpoints, bsdp: Dict, **kwargs: Any) -> BRDP:
        """Call YoLink Api"""
        try:
            api_gate = (
                YOLINK_API_GATE_EU if endpoint == Endpoints.EU else YOLINK_API_GATE
            )
            yl_resp = await self.post(api_gate, json=bsdp, **kwargs)
            yl_resp.raise_for_status()
            _yl_body = await yl_resp.text()
            brdp = BRDP.parse_raw(_yl_body)
            brdp.check_response()
        except ClientError as client_err:
            raise YoLinkClientError(
                "-1003", "yolink client request failed!"
            ) from client_err
        except YoLinkClientError as yl_client_err:
            raise yl_client_err
        return brdp
