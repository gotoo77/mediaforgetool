import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.exceptions import InvalidMediaUrl


def _is_blocked_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_public_media_url(url: str, max_length: int) -> str:
    if len(url) > max_length:
        raise InvalidMediaUrl

    parts = urlsplit(url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise InvalidMediaUrl

    if parts.hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise InvalidMediaUrl

    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise InvalidMediaUrl from exc

    if any(_is_blocked_address(item[4][0]) for item in addresses):
        raise InvalidMediaUrl
    return url
