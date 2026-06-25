from app.core.exceptions import ExtensionKeyAlreadyRegistered, PlaylistImporterUnknown
from app.services.playlist_import.base import PlaylistImporter


class PlaylistImporterRegistry:
    def __init__(self) -> None:
        self._importers: dict[str, PlaylistImporter] = {}

    def register(self, importer: PlaylistImporter) -> None:
        key = _validated_key(importer.key)
        if key in self._importers:
            raise ExtensionKeyAlreadyRegistered
        self._importers[key] = importer

    def get(self, key: str) -> PlaylistImporter:
        try:
            return self._importers[_validated_key(key)]
        except (KeyError, ValueError) as exc:
            raise PlaylistImporterUnknown from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._importers))


def _validated_key(key: str) -> str:
    normalized = key.strip().casefold()
    if not normalized or normalized != key:
        raise ValueError("Extension keys must already be normalized.")
    return normalized
