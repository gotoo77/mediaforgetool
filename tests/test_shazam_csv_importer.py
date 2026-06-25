from io import BytesIO
from pathlib import Path

import pytest

from app.core.exceptions import PlaylistImportFileInvalid, PlaylistImportTooManyRows
from app.services.playlist_import.shazam_csv import ShazamCsvImporter
from app.services.track_normalizer import TrackNormalizer

FIXTURES = Path(__file__).parent / "fixtures" / "shazam"


def test_imports_standard_shazam_csv() -> None:
    result = ShazamCsvImporter(max_tracks=10).import_tracks(
        BytesIO((FIXTURES / "basic.csv").read_bytes()),
        filename="My Shazam Tracks.csv",
    )

    assert result.name == "My Shazam Tracks"
    assert len(result.tracks) == 2
    assert result.tracks[0].artist == "M83"
    assert result.tracks[0].duration_seconds == 244
    assert result.tracks[1].duration_seconds == 255
    assert result.issues == ()


def test_accepts_bom_alias_headers_and_semicolon_with_partial_rows() -> None:
    content = b"\xef\xbb\xbf" + (FIXTURES / "partial_semicolon.csv").read_bytes()

    result = ShazamCsvImporter(max_tracks=10).import_tracks(
        BytesIO(content),
        filename="export.csv",
    )

    assert [(track.artist, track.title) for track in result.tracks] == [
        ("Artist One", "Song One (Live)"),
        ("Artiste Deux", "Deuxième chanson"),
    ]
    assert result.tracks[0].raw_artist == "  Artist One  "
    assert result.tracks[0].source_payload["Track Title"] == "  Song   One (Live)  "
    assert [issue.code for issue in result.issues] == [
        "TRACK_METADATA_MISSING",
        "DUPLICATE_TRACK",
    ]


def test_normalizer_preserves_explicit_version_markers() -> None:
    normalized = TrackNormalizer().normalize(
        artist="  Artist\u00a0Name ",
        title="Title   (Remastered 2011)",
        album=" Album ",
    )

    assert normalized.artist == "Artist Name"
    assert normalized.title == "Title (Remastered 2011)"
    assert normalized.album == "Album"


def test_rejects_invalid_encoding_and_missing_columns() -> None:
    importer = ShazamCsvImporter(max_tracks=10)

    with pytest.raises(PlaylistImportFileInvalid):
        importer.import_tracks(BytesIO(b"\xff\xfe"), filename="bad.csv")
    with pytest.raises(PlaylistImportFileInvalid):
        importer.import_tracks(BytesIO(b"Name,Value\nA,B\n"), filename="bad.csv")


def test_rejects_more_source_rows_than_configured() -> None:
    importer = ShazamCsvImporter(max_tracks=2)
    content = BytesIO(b"Title,Artist\nOne,A\nTwo,B\nThree,C\n")

    with pytest.raises(PlaylistImportTooManyRows):
        importer.import_tracks(content, filename="large.csv")
