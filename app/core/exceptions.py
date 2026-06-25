class MediaForgeToolError(Exception):
    code = "MEDIAFORGETOOL_ERROR"
    public_message = "The media job could not be completed."


class InvalidMediaUrl(MediaForgeToolError):
    code = "INVALID_URL"
    public_message = "Provide a public HTTP or HTTPS media URL."


class MediaTooLong(MediaForgeToolError):
    code = "MEDIA_TOO_LONG"
    public_message = "The media duration exceeds this instance limit."


class MediaTooLarge(MediaForgeToolError):
    code = "MEDIA_TOO_LARGE"
    public_message = "The media output exceeds this instance limit."


class SegmentOutOfBounds(MediaForgeToolError):
    code = "SEGMENT_OUT_OF_BOUNDS"
    public_message = "The requested media segment is outside the source duration."


class DownloadFailed(MediaForgeToolError):
    code = "DOWNLOAD_FAILED"
    public_message = "The media could not be downloaded from its source."


class SourceAuthenticationRequired(MediaForgeToolError):
    code = "SOURCE_AUTH_REQUIRED"
    public_message = "This source requires authentication before it can be downloaded."


class SourceNoStreams(MediaForgeToolError):
    code = "SOURCE_NO_STREAMS"
    public_message = "This source did not expose any downloadable stream without credentials."


class CookiesUnavailable(MediaForgeToolError):
    code = "COOKIES_UNAVAILABLE"
    public_message = "The configured cookies source is unavailable."


class OutputFormatUnavailable(MediaForgeToolError):
    code = "OUTPUT_FORMAT_UNAVAILABLE"
    public_message = "No compatible output format fits this request and instance limits."


class ConversionFailed(MediaForgeToolError):
    code = "CONVERSION_FAILED"
    public_message = "The media could not be converted to the requested format."


class JobTimeout(MediaForgeToolError):
    code = "JOB_TIMEOUT"
    public_message = "The media job exceeded this instance timeout."


class JobPaused(MediaForgeToolError):
    code = "JOB_PAUSED"
    public_message = "The media job was paused."


class PlaylistImporterUnknown(MediaForgeToolError):
    code = "PLAYLIST_IMPORTER_UNKNOWN"
    public_message = "The requested playlist importer is unavailable."


class MediaSearchProviderUnknown(MediaForgeToolError):
    code = "MEDIA_SEARCH_PROVIDER_UNKNOWN"
    public_message = "The requested media search provider is unavailable."


class ExtensionKeyAlreadyRegistered(MediaForgeToolError):
    code = "EXTENSION_KEY_ALREADY_REGISTERED"
    public_message = "An extension with this identifier is already registered."
