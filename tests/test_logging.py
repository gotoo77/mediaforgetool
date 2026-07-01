import json
import logging

from app.core.logging import JsonFormatter, reset_request_id, set_request_id


def test_json_formatter_includes_standard_fields() -> None:
    record = logging.LogRecord(
        name="mediaforgetool.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="App started",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "mediaforgetool.test"
    assert payload["message"] == "App started"
    assert "timestamp" in payload


def test_json_formatter_includes_operational_extra_fields() -> None:
    record = logging.LogRecord(
        name="mediaforgetool.jobs",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="Job failed",
        args=(),
        exc_info=None,
    )
    record.event = "job_failed"
    record.job_id = "job-1"
    record.status = "failed"
    record.error_code = "DOWNLOAD_FAILED"
    record.platform = "Example"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "job_failed"
    assert payload["job_id"] == "job-1"
    assert payload["status"] == "failed"
    assert payload["error_code"] == "DOWNLOAD_FAILED"
    assert payload["platform"] == "Example"


def test_json_formatter_includes_playlist_import_context() -> None:
    record = logging.LogRecord(
        name="mediaforgetool.playlists",
        level=logging.INFO,
        pathname=__file__,
        lineno=25,
        msg="Playlist imported",
        args=(),
        exc_info=None,
    )
    record.event = "playlist_import_completed"
    record.playlist_id = "playlist-1"
    record.importer = "shazam_csv"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "playlist_import_completed"
    assert payload["playlist_id"] == "playlist-1"
    assert payload["importer"] == "shazam_csv"


def test_json_formatter_includes_playlist_resolution_context() -> None:
    record = logging.LogRecord(
        name="mediaforgetool.playlists",
        level=logging.INFO,
        pathname=__file__,
        lineno=28,
        msg="Candidate selected",
        args=(),
        exc_info=None,
    )
    record.event = "media_candidate_selected"
    record.playlist_id = "playlist-1"
    record.track_id = "track-1"
    record.candidate_id = "candidate-1"
    record.queue_item_id = "queue-item-1"
    record.job_id = "job-1"
    record.provider = "youtube"
    record.row_number = 4

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "media_candidate_selected"
    assert payload["playlist_id"] == "playlist-1"
    assert payload["track_id"] == "track-1"
    assert payload["candidate_id"] == "candidate-1"
    assert payload["queue_item_id"] == "queue-item-1"
    assert payload["job_id"] == "job-1"
    assert payload["provider"] == "youtube"
    assert payload["row_number"] == 4


def test_json_formatter_includes_context_request_id() -> None:
    token = set_request_id("request-1")
    try:
        record = logging.LogRecord(
            name="mediaforgetool.request",
            level=logging.INFO,
            pathname=__file__,
            lineno=30,
            msg="Request handled",
            args=(),
            exc_info=None,
        )

        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "request-1"
