"""Refuse requests whose `Host` header is not an address the server is served at.

Guards against DNS rebinding: a page whose domain re-resolves to this server sends
its own domain as `Host`, and an `Origin` equal to it, so origin checks accept it.
"""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

from server.constants import (
    DEFAULT_SERVED_HOST,
    LOOPBACK_BIND_ADDRESSES,
    LOOPBACK_HOST_NAMES,
    SERVER_PORT,
    WILDCARD_BIND_ADDRESSES,
)

if TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment

_REFUSAL_BODY = json.dumps({"error": "host not allowed"}).encode()


class UnsupportedServedHostError(ValueError):
    """`G4AL_HOST` names an address no browser can put in a `Host` header."""


def normalise_served_host(raw: str) -> str:
    """Bind address read from `G4AL_HOST`, in the form `allowed_hosts` expects.

    Surrounding brackets are stripped and an IP address is written in its compressed
    form (`0:0:0:0:0:0:0:1` → `::1`); a name is lowercased. An empty value means
    `DEFAULT_SERVED_HOST`. Raises `UnsupportedServedHostError` on an IPv6 zone id
    (`fe80::1%en0`).
    """
    host = raw.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host:
        return DEFAULT_SERVED_HOST
    if "%" in host:
        # Browsers percent-encode or drop a zone id, so no Host would ever match.
        raise UnsupportedServedHostError(
            f"G4AL_HOST={raw!r}: a link-local address with a zone id is not supported;"
            " use a global or loopback address"
        )
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return host.lower()


def allowed_hosts(served_host: str) -> frozenset[str]:
    """`Host` values (`name:port`, lowercase) a browser sends to the server bound to ``served_host``.

    ``served_host`` comes from `normalise_served_host`.
    The bind address itself, unless it is a wildcard, plus `localhost` and `127.0.0.1`
    when the server also listens on loopback.
    """
    return frozenset(f"{name}:{SERVER_PORT}" for name in _browser_host_names(served_host))


def browser_url(served_host: str) -> str:
    """URL a player opens to reach the server bound to ``served_host``: an allowed host.

    `localhost` when the server listens on loopback, the bind address otherwise.
    """
    return f"http://{_browser_host_names(served_host)[0]}:{SERVER_PORT}"


def _browser_host_names(served_host: str) -> list[str]:
    """Host names a browser may use for ``served_host``, the one to show first."""
    names = list(LOOPBACK_HOST_NAMES) if served_host in LOOPBACK_BIND_ADDRESSES else []
    if served_host not in WILDCARD_BIND_ADDRESSES:
        names.append(f"[{served_host}]" if ":" in served_host else served_host)
    return list(dict.fromkeys(names))


class HostAllowlistMiddleware:
    """WSGI middleware answering 403 to a request whose `Host` is not allowed.

    Wraps the whole app, Socket.IO included: Engine.IO checks `Origin` only when the
    request has one, and a same-origin polling request has none.
    """

    def __init__(self, wsgi_app: WSGIApplication, hosts: frozenset[str]) -> None:
        self._wsgi_app = wsgi_app
        self._hosts = hosts

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        host = str(environ.get("HTTP_HOST", "")).lower()
        if host in self._hosts:
            return self._wsgi_app(environ, start_response)
        start_response(
            "403 FORBIDDEN",
            [("Content-Type", "application/json"), ("Content-Length", str(len(_REFUSAL_BODY)))],
        )
        return [_REFUSAL_BODY]
