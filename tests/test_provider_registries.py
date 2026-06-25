from io import BytesIO

import pytest

from app.core.exceptions import (
    ExtensionKeyAlreadyRegistered,
    MediaSearchProviderUnknown,
    PlaylistImporterUnknown,
)
from app.services.media_search import (
    MediaSearchProviderRegistry,
    SearchCandidate,
    TrackQuery,
)
from app.services.playlist_import import (
    ImportedTrack,
    ImportResult,
    PlaylistImporterRegistry,
)


class FakeImporter:
    key = "fake"

    def import_tracks(
        self,
        content: BytesIO,
        *,
        filename: str | None,
    ) -> ImportResult:
        assert content.read() == b"track"
        return ImportResult(
            name=filename or "Imported",
            tracks=(ImportedTrack(position=0, artist="Artist", title="Title"),),
        )


class FakeProvider:
    key = "fake"

    def __init__(self) -> None:
        self.searches: list[TrackQuery] = []

    def search(self, track: TrackQuery, *, limit: int) -> list[SearchCandidate]:
        self.searches.append(track)
        return [
            SearchCandidate(
                provider_key=self.key,
                provider_media_id="media-1",
                source_url="https://example.com/media-1",
                title=f"{track.artist} - {track.title}",
                rank=0,
            )
        ][:limit]


def test_importer_registry_resolves_registered_importer() -> None:
    registry = PlaylistImporterRegistry()
    importer = FakeImporter()
    registry.register(importer)

    result = registry.get("fake").import_tracks(BytesIO(b"track"), filename="list.csv")

    assert registry.keys() == ("fake",)
    assert result.name == "list.csv"
    assert result.tracks[0].artist == "Artist"


def test_provider_registry_resolves_without_creating_jobs() -> None:
    registry = MediaSearchProviderRegistry()
    provider = FakeProvider()
    registry.register(provider)
    query = TrackQuery(track_id="track-1", artist="Artist", title="Title")

    candidates = registry.get("fake").search(query, limit=5)

    assert registry.keys() == ("fake",)
    assert provider.searches == [query]
    assert candidates[0].provider_media_id == "media-1"


@pytest.mark.parametrize(
    ("registry", "extension"),
    [
        (PlaylistImporterRegistry(), FakeImporter()),
        (MediaSearchProviderRegistry(), FakeProvider()),
    ],
)
def test_registries_reject_duplicate_keys(registry: object, extension: object) -> None:
    registry.register(extension)
    with pytest.raises(ExtensionKeyAlreadyRegistered):
        registry.register(extension)


def test_registries_report_unknown_keys() -> None:
    with pytest.raises(PlaylistImporterUnknown):
        PlaylistImporterRegistry().get("missing")
    with pytest.raises(MediaSearchProviderUnknown):
        MediaSearchProviderRegistry().get("missing")
