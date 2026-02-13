from __future__ import annotations

import logging
import os
from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class OpenObserveError(Exception):
    """Base exception for OpenObserve client errors."""

    pass


class ConfigurationError(OpenObserveError):
    """Raised when configuration is invalid."""

    pass


class AuthenticationError(OpenObserveError):
    """Raised when authentication fails."""

    pass


class OpenObserveConnectionError(OpenObserveError):
    """Raised when connection to OpenObserve fails."""

    pass


class APIError(OpenObserveError):
    """Raised when OpenObserve API returns an error."""

    def __init__(
        self, message: str, status_code: int | None = None, response_text: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class OpenObserveClient:
    def __init__(
        self,
        base_url: str | None = None,
        org: str | None = None,
        email: str | None = None,
        password: str | None = None,
        access_key: str | None = None,
        timeout_s: int = 30,
    ) -> None:
        self.base_url = (base_url or os.getenv("ZO_BASE_URL", "http://127.0.0.1:5080")).rstrip("/")
        self.org = org or os.getenv("ZO_ORG", "default")
        self.email = email or os.getenv("ZO_ROOT_USER_EMAIL")
        self.password = password or os.getenv("ZO_ROOT_USER_PASSWORD")
        self.access_key = access_key or os.getenv("ZO_ACCESS_KEY")
        self.timeout_s = timeout_s

        # Validate configuration
        if not self.base_url:
            raise ConfigurationError("base_url is required")

        if not self.org:
            raise ConfigurationError("org is required")

        if not self.access_key and not (self.email and self.password):
            raise ConfigurationError(
                "Authentication required: provide either access_key or both email and password"
            )

        if timeout_s <= 0:
            raise ConfigurationError(f"timeout_s must be positive, got {timeout_s}")

        logger.debug(
            "OpenObserveClient initialized: base_url=%s, org=%s, timeout=%ds",
            self.base_url,
            self.org,
            self.timeout_s,
        )

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_key:
            headers["Authorization"] = f"Basic {self.access_key}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        params = kwargs.get("params")
        json_body = kwargs.get("json")

        # Log request with SQL if present
        if (
            isinstance(json_body, dict)
            and "query" in json_body
            and isinstance(json_body["query"], dict)
        ):
            query = json_body["query"]
            sql = query.get("sql")
            if sql is not None:
                logger.info("OpenObserve request: %s %s sql=%s params=%s", method, url, sql, params)
            else:
                logger.info("OpenObserve request: %s %s params=%s", method, url, params)
        else:
            logger.info("OpenObserve request: %s %s params=%s", method, url, params)

        logger.debug("Request details: url=%s, timeout=%ds", url, self.timeout_s)

        headers = dict(self._auth_headers())
        headers.update(kwargs.pop("headers", {}))
        auth = None if self.access_key else (self.email, self.password)

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                auth=auth,
                timeout=self.timeout_s,
                **kwargs,
            )
        except Timeout as e:
            logger.error("Request timeout after %ds: %s %s", self.timeout_s, method, url)
            raise OpenObserveConnectionError(
                f"Request to OpenObserve timed out after {self.timeout_s}s. "
                "Consider increasing ZO_TIMEOUT or check network connectivity."
            ) from e
        except RequestsConnectionError as e:
            logger.error("Connection error: %s %s - %s", method, url, e)
            raise OpenObserveConnectionError(
                f"Failed to connect to OpenObserve at {self.base_url}. "
                "Verify the URL and that OpenObserve is running."
            ) from e
        except RequestException as e:
            logger.error("Request error: %s %s - %s", method, url, e)
            raise OpenObserveConnectionError(f"Request failed: {e}") from e

        # Handle HTTP errors
        if not response.ok:
            logger.error(
                "OpenObserve API error: %s %s -> HTTP %d: %s",
                method,
                url,
                response.status_code,
                response.text[:200],
            )

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Verify ZO_ACCESS_KEY or ZO_ROOT_USER_EMAIL/PASSWORD credentials."
                )
            elif response.status_code == 403:
                raise AuthenticationError(
                    f"Access forbidden. User may not have permissions for organization '{self.org}'."
                )
            elif response.status_code == 404:
                raise APIError(
                    f"Resource not found: {path}. Verify organization name and resource path.",
                    status_code=404,
                    response_text=response.text,
                )
            elif response.status_code >= 500:
                raise APIError(
                    f"OpenObserve server error (HTTP {response.status_code}). "
                    "Check OpenObserve server logs for details.",
                    status_code=response.status_code,
                    response_text=response.text,
                )
            else:
                raise APIError(
                    f"API request failed (HTTP {response.status_code}): {response.text}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

        logger.debug("Request successful: %s %s -> HTTP %d", method, url, response.status_code)
        return response

    def search(
        self,
        sql: str,
        start_time_micros: int,
        end_time_micros: int,
        size: int,
        offset: int,
    ) -> dict[str, Any]:
        payload = {
            "query": {
                "sql": sql,
                "from": offset,
                "size": size,
                "start_time": start_time_micros,
                "end_time": end_time_micros,
            }
        }
        return self._request("POST", f"api/{self.org}/_search", json=payload).json()

    def list_streams(self) -> Any:
        return self._request("GET", f"api/{self.org}/streams").json()

    def get_stream_schema(self, stream: str) -> dict[str, Any]:
        return self._request("GET", f"api/{self.org}/streams/{stream}/schema").json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()
