from typing import Any

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.http_request.instance import HttpRequestInstance


class HttpRequest(TestSpec):
    """Poll an HTTP endpoint and assert its status, body, or JSON response."""

    url: str = Field(description="HTTP endpoint to request.")
    method: str = Field(default="GET", description="HTTP method to send.")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP request headers.")
    body: str | None = Field(default=None, description="Text request body.")
    json_body: Any | None = Field(default=None, description="JSON value used as the request body.")
    expected_status: int | list[int] = Field(
        default=200, description="Accepted HTTP status code or codes."
    )
    body_contains: str | None = Field(
        default=None, description="Text that must occur in the response body."
    )
    json_equals: Any | None = Field(
        default=None, description="JSON value required for the response body."
    )
    timeout: float = Field(
        default=10.0, gt=0, description="Maximum seconds to wait for a passing response."
    )
    interval: float = Field(
        default=0.1, gt=0, description="Seconds between requests while waiting."
    )

    class Output(BaseModel):
        status: int = Field(default=0, description="HTTP status returned by the response.")
        headers: dict[str, str] = Field(default_factory=dict, description="Response headers.")
        body: str = Field(default="", description="Response body as text.")
        json_data: Any | None = Field(
            default=None, description="Decoded JSON response body, if present."
        )

    def create_instance(self) -> HttpRequestInstance:
        return HttpRequestInstance(self)
