import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import MediaForgeToolError, MediaSearchNoResults
from app.models.playlist import ResolvedMediaCandidate, Track, TrackResolutionStatus
from app.services.media_search import MediaSearchProviderRegistry, TrackQuery

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedTrack:
    track: Track
    candidates: list[ResolvedMediaCandidate]


class MediaResolutionService:
    def __init__(
        self,
        session: Session,
        registry: MediaSearchProviderRegistry,
    ) -> None:
        self.session = session
        self.registry = registry

    def resolve_track(
        self,
        track: Track,
        *,
        provider_key: str,
        limit: int,
    ) -> ResolvedTrack:
        provider = self.registry.get(provider_key)
        track.transition_resolution_to(TrackResolutionStatus.searching)
        self.session.commit()
        self.session.refresh(track)
        logger.info(
            "Media search started",
            extra={
                "event": "media_search_started",
                "playlist_id": track.playlist_id,
                "track_id": track.id,
                "provider": provider_key,
            },
        )
        try:
            results = provider.search(_track_query(track), limit=limit)
        except MediaSearchNoResults:
            self._replace_candidates(track, provider_key, [])
            track.transition_resolution_to(TrackResolutionStatus.no_match)
            self.session.commit()
            logger.info(
                "Media search returned no results",
                extra={
                    "event": "media_search_no_results",
                    "playlist_id": track.playlist_id,
                    "track_id": track.id,
                    "provider": provider_key,
                    "error_code": MediaSearchNoResults.code,
                },
            )
            raise
        except MediaForgeToolError as exc:
            track.transition_resolution_to(TrackResolutionStatus.failed)
            self.session.commit()
            logger.warning(
                "Media search failed",
                extra={
                    "event": "media_search_failed",
                    "playlist_id": track.playlist_id,
                    "track_id": track.id,
                    "provider": provider_key,
                    "error_code": exc.code,
                },
            )
            raise

        candidates = self._replace_candidates(track, provider_key, results)
        track.transition_resolution_to(
            TrackResolutionStatus.resolved
            if candidates
            else TrackResolutionStatus.no_match
        )
        self.session.commit()
        self.session.refresh(track)
        logger.info(
            "Media search completed",
            extra={
                "event": "media_search_completed",
                "playlist_id": track.playlist_id,
                "track_id": track.id,
                "provider": provider_key,
                "candidate_count": len(candidates),
            },
        )
        return ResolvedTrack(track=track, candidates=candidates)

    def _replace_candidates(
        self,
        track: Track,
        provider_key: str,
        results: list,
    ) -> list[ResolvedMediaCandidate]:
        existing = self.session.scalars(
            select(ResolvedMediaCandidate)
            .where(
                    ResolvedMediaCandidate.track_id == track.id,
                    ResolvedMediaCandidate.provider_key == provider_key,
            )
            .options(selectinload(ResolvedMediaCandidate.queue_items))
        ).all()
        kept = [candidate for candidate in existing if candidate.queue_items]
        kept_media_ids = {
            candidate.provider_media_id
            for candidate in kept
            if candidate.provider_media_id is not None
        }
        for candidate in existing:
            if candidate not in kept:
                self.session.delete(candidate)
        self.session.flush()
        candidates = [
            ResolvedMediaCandidate(
                track_id=track.id,
                provider_key=result.provider_key,
                provider_media_id=result.provider_media_id,
                source_url=result.source_url,
                title=result.title,
                creator=result.creator,
                duration_seconds=result.duration_seconds,
                thumbnail_url=result.thumbnail_url,
                rank=index + len(kept),
                match_score=result.match_score,
            )
            for index, result in enumerate(results)
            if result.provider_media_id is None or result.provider_media_id not in kept_media_ids
        ]
        self.session.add_all(candidates)
        self.session.flush()
        return [*kept, *candidates]


def _track_query(track: Track) -> TrackQuery:
    return TrackQuery(
        track_id=track.id,
        artist=track.artist,
        title=track.title,
        album=track.album,
        duration_seconds=track.duration_seconds,
    )
