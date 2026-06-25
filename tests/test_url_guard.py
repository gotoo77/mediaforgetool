import pytest

from app.core.exceptions import InvalidMediaUrl
from app.services.url_guard import validate_public_media_url


def test_url_guard_rejects_loopback_ip() -> None:
    with pytest.raises(InvalidMediaUrl):
        validate_public_media_url("http://127.0.0.1/media", 2048)


def test_url_guard_rejects_url_credentials() -> None:
    with pytest.raises(InvalidMediaUrl):
        validate_public_media_url("https://user:secret@example.com/media", 2048)
