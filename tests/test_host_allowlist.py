import pytest

from server.app import served_host_from_environment
from server.constants import WILDCARD_BIND_ADDRESSES
from server.host_allowlist import (
    HostAllowlistMiddleware,
    UnsupportedServedHostError,
    allowed_hosts,
    browser_url,
    normalise_served_host,
)

_LOOPBACK = {"localhost:8000", "127.0.0.1:8000"}


@pytest.mark.parametrize(
    ("served_host", "expected"),
    [
        ("127.0.0.1", _LOOPBACK),
        ("localhost", _LOOPBACK),
        ("::1", _LOOPBACK | {"[::1]:8000"}),
        *[(wildcard, _LOOPBACK) for wildcard in sorted(WILDCARD_BIND_ADDRESSES)],
        ("192.168.1.20", {"192.168.1.20:8000"}),
        ("Game.Lan", {"game.lan:8000"}),
        # G4AL_HOST set but empty: the default bind address.
        ("", _LOOPBACK),
        ("[::1]", _LOOPBACK | {"[::1]:8000"}),
        ("0:0:0:0:0:0:0:1", _LOOPBACK | {"[::1]:8000"}),
        ("0:0:0:0:0:0:0:0", _LOOPBACK),
        ("FE80:0:0:0:0:0:0:1", {"[fe80::1]:8000"}),
        # A zone id: no browser sends it in Host, so the server refuses to start.
        ("fe80::1%en0", UnsupportedServedHostError),
        ("[fe80::1%25en0]", UnsupportedServedHostError),
    ],
)
def test_allowed_hosts_follow_the_served_address(
    served_host: str, expected: set[str] | type[Exception]
) -> None:
    if isinstance(expected, set):
        assert allowed_hosts(normalise_served_host(served_host)) == expected
    else:
        with pytest.raises(expected, match="zone id is not supported"):
            normalise_served_host(served_host)


@pytest.mark.parametrize(
    ("served_host", "expected"),
    [
        ("127.0.0.1", "http://localhost:8000"),
        ("::1", "http://localhost:8000"),
        *[(wildcard, "http://localhost:8000") for wildcard in sorted(WILDCARD_BIND_ADDRESSES)],
        ("192.168.1.20", "http://192.168.1.20:8000"),
        ("fe80::1", "http://[fe80::1]:8000"),
    ],
)
def test_the_browser_url_is_an_allowed_host(served_host: str, expected: str) -> None:
    url = browser_url(normalise_served_host(served_host))

    assert url == expected
    assert url.removeprefix("http://") in allowed_hosts(normalise_served_host(served_host))


def test_a_request_without_host_is_refused() -> None:
    # HTTP/1.0 may omit Host; the test client always sends one, so drive the middleware.
    statuses: list[str] = []
    middleware = HostAllowlistMiddleware(
        lambda environ, start_response: [b"served"], allowed_hosts("127.0.0.1")
    )

    body = middleware({}, lambda status, headers, exc_info=None: statuses.append(status))

    assert (statuses, list(body)) == (["403 FORBIDDEN"], [b'{"error": "host not allowed"}'])


def test_a_zone_id_in_g4al_host_stops_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("G4AL_HOST", "fe80::1%en0")

    with pytest.raises(SystemExit, match=r"fe80::1%en0.*zone id is not supported"):
        served_host_from_environment()
