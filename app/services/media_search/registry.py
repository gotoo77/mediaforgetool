from app.core.exceptions import ExtensionKeyAlreadyRegistered, MediaSearchProviderUnknown
from app.services.media_search.base import MediaSearchProvider


class MediaSearchProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MediaSearchProvider] = {}

    def register(self, provider: MediaSearchProvider) -> None:
        key = _validated_key(provider.key)
        if key in self._providers:
            raise ExtensionKeyAlreadyRegistered
        self._providers[key] = provider

    def get(self, key: str) -> MediaSearchProvider:
        try:
            return self._providers[_validated_key(key)]
        except (KeyError, ValueError) as exc:
            raise MediaSearchProviderUnknown from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


def _validated_key(key: str) -> str:
    normalized = key.strip().casefold()
    if not normalized or normalized != key:
        raise ValueError("Extension keys must already be normalized.")
    return normalized
