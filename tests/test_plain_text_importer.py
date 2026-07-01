from io import BytesIO

import pytest

from app.core.exceptions import PlaylistImportFileInvalid, PlaylistImportTooManyRows
from app.services.playlist_import.plain_text import PlainTextImporter


def test_plain_text_importer_imports_tracks_and_reports_line_issues() -> None:
    importer = PlainTextImporter(max_tracks=10)
    content = (
        "# ignored comment\n"
        "M83 - Midnight City\n"
        "\n"
        "No separator\n"
        "Artist - \n"
        "M83 - Midnight City\n"
        "Artiste Deux - Deuxième chanson\n"
        "Artist - Title - Extra\n"
    ).encode()

    result = importer.import_tracks(BytesIO(content), filename="favorites.txt")

    assert result.name == "favorites"
    assert [(track.artist, track.title, track.source_payload) for track in result.tracks] == [
        ("M83", "Midnight City", {"line": 2}),
        ("Artiste Deux", "Deuxième chanson", {"line": 7}),
    ]
    assert [(issue.row_number, issue.code) for issue in result.issues] == [
        (4, "TEXT_TRACK_FORMAT_INVALID"),
        (5, "TEXT_TRACK_FORMAT_INVALID"),
        (6, "DUPLICATE_TRACK"),
        (8, "TEXT_TRACK_FORMAT_INVALID"),
    ]


def test_plain_text_importer_rejects_invalid_encoding() -> None:
    importer = PlainTextImporter(max_tracks=10)

    with pytest.raises(PlaylistImportFileInvalid):
        importer.import_tracks(BytesIO(b"\xff"), filename="tracks.txt")


def test_plain_text_importer_rejects_file_without_valid_tracks() -> None:
    importer = PlainTextImporter(max_tracks=10)

    with pytest.raises(PlaylistImportFileInvalid):
        importer.import_tracks(
            BytesIO(b"# comment\n\nNo separator\n"),
            filename="tracks.txt",
        )


def test_plain_text_importer_applies_max_tracks_to_source_rows() -> None:
    importer = PlainTextImporter(max_tracks=2)

    with pytest.raises(PlaylistImportTooManyRows):
        importer.import_tracks(
            BytesIO(b"A - One\nBad line\nB - Two\n"),
            filename="tracks.txt",
        )
