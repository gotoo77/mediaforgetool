from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.models.studio import (
    MediaAsset,
    MediaAssetKind,
    MediaAssetOrigin,
    MediaEditJob,
    MediaEditJobInput,
    MediaEditJobOutput,
    MediaEditOperation,
    MediaEditStatus,
)


def _session(tmp_path: Path) -> Session:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'studio.db'}")
    engine = build_engine(settings)
    create_schema(engine)
    return build_session_factory(engine)()


def test_studio_domain_persists_asset_job_and_inputs(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        video = MediaAsset(
            display_name="Concert video",
            relative_path="assets/concert.mp4",
            kind=MediaAssetKind.video,
            origin=MediaAssetOrigin.upload,
            container_format="mov,mp4,m4a,3gp,3g2,mj2",
            mime_type="video/mp4",
            size_bytes=1024,
            duration_seconds=120.5,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac",
        )
        audio = MediaAsset(
            display_name="Better audio",
            relative_path="assets/audio.m4a",
            kind=MediaAssetKind.audio,
            origin=MediaAssetOrigin.upload,
            size_bytes=512,
            duration_seconds=120.5,
            audio_codec="aac",
        )
        job = MediaEditJob(
            operation=MediaEditOperation.replace_audio,
            output_name="concert-remux.mp4",
            options={"audio_offset_seconds": 0, "duration_mode": "shortest"},
            inputs=[
                MediaEditJobInput(asset=video, role="video", position=0),
                MediaEditJobInput(asset=audio, role="audio", position=1),
            ],
        )
        session.add(job)
        session.commit()
        session.expire_all()

        stored = session.get(MediaEditJob, job.id)
        assert stored is not None
        assert stored.status is MediaEditStatus.queued
        assert [item.role for item in stored.inputs] == ["video", "audio"]
        assert stored.inputs[0].asset.kind is MediaAssetKind.video


def test_studio_domain_persists_multiple_outputs(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        source = MediaAsset(
            display_name="Source",
            relative_path="assets/source.mp4",
            kind=MediaAssetKind.video,
            origin=MediaAssetOrigin.upload,
            size_bytes=1024,
        )
        part1 = MediaAsset(
            display_name="Part 1",
            relative_path="studio/job/part1.mp4",
            kind=MediaAssetKind.video,
            origin=MediaAssetOrigin.studio_output,
            size_bytes=512,
        )
        part2 = MediaAsset(
            display_name="Part 2",
            relative_path="studio/job/part2.mp4",
            kind=MediaAssetKind.video,
            origin=MediaAssetOrigin.studio_output,
            size_bytes=512,
        )
        job = MediaEditJob(
            operation=MediaEditOperation.split_media,
            output_name="source-split",
            inputs=[MediaEditJobInput(asset=source, role="source", position=0)],
            outputs=[
                MediaEditJobOutput(asset=part1, role="part1", position=0),
                MediaEditJobOutput(asset=part2, role="part2", position=1),
            ],
            output_asset=part1,
        )

        session.add(job)
        session.commit()
        session.expire_all()

        stored = session.get(MediaEditJob, job.id)
        assert stored is not None
        assert [output.role for output in stored.outputs] == ["part1", "part2"]
        assert stored.output_asset_id == part1.id


def test_studio_status_transitions_are_explicit() -> None:
    job = MediaEditJob(
        operation=MediaEditOperation.split_media,
        output_name="split-output",
    )

    job.transition_to(MediaEditStatus.probing)
    job.transition_to(MediaEditStatus.processing)
    job.transition_to(MediaEditStatus.completed)

    with pytest.raises(ValueError, match="completed -> failed"):
        job.transition_to(MediaEditStatus.failed)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: MediaAsset(
                display_name=" ",
                relative_path="assets/file.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=1,
            ),
            "display_name",
        ),
        (
            lambda: MediaAsset(
                display_name="File",
                relative_path="../outside.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=1,
            ),
            "relative_path",
        ),
        (
            lambda: MediaAsset(
                display_name="File",
                relative_path="assets/file.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=-1,
            ),
            "size_bytes",
        ),
        (
            lambda: MediaEditJob(
                operation=MediaEditOperation.remove_audio,
                output_name="out.mp4",
                progress_percent=101,
            ),
            "progress_percent",
        ),
        (
            lambda: MediaEditJobInput(
                asset_id="asset",
                role="video",
                position=-1,
            ),
            "position",
        ),
    ],
)
def test_studio_domain_rejects_invalid_values(factory: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_asset_relative_path_is_unique(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        session.add_all(
            [
                MediaAsset(
                    display_name="One",
                    relative_path="assets/same.mp4",
                    kind=MediaAssetKind.video,
                    origin=MediaAssetOrigin.upload,
                    size_bytes=1,
                ),
                MediaAsset(
                    display_name="Two",
                    relative_path="assets/same.mp4",
                    kind=MediaAssetKind.video,
                    origin=MediaAssetOrigin.upload,
                    size_bytes=1,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_create_schema_adds_studio_tables_to_existing_database(tmp_path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'existing.db'}")
    engine = build_engine(settings)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE download_jobs (id VARCHAR(36) PRIMARY KEY)"))

    create_schema(engine)

    tables = set(inspect(engine).get_table_names())
    assert {
        "download_jobs",
        "media_assets",
        "media_edit_jobs",
        "media_edit_job_inputs",
        "media_edit_job_outputs",
    } <= tables
