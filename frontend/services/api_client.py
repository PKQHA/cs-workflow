from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, BinaryIO

import requests
import streamlit as st

DEFAULT_API_TIMEOUT_SECONDS = 60


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


def get_frontend_timeout_seconds() -> int:
    raw_value = os.getenv("FRONTEND_API_TIMEOUT_SECONDS", str(DEFAULT_API_TIMEOUT_SECONDS)).strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        timeout = DEFAULT_API_TIMEOUT_SECONDS
    return max(10, timeout)


class BackendApiClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or get_backend_base_url()).rstrip("/")
        self.timeout = timeout or get_frontend_timeout_seconds()
        self.session = requests.Session()

    def get(self, path: str, params: dict[str, Any] | None = None, include_workspace: bool = True) -> Any:
        try:
            response = self.session.get(
                self._url(path),
                params=self._with_workspace(params, include_workspace=include_workspace),
                timeout=self.timeout,
            )
            return self._parse_response(response)
        except requests.Timeout as exc:
            raise ApiClientError(
                f"当前请求处理时间较长，已等待 {self.timeout} 秒。请稍后重试，如持续出现可联系值班客服确认。",
                "REQUEST_TIMEOUT",
            ) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"请求后端失败：{exc}") from exc

    def post(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        include_workspace: bool = True,
    ) -> Any:
        try:
            response = self.session.post(
                self._url(path),
                params=self._with_workspace(params, include_workspace=include_workspace),
                json=payload or {},
                timeout=self.timeout,
            )
            return self._parse_response(response)
        except requests.Timeout as exc:
            raise ApiClientError(
                f"当前请求处理时间较长，已等待 {self.timeout} 秒。请稍后重试，如持续出现可联系值班客服确认。",
                "REQUEST_TIMEOUT",
            ) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"请求后端失败：{exc}") from exc

    def upload_file(
        self,
        path: str,
        file_name: str,
        file_obj: BinaryIO,
        content_type: str,
        params: dict[str, Any] | None = None,
        include_workspace: bool = True,
    ) -> Any:
        try:
            files = {"file": (file_name, file_obj, content_type)}
            response = self.session.post(
                self._url(path),
                params=self._with_workspace(params, include_workspace=include_workspace),
                files=files,
                timeout=self.timeout,
            )
            return self._parse_response(response)
        except requests.Timeout as exc:
            raise ApiClientError(
                f"文件上传耗时较长，已等待 {self.timeout} 秒。请稍后重试，或确认文件与后端服务状态。",
                "REQUEST_TIMEOUT",
            ) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"上传文件失败：{exc}") from exc

    def download_file(self, path: str, params: dict[str, Any] | None = None, include_workspace: bool = True) -> bytes:
        try:
            response = self.session.get(
                self._url(path),
                params=self._with_workspace(params, include_workspace=include_workspace),
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise ApiClientError(
                f"当前请求处理时间较长，已等待 {self.timeout} 秒。请稍后重试，如持续出现可联系值班客服确认。",
                "REQUEST_TIMEOUT",
            ) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"请求后端失败：{exc}") from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError as exc:
                raise ApiClientError(f"文件下载失败，HTTP 状态码：{response.status_code}") from exc
            message = body.get("message") or f"文件下载失败，HTTP 状态码：{response.status_code}"
            raise ApiClientError(message, body.get("error_code"))
        return response.content

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

    @staticmethod
    def _with_workspace(params: dict[str, Any] | None = None, include_workspace: bool = True) -> dict[str, Any] | None:
        merged = dict(params or {})
        if include_workspace:
            workspace_id = str(st.session_state.get("workspace_id") or "").strip()
            if workspace_id and "workspace_id" not in merged:
                merged["workspace_id"] = workspace_id
        return merged or None


def get_api_client() -> BackendApiClient:
    return _get_cached_api_client(get_backend_base_url(), get_frontend_timeout_seconds())


@lru_cache(maxsize=1)
def _get_cached_api_client(base_url: str, timeout: int) -> BackendApiClient:
    return BackendApiClient(base_url=base_url, timeout=timeout)
