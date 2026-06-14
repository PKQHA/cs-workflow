from __future__ import annotations

import os
from typing import Any, BinaryIO

import requests


class ApiClientError(Exception):
    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def get_backend_base_url() -> str:
    base_url = os.getenv("BACKEND_BASE_URL", "").strip()
    if not base_url:
        raise ApiClientError("未配置 BACKEND_BASE_URL，请先设置后端地址后再启动前端。")
    return base_url.rstrip("/")


class BackendApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 15) -> None:
        self.base_url = (base_url or get_backend_base_url()).rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.get(self._url(path), params=params, timeout=self.timeout)
            return self._parse_response(response)
        except requests.RequestException as exc:
            raise ApiClientError(f"请求后端失败：{exc}") from exc

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.post(self._url(path), json=payload or {}, timeout=self.timeout)
            return self._parse_response(response)
        except requests.RequestException as exc:
            raise ApiClientError(f"请求后端失败：{exc}") from exc

    def upload_file(self, path: str, file_name: str, file_obj: BinaryIO, content_type: str) -> Any:
        try:
            files = {"file": (file_name, file_obj, content_type)}
            response = requests.post(self._url(path), files=files, timeout=self.timeout)
            return self._parse_response(response)
        except requests.RequestException as exc:
            raise ApiClientError(f"上传文件失败：{exc}") from exc

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _parse_response(response: requests.Response) -> Any:
        try:
            body = response.json()
        except ValueError as exc:
            raise ApiClientError(f"后端返回了非 JSON 响应，HTTP 状态码：{response.status_code}") from exc

        if response.status_code >= 400 or body.get("success") is False:
            message = body.get("message") or f"请求失败，HTTP 状态码：{response.status_code}"
            raise ApiClientError(message, body.get("error_code"))
        return body.get("data")


def get_api_client() -> BackendApiClient:
    return BackendApiClient()
