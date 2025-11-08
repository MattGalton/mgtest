from __future__ import annotations

import json
import logging
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.retry import retry

logger = logging.getLogger(__name__)


class HttpRequestInstance(TestInstance):
    def run(self, resources):
        status, headers, body = retry(
            self._request_and_assert,
            timeout=self.definition.timeout,
            interval=self.definition.interval,
        )
        self.outputs.status = status
        self.outputs.headers = headers
        self.outputs.body = body
        try:
            self.outputs.json_data = json.loads(body)
        except json.JSONDecodeError:
            self.outputs.json_data = None

    def _request_and_assert(self):
        logger.debug("Making HTTP %s request", self.definition.method)
        headers = dict(self.definition.headers)
        data = self.definition.body.encode() if self.definition.body is not None else None
        if self.definition.json_body is not None:
            data = json.dumps(self.definition.json_body).encode()
            headers.setdefault("Content-Type", "application/json")
        request = Request(
            self.definition.url,
            data=data,
            headers=headers,
            method=self.definition.method,
        )
        try:
            with urlopen(request, timeout=self.definition.interval) as response:
                status = response.status
                response_headers = dict(response.headers)
                body = response.read().decode()
        except HTTPError as response:
            status = response.code
            response_headers = dict(response.headers)
            body = response.read().decode()
        expected = self.definition.expected_status
        accepted = {expected} if isinstance(expected, int) else set(expected)
        assert status in accepted, f"Expected HTTP {sorted(accepted)}, got {status}: {body}"
        if self.definition.body_contains is not None:
            assert self.definition.body_contains in body, body
        if self.definition.json_equals is not None:
            assert json.loads(body) == self.definition.json_equals, body
        return status, response_headers, body
