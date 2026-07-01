const form = document.querySelector("#download-form");
const submitButton = document.querySelector("#submit-button");
const currentJob = document.querySelector("#current-job");
const jobTitle = document.querySelector("#job-title");
const jobStatus = document.querySelector("#job-status");
const jobProgress = document.querySelector("#job-progress");
const jobDetails = document.querySelector("#job-details");
const jobError = document.querySelector("#job-error");
const jobPause = document.querySelector("#job-pause");
const jobResume = document.querySelector("#job-resume");
const jobDownload = document.querySelector("#job-download");
const batchJobs = document.querySelector("#batch-jobs");
const batchStatus = document.querySelector("#batch-status");
const batchProgress = document.querySelector("#batch-progress");
const batchList = document.querySelector("#batch-list");
const historyList = document.querySelector("#history-list");
const inspectButton = document.querySelector("#inspect-button");
const mediaEstimate = document.querySelector("#media-estimate");
const inspectionMessage = document.querySelector("#inspection-message");
const mediaInspection = document.querySelector("#media-inspection");
const mediaThumbnail = document.querySelector("#media-thumbnail");
const mediaTitle = document.querySelector("#media-title");
const mediaMetadata = document.querySelector("#media-metadata");
const mediaUrl = document.querySelector("#media-url");
const resolutionField = document.querySelector("#resolution-field");
const resolutionSelect = document.querySelector("#resolution-select");
const audioQualityField = document.querySelector("#audio-quality-field");
const audioQualitySelect = document.querySelector("#audio-quality-select");
const segmentToggle = document.querySelector("#segment-toggle");
const segmentPicker = document.querySelector("#segment-picker");
const segmentOptions = document.querySelector("#segment-options");
const selectFirstSegment = document.querySelector("#select-first-segment");
const selectAllSegments = document.querySelector("#select-all-segments");
const clearSegments = document.querySelector("#clear-segments");
const markerHours = document.querySelector("#marker-hours");
const markerMinutes = document.querySelector("#marker-minutes");
const markerSeconds = document.querySelector("#marker-seconds");
const addSegmentMarker = document.querySelector("#add-segment-marker");
const clearSegmentMarkers = document.querySelector("#clear-segment-markers");
const segmentTimeline = document.querySelector("#segment-timeline");
const segmentMarkers = document.querySelector("#segment-markers");
const segmentStatus = document.querySelector("#segment-status");
const saveSegmentPlan = document.querySelector("#save-segment-plan");
const loadSegmentPlan = document.querySelector("#load-segment-plan");
const exportSegmentPlan = document.querySelector("#export-segment-plan");
const importSegmentPlan = document.querySelector("#import-segment-plan");
const themeToggle = document.querySelector("#theme-toggle");
const clearHistoryButton = document.querySelector("#clear-history-button");
const cleanupReportToggle = document.querySelector("#cleanup-report-toggle");
const cleanupReportDialog = document.querySelector("#cleanup-report-dialog");
const cleanupReportMessage = document.querySelector("#cleanup-report-message");
const navToggle = document.querySelector("#nav-toggle");
const navMenu = document.querySelector("#nav-menu");
const topbar = document.querySelector(".topbar");
const playlistOpenButton = document.querySelector("#playlist-open-button");
const playlistDialog = document.querySelector("#playlist-dialog");
const historyOpenButton = document.querySelector("#history-open-button");
const historyDialog = document.querySelector("#history-dialog");
const playlistImportForm = document.querySelector("#playlist-import-form");
const playlistImporterKey = document.querySelector("#playlist-importer-key");
const playlistImportFile = document.querySelector("#playlist-import-file");
const playlistImportFileLabel = document.querySelector("#playlist-import-file-label");
const playlistImportHelp = document.querySelector("#playlist-import-help");
const playlistImportButton = document.querySelector("#playlist-import-button");
const playlistImportMessage = document.querySelector("#playlist-import-message");
const playlistList = document.querySelector("#playlist-list");
const playlistDetail = document.querySelector("#playlist-detail");
const playlistDetailTitle = document.querySelector("#playlist-detail-title");
const playlistDetailMeta = document.querySelector("#playlist-detail-meta");
const playlistIssues = document.querySelector("#playlist-issues");
const playlistTracks = document.querySelector("#playlist-tracks");
const playlistPrev = document.querySelector("#playlist-prev");
const playlistNext = document.querySelector("#playlist-next");
const playlistPageStatus = document.querySelector("#playlist-page-status");
const playlistFilterForm = document.querySelector("#playlist-filter-form");
const playlistSearch = document.querySelector("#playlist-search");
const playlistStatusFilter = document.querySelector("#playlist-status-filter");
const playlistSort = document.querySelector("#playlist-sort");
const playlistSortDirection = document.querySelector("#playlist-sort-direction");
const playlistClearFilter = document.querySelector("#playlist-clear-filter");
const playlistSelectPage = document.querySelector("#playlist-select-page");
const playlistClearSelection = document.querySelector("#playlist-clear-selection");
const playlistBatchResolve = document.querySelector("#playlist-batch-resolve");
const playlistBatchQueue = document.querySelector("#playlist-batch-queue");
const playlistBatchFormat = document.querySelector("#playlist-batch-format");
const playlistBatchQuality = document.querySelector("#playlist-batch-quality");
const playlistSelectionStatus = document.querySelector("#playlist-selection-status");

const terminalStates = new Set(["completed", "failed", "expired", "interrupted", "paused"]);
const themeStorageKey = "mediaforgetool-theme";
const cleanupReportStorageKey = "mediaforgetool-show-cleanup-report";
const segmentPlanStorageKey = "mediaforgetool-segment-plan";
const segmentPlanSchema = "mediaforgetool.segment-plan.v1";
const playlistPageSize = 25;
const iconPaths = {
  details: [
    "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z",
    "M12 16v-4",
    "M12 8h.01",
  ],
  download: [
    "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4",
    "M7 10l5 5 5-5",
    "M12 15V3",
  ],
  file: [
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z",
    "M14 2v6h6",
    "M8 13h8",
    "M8 17h5",
  ],
  history: [
    "M3 12a9 9 0 1 0 3-6.7",
    "M3 3v6h6",
    "M12 7v5l3 2",
  ],
  menu: ["M4 7h16", "M4 12h16", "M4 17h16"],
  moon: ["M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"],
  pause: ["M10 4H6v16h4Z", "M18 4h-4v16h4Z"],
  play: ["M5 3l14 9-14 9Z"],
  scissors: [
    "M4.5 8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
    "M4.5 20.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
    "M8.2 8.2 19 19",
    "M8.2 15.8 19 5",
  ],
  search: [
    "M21 21l-4.3-4.3",
    "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z",
  ],
  sun: [
    "M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z",
    "M12 2v2",
    "M12 20v2",
    "M4.93 4.93l1.41 1.41",
    "M17.66 17.66l1.41 1.41",
    "M2 12h2",
    "M20 12h2",
    "M6.34 17.66l-1.41 1.41",
    "M19.07 4.93l-1.41 1.41",
  ],
  target: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z", "M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"],
  trash: [
    "M3 6h18",
    "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",
    "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6",
  ],
  upload: [
    "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4",
    "M17 8l-5-5-5 5",
    "M12 3v12",
  ],
};
let pollTimer = null;
let batchPollTimer = null;
let inspection = null;
let selectedSegments = [];
let cutMarkers = [];
let segmentNames = {};
let segmentPanelOpen = false;
let activeBatchJobs = [];
let renderedJob = null;
let selectedPlaylistId = null;
let selectedPlaylistOffset = 0;
let selectedPlaylistTrackIds = new Set();
let currentPlaylistTracks = [];
let playlistFilters = {
  q: "",
  resolution_status: "",
  sort: "position",
  direction: "asc",
};

initTheme();
initCleanupReportPreference();
enhanceStaticControls();
navToggle.addEventListener("click", toggleNavMenu);
themeToggle.addEventListener("click", toggleTheme);
clearHistoryButton.addEventListener("click", clearHistory);
cleanupReportToggle.addEventListener("change", () => {
  storePreference(cleanupReportStorageKey, cleanupReportToggle.checked);
});
document.addEventListener("click", closeNavMenuOnOutsideClick);
document.addEventListener("keydown", closeNavMenuOnEscape);
playlistOpenButton.addEventListener("click", openPlaylistDialog);
playlistDialog.addEventListener("close", () => playlistOpenButton.focus());
historyOpenButton.addEventListener("click", openHistoryDialog);
historyDialog.addEventListener("close", () => historyOpenButton.focus());
inspectButton.addEventListener("click", inspectMedia);
jobPause.addEventListener("click", () => {
  if (renderedJob?.id) {
    pauseJob(renderedJob.id);
  }
});
jobResume.addEventListener("click", () => {
  if (renderedJob?.id) {
    resumeJob(renderedJob.id);
  }
});
mediaUrl.addEventListener("input", clearInspection);
segmentToggle.addEventListener("click", toggleSegmentPanel);
selectFirstSegment.addEventListener("click", () => {
  const segments = availableSegments();
  selectedSegments = segments.slice(0, 1);
  renderSegmentOptions();
  renderEstimate();
});
selectAllSegments.addEventListener("click", () => {
  selectedSegments = availableSegments();
  renderSegmentOptions();
  renderEstimate();
});
clearSegments.addEventListener("click", () => {
  selectedSegments = [];
  renderSegmentOptions();
  renderEstimate();
});
saveSegmentPlan.addEventListener("click", saveCurrentSegmentPlan);
loadSegmentPlan.addEventListener("click", loadSavedSegmentPlan);
exportSegmentPlan.addEventListener("click", exportCurrentSegmentPlan);
importSegmentPlan.addEventListener("change", importSegmentPlanFile);
addSegmentMarker.addEventListener("click", addMarkerFromInput);
clearSegmentMarkers.addEventListener("click", resetMarkers);
playlistImporterKey.addEventListener("change", updatePlaylistImportMode);
playlistImportForm.addEventListener("submit", importPlaylist);
playlistPrev.addEventListener("click", () => pagePlaylist(-playlistPageSize));
playlistNext.addEventListener("click", () => pagePlaylist(playlistPageSize));
playlistFilterForm.addEventListener("submit", applyPlaylistFilters);
playlistClearFilter.addEventListener("click", clearPlaylistFilters);
playlistSelectPage.addEventListener("click", selectCurrentPlaylistPage);
playlistClearSelection.addEventListener("click", clearPlaylistSelection);
playlistBatchResolve.addEventListener("click", resolveSelectedPlaylistTracks);
playlistBatchQueue.addEventListener("click", queueSelectedPlaylistTracks);
playlistBatchFormat.addEventListener("change", () =>
  setCandidateOptionChoices(playlistBatchFormat, playlistBatchQuality)
);
setCandidateOptionChoices(playlistBatchFormat, playlistBatchQuality);
updatePlaylistImportMode();
document.querySelectorAll(".timecode-editor input").forEach((input) => {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addMarkerFromInput();
    }
  });
});
resolutionSelect.addEventListener("change", renderEstimate);
audioQualitySelect.addEventListener("change", renderEstimate);
document.querySelectorAll('input[name="format"]').forEach((radio) => {
  radio.addEventListener("change", renderEstimate);
});

function initTheme() {
  const storedTheme = readStoredTheme();
  const theme = storedTheme || preferredTheme();
  applyTheme(theme);
}

function toggleTheme() {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  storeTheme(nextTheme);
  applyTheme(nextTheme);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === "dark";
  themeToggle.setAttribute("aria-pressed", String(dark));
  setInlineContent(themeToggle, dark ? "Mode clair" : "Mode sombre", dark ? "sun" : "moon");
}

function enhanceStaticControls() {
  setInlineContent(navToggle, "Menu", "menu");
  setInlineContent(playlistOpenButton, "Importer une liste", "upload");
  setInlineContent(historyOpenButton, "Historique", "history");
  setInlineContent(inspectButton, "Analyser", "search");
  setInlineContent(segmentToggle, "Segments", "scissors");
  setInlineContent(submitButton, "Telecharger", "download");
  setInlineContent(clearHistoryButton, "Vider l historique", "trash");
  setInlineContent(selectFirstSegment, "Premier", "target");
  setInlineContent(selectAllSegments, "Tous", "details");
  setInlineContent(clearSegments, "Aucun", "trash");
  setInlineContent(jobPause, "Pause", "pause");
  setInlineContent(jobResume, "Reprendre", "play");
  setInlineContent(jobDownload, "Recuperer le fichier", "file");
}

function openPlaylistDialog() {
  if (!playlistDialog.open) {
    playlistDialog.showModal();
  }
  loadPlaylists();
}

function openHistoryDialog() {
  if (!historyDialog.open) {
    historyDialog.showModal();
  }
  loadHistory();
}

function toggleNavMenu() {
  setNavMenuOpen(navMenu.hidden);
}

function setNavMenuOpen(open) {
  navMenu.hidden = !open;
  navToggle.setAttribute("aria-expanded", String(open));
}

function closeNavMenuOnOutsideClick(event) {
  if (navMenu.hidden || topbar.contains(event.target)) {
    return;
  }
  setNavMenuOpen(false);
}

function closeNavMenuOnEscape(event) {
  if (event.key !== "Escape" || navMenu.hidden) {
    return;
  }
  setNavMenuOpen(false);
  navToggle.focus();
}

function toggleSegmentPanel() {
  setSegmentPanelOpen(!segmentPanelOpen);
  if (segmentPanelOpen && selectedSegments.length === 0) {
    selectedSegments = availableSegments();
  }
  renderSegmentOptions();
  renderEstimate();
}

function setSegmentPanelOpen(open) {
  segmentPanelOpen = Boolean(open && inspection);
  segmentToggle.disabled = !inspection;
  segmentToggle.setAttribute("aria-expanded", String(segmentPanelOpen));
  segmentToggle.setAttribute("aria-pressed", String(segmentPanelOpen));
}

function initCleanupReportPreference() {
  cleanupReportToggle.checked = readStoredPreference(cleanupReportStorageKey, true);
}

function setInlineContent(element, label, iconName) {
  element.replaceChildren(icon(iconName), textNode(label));
}

function textNode(label) {
  const text = document.createElement("span");
  text.textContent = label;
  return text;
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "button-icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  iconPaths[name].forEach((pathData) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathData);
    svg.append(path);
  });
  return svg;
}

function preferredTheme() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readStoredTheme() {
  try {
    return localStorage.getItem(themeStorageKey);
  } catch {
    return null;
  }
}

function storeTheme(theme) {
  try {
    localStorage.setItem(themeStorageKey, theme);
  } catch {
    // localStorage can be unavailable in hardened browsing contexts.
  }
}

function readStoredPreference(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : value === "true";
  } catch {
    return fallback;
  }
}

function storePreference(key, value) {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // localStorage can be unavailable in hardened browsing contexts.
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;

  try {
    if (!inspection) {
      const inspected = await inspectMedia();
      if (!inspected) {
        return;
      }
    }
    validateSegmentsForSubmit();
    const payloads = jobPayloads();
    const createdJobs = [];
    for (const payload of payloads) {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(apiErrorMessage(body.detail, "Le job n'a pas pu demarrer."));
      }
      createdJobs.push(body);
    }
    const firstJob = createdJobs[0];
    renderJob(firstJob);
    startBatchPolling(createdJobs);
    startPolling(firstJob.id);
    await loadHistory();
  } catch (error) {
    showFormError(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

function jobPayloads() {
  const segments = segmentPanelOpen && selectedSegments.length > 0 ? selectedSegments : [null];
  return segments.map((segment) => {
    const payload = {
      url: mediaUrl.value,
      format: new FormData(form).get("format"),
      title: segment?.title ? `${inspection?.title || "Media"} - ${segment.title}` : inspection?.title,
      platform: inspection?.platform,
      thumbnail_url: inspection?.thumbnail_url,
      duration_seconds: inspection?.duration_seconds,
      estimated_total_bytes: segmentEstimate(selectedEstimate(), segment),
    };
    if (payload.format === "mp4" && resolutionSelect.value) {
      payload.resolution = Number.parseInt(resolutionSelect.value, 10);
    }
    if (payload.format === "mp3") {
      payload.audio_bitrate_kbps = selectedAudioBitrate();
    }
    if (segment) {
      payload.segment_start_seconds = segment.start_seconds;
      payload.segment_end_seconds = segment.end_seconds;
    }
    return payload;
  });
}

async function inspectMedia() {
  if (!mediaUrl.reportValidity()) {
    return false;
  }

  inspectButton.disabled = true;
  inspectionMessage.textContent = "Analyse en cours...";
  try {
    const response = await fetch("/api/jobs/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: mediaUrl.value }),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "Le media ne peut pas etre analyse."));
    }
    inspection = body;
    cutMarkers = markersFromSuggestions(inspection.segment_suggestions || []);
    selectedSegments = [];
    setSegmentPanelOpen(false);
    resetMarkerInputs();
    renderInspection();
    renderResolutionOptions();
    renderSegmentOptions();
    renderEstimate();
    return true;
  } catch (error) {
    clearInspection();
    inspectionMessage.textContent = error.message;
    return false;
  } finally {
    inspectButton.disabled = false;
  }
}

function clearInspection() {
  inspection = null;
  selectedSegments = [];
  cutMarkers = [];
  segmentNames = {};
  setSegmentPanelOpen(false);
  inspectionMessage.textContent = "";
  mediaInspection.hidden = true;
  segmentPicker.hidden = true;
  segmentOptions.replaceChildren();
  segmentMarkers.replaceChildren();
  resetMarkerInputs();
  renderSegmentStatus();
  mediaThumbnail.hidden = true;
  mediaThumbnail.removeAttribute("src");
  resolutionSelect.replaceChildren(new Option("Auto", ""));
  segmentToggle.disabled = true;
  renderEstimate();
}

function renderInspection() {
  inspectionMessage.textContent = "";
  mediaInspection.hidden = false;
  mediaTitle.textContent = inspection.title || "Media";
  mediaMetadata.textContent = metadataText(inspection);
  mediaThumbnail.hidden = !inspection.thumbnail_url;
  if (inspection.thumbnail_url) {
    mediaThumbnail.src = inspection.thumbnail_url;
  }
}

function renderResolutionOptions() {
  const selected = resolutionSelect.value;
  const options = [new Option("Auto", "")];
  inspection.mp4_variants.forEach((variant) => {
    const size = sizeLabel(variant.estimated_size_bytes);
    const label = size ? `${variant.resolution}p - ${size}` : `${variant.resolution}p`;
    options.push(new Option(label, variant.resolution));
  });
  resolutionSelect.replaceChildren(...options);
  if ([...resolutionSelect.options].some((option) => option.value === selected)) {
    resolutionSelect.value = selected;
  }
}

function renderSegmentOptions() {
  const segments = availableSegments();
  segmentPicker.hidden = !segmentPanelOpen;
  segmentOptions.replaceChildren(...segments.map(segmentButton));
  renderTimeline();
  renderMarkers();
  renderSegmentStatus();
  if (segmentPanelOpen && segments.length > 0) {
    inspectionMessage.textContent = "Pose tes jalons, puis selectionne les segments a telecharger.";
  } else if (inspection) {
    inspectionMessage.textContent = "";
  }
}

function availableSegments() {
  if (!inspection) {
    return [];
  }
  if (Number.isFinite(inspection.duration_seconds) && inspection.duration_seconds > 0) {
    return segmentsFromMarkers();
  }
  return inspection.segment_suggestions || [];
}

function segmentButton(segment, index) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "segment-card";
  button.setAttribute("aria-pressed", isSegmentSelected(segment) ? "true" : "false");
  const label = document.createElement("input");
  label.type = "text";
  label.value = segment.title;
  label.setAttribute("aria-label", `Nom du segment ${index + 1}`);
  label.addEventListener("click", (event) => event.stopPropagation());
  label.addEventListener("input", () => {
    segmentNames[segmentKey(segment)] = label.value.trim();
    updateSelectedSegmentTitles();
  });
  const range = document.createElement("span");
  range.textContent = segmentRangeLabel(segment).replace(/ - Segment \d+$/, "");
  const duration = document.createElement("small");
  duration.textContent = `${durationLabel(segment.end_seconds - segment.start_seconds)}`;
  button.append(label, range, duration);
  button.addEventListener("click", () => {
    selectedSegments = isSegmentSelected(segment)
      ? selectedSegments.filter((item) => !sameSegment(item, segment))
      : [...selectedSegments, segment];
    renderSegmentOptions();
    renderEstimate();
  });
  return button;
}

function markersFromSuggestions(suggestions) {
  const duration = inspection?.duration_seconds;
  return uniqueSortedMarkers(
    suggestions.flatMap((segment) => [
      segment.start_seconds,
      segment.end_seconds,
    ]),
    duration,
  );
}

function segmentsFromMarkers() {
  const duration = inspection.duration_seconds;
  const boundaries = [0, ...uniqueSortedMarkers(cutMarkers, duration), duration];
  return boundaries.slice(0, -1).flatMap((start, index) => {
    const end = boundaries[index + 1];
    if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
      return [];
    }
    return [{
      start_seconds: start,
      end_seconds: end,
      title: segmentNames[`${start}-${end}`] || `Segment ${index + 1}`,
    }];
  });
}

function uniqueSortedMarkers(markers, duration) {
  return [...new Set(
    markers
      .filter((marker) => Number.isFinite(marker))
      .map((marker) => Math.round(marker))
      .filter((marker) => marker > 0 && Number.isFinite(duration) && marker < duration),
  )].sort((left, right) => left - right);
}

function addMarkerFromInput() {
  const marker = markerInputSeconds();
  if (!Number.isFinite(marker)) {
    renderSegmentStatus("Saisis un timecode valide.", "error");
    return;
  }
  if (!Number.isFinite(inspection?.duration_seconds) || inspection.duration_seconds <= 0) {
    renderSegmentStatus("Analyse un media avec une duree connue avant d'ajouter des jalons.", "error");
    return;
  }
  if (marker <= 0 || marker >= inspection.duration_seconds) {
    renderSegmentStatus("Le jalon doit etre strictement entre le debut et la fin du media.", "error");
    return;
  }
  cutMarkers = uniqueSortedMarkers([...cutMarkers, marker], inspection.duration_seconds);
  selectedSegments = availableSegments();
  resetMarkerInputs();
  renderSegmentOptions();
  renderEstimate();
}

function markerInputSeconds() {
  const hours = numericInputValue(markerHours);
  const minutes = numericInputValue(markerMinutes);
  const seconds = numericInputValue(markerSeconds);
  if (![hours, minutes, seconds].every(Number.isFinite)) {
    return null;
  }
  return hours * 3600 + minutes * 60 + seconds;
}

function numericInputValue(input) {
  if (input.value.trim() === "") {
    return 0;
  }
  const value = Number.parseInt(input.value, 10);
  return Number.isFinite(value) && value >= 0 ? value : null;
}

function resetMarkerInputs() {
  markerHours.value = "0";
  markerMinutes.value = "0";
  markerSeconds.value = "0";
}

function removeMarker(marker) {
  cutMarkers = cutMarkers.filter((item) => item !== marker);
  segmentNames = namesForExistingSegments();
  selectedSegments = availableSegments();
  renderSegmentOptions();
  renderEstimate();
}

function resetMarkers() {
  cutMarkers = markersFromSuggestions(inspection?.segment_suggestions || []);
  segmentNames = {};
  selectedSegments = availableSegments();
  renderSegmentOptions();
  renderEstimate();
}

function renderMarkers() {
  segmentMarkers.replaceChildren(...cutMarkers.map(markerChip));
}

function renderTimeline() {
  const duration = inspection?.duration_seconds;
  if (!Number.isFinite(duration) || duration <= 0) {
    segmentTimeline.replaceChildren();
    return;
  }
  const track = document.createElement("div");
  track.className = "timeline-track";
  const start = document.createElement("span");
  start.className = "timeline-edge";
  start.textContent = "0:00";
  const end = document.createElement("span");
  end.className = "timeline-edge timeline-end";
  end.textContent = durationLabel(duration);
  track.append(start, end, ...cutMarkers.map((marker) => timelineMarker(marker, duration)));
  segmentTimeline.replaceChildren(track);
}

function timelineMarker(marker, duration) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "timeline-marker";
  button.style.left = `${marker / duration * 100}%`;
  button.setAttribute("aria-label", `Retirer le jalon ${durationLabel(marker)}`);
  button.textContent = durationLabel(marker);
  button.addEventListener("click", () => removeMarker(marker));
  return button;
}

function markerChip(marker) {
  const chip = document.createElement("span");
  chip.className = "segment-marker";
  const label = document.createElement("span");
  label.textContent = durationLabel(marker);
  const remove = document.createElement("button");
  remove.type = "button";
  remove.setAttribute("aria-label", `Retirer le jalon ${durationLabel(marker)}`);
  remove.textContent = "x";
  remove.addEventListener("click", () => removeMarker(marker));
  chip.append(label, remove);
  return chip;
}

function isSegmentSelected(segment) {
  return selectedSegments.some((item) => sameSegment(item, segment));
}

function sameSegment(left, right) {
  return left?.start_seconds === right?.start_seconds && left?.end_seconds === right?.end_seconds;
}

function segmentKey(segment) {
  return `${segment.start_seconds}-${segment.end_seconds}`;
}

function updateSelectedSegmentTitles() {
  selectedSegments = selectedSegments.map((segment) => ({
    ...segment,
    title: segmentNames[segmentKey(segment)] || segment.title,
  }));
}

function namesForExistingSegments() {
  return Object.fromEntries(
    availableSegments()
      .map((segment) => [segmentKey(segment), segmentNames[segmentKey(segment)]])
      .filter((entry) => entry[1])
  );
}

function segmentRangeLabel(segment) {
  const range = `${durationLabel(segment.start_seconds)} - ${durationLabel(segment.end_seconds)}`;
  return segment.title ? `${range} - ${segment.title}` : range;
}

function parseTime(value) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(",", ".")
    .replace(/\s+/g, "")
    .replace(/(\d+(?:\.\d+)?)h/g, "$1:")
    .replace(/(\d+(?:\.\d+)?)m(?:in)?/g, "$1:")
    .replace(/(\d+(?:\.\d+)?)s(?:ec)?/g, "$1")
    .replace(/:+$/, "");
  const parts = normalized.split(":").map(Number);
  if (parts.some((part) => !Number.isFinite(part)) || parts.length > 3) {
    return null;
  }
  return Math.round(parts.reduce((total, part) => total * 60 + part, 0));
}

function validateSegmentsForSubmit() {
  if (!segmentPanelOpen) {
    return;
  }
  const segments = availableSegments();
  selectedSegments = selectedSegments.filter((segment) =>
    segments.some((item) => sameSegment(item, segment))
  );
  if (segments.length > 0 && selectedSegments.length === 0) {
    throw new Error("Selectionne au moins un segment, ou reinitialise les jalons.");
  }
}

function renderSegmentStatus(message = "", state = "") {
  if (!segmentStatus) {
    return;
  }
  if (message) {
    segmentStatus.dataset.state = state;
    segmentStatus.textContent = message;
    return;
  }
  const duration = Number.isFinite(inspection?.duration_seconds)
    ? `Duree analysee: ${durationLabel(inspection.duration_seconds)}.`
    : "";
  const segments = availableSegments();
  segmentStatus.dataset.state = segments.length > 0 ? "ok" : "";
  segmentStatus.textContent =
    `${duration} ${cutMarkers.length} jalon(s), ${segments.length} segment(s), ${selectedSegments.length} selectionne(s).`;
}

function currentSegmentPlan() {
  const segments = availableSegments();
  return {
    schema: segmentPlanSchema,
    source_url: mediaUrl.value,
    format: new FormData(form).get("format"),
    resolution: resolutionSelect.value || null,
    audio_bitrate_kbps: selectedAudioBitrate(),
    media: {
      title: inspection?.title || null,
      platform: inspection?.platform || null,
      thumbnail_url: inspection?.thumbnail_url || null,
      duration_seconds: inspection?.duration_seconds || null,
    },
    markers: cutMarkers,
    segments: segments.map((segment) => ({
      start_seconds: segment.start_seconds,
      end_seconds: segment.end_seconds,
      title: segment.title,
      selected: selectedSegments.some((item) => sameSegment(item, segment)),
    })),
  };
}

function applySegmentPlan(plan) {
  if (plan.schema !== segmentPlanSchema || !Array.isArray(plan.markers)) {
    throw new Error("Plan de decoupe incompatible.");
  }
  mediaUrl.value = plan.source_url || mediaUrl.value;
  const formatInput = document.querySelector(`input[name="format"][value="${plan.format || "mp4"}"]`);
  if (formatInput) {
    formatInput.checked = true;
  }
  inspection = {
    title: plan.media?.title,
    platform: plan.media?.platform,
    thumbnail_url: plan.media?.thumbnail_url,
    duration_seconds: plan.media?.duration_seconds,
    mp3_estimated_size_bytes: null,
    mp4_variants: [],
    segment_suggestions: [],
  };
  cutMarkers = uniqueSortedMarkers(plan.markers, inspection.duration_seconds);
  segmentNames = Object.fromEntries(
    (plan.segments || []).map((segment) => [
      `${segment.start_seconds}-${segment.end_seconds}`,
      segment.title,
    ])
  );
  selectedSegments = availableSegments().filter((segment) =>
    (plan.segments || []).some((item) => item.selected && sameSegment(item, segment))
  );
  renderInspection();
  renderResolutionOptions();
  if (plan.resolution) {
    resolutionSelect.value = plan.resolution;
  }
  if (plan.audio_bitrate_kbps) {
    audioQualitySelect.value = String(plan.audio_bitrate_kbps);
  }
  setSegmentPanelOpen(true);
  renderSegmentOptions();
  renderEstimate();
}

function saveCurrentSegmentPlan() {
  localStorage.setItem(segmentPlanStorageKey, JSON.stringify(currentSegmentPlan()));
  renderSegmentStatus("Plan de decoupe sauvegarde localement.", "ok");
}

function loadSavedSegmentPlan() {
  const rawPlan = localStorage.getItem(segmentPlanStorageKey);
  if (!rawPlan) {
    renderSegmentStatus("Aucun plan sauvegarde localement.", "error");
    return;
  }
  applySegmentPlan(JSON.parse(rawPlan));
  renderSegmentStatus("Plan de decoupe charge.", "ok");
}

function exportCurrentSegmentPlan() {
  const blob = new Blob([JSON.stringify(currentSegmentPlan(), null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mediaforgetool-segment-plan.json";
  link.click();
  URL.revokeObjectURL(url);
}

function importSegmentPlanFile() {
  const file = importSegmentPlan.files[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      applySegmentPlan(JSON.parse(String(reader.result)));
      renderSegmentStatus("Plan de decoupe importe.", "ok");
    } catch (error) {
      renderSegmentStatus(error.message, "error");
    } finally {
      importSegmentPlan.value = "";
    }
  });
  reader.readAsText(file);
}

function renderEstimate() {
  const format = new FormData(form).get("format");
  resolutionField.hidden = format !== "mp4";
  audioQualityField.hidden = format !== "mp3";
  if (!inspection) {
    mediaEstimate.textContent = "";
    return;
  }

  if (format === "mp3") {
    mediaEstimate.textContent = estimateText("MP3", selectionEstimate(selectedEstimate()));
    return;
  }

  mediaEstimate.textContent = estimateText("MP4", selectionEstimate(selectedEstimate()));
}

function selectedEstimate() {
  const format = new FormData(form).get("format");
  if (format === "mp3") {
    return mp3EstimateForSelectedBitrate();
  }
  const resolution = Number.parseInt(resolutionSelect.value, 10);
  const variant = inspection?.mp4_variants.find((item) => item.resolution === resolution)
    || inspection?.mp4_variants.at(-1);
  return variant?.estimated_size_bytes;
}

function selectedAudioBitrate() {
  return Number.parseInt(audioQualitySelect.value, 10);
}

function mp3EstimateForSelectedBitrate() {
  if (!Number.isFinite(inspection?.duration_seconds)) {
    return inspection?.mp3_estimated_size_bytes;
  }
  return Math.round(inspection.duration_seconds * selectedAudioBitrate() * 1000 / 8);
}

function segmentEstimate(size, segment = firstSelectedSegment()) {
  if (!segment || !Number.isFinite(size) || !Number.isFinite(inspection?.duration_seconds)) {
    return size;
  }
  const segmentDuration = segment.end_seconds - segment.start_seconds;
  if (inspection.duration_seconds <= 0 || segmentDuration <= 0) {
    return size;
  }
  return Math.round(size * (segmentDuration / inspection.duration_seconds));
}

function selectionEstimate(size) {
  if (!segmentPanelOpen) {
    return { size, scoped: false };
  }
  const segments = availableSegments();
  if (!Number.isFinite(size) || !Number.isFinite(inspection?.duration_seconds)) {
    return { size, scoped: false };
  }
  if (segments.length === 0) {
    return { size, scoped: false };
  }
  if (selectedSegments.length === 0) {
    return { size: null, scoped: true };
  }
  const selectedDuration = selectedSegments.reduce((total, segment) => {
    const duration = segment.end_seconds - segment.start_seconds;
    return duration > 0 ? total + duration : total;
  }, 0);
  if (selectedDuration <= 0) {
    return { size: null, scoped: true };
  }
  return {
    fullSize: size,
    scoped: selectedDuration < inspection.duration_seconds,
    size: Math.round(size * (selectedDuration / inspection.duration_seconds)),
  };
}

function firstSelectedSegment() {
  return selectedSegments[0] || null;
}

function estimateText(format, estimate) {
  const label = sizeLabel(estimate.size);
  if (!label && estimate.scoped) {
    return `Estimation ${format}: aucune selection`;
  }
  if (!label) {
    return `Estimation ${format} indisponible`;
  }
  if (estimate.scoped) {
    const fullLabel = sizeLabel(estimate.fullSize);
    return fullLabel
      ? `Estimation ${format} selection: ${label} (media entier: ${fullLabel})`
      : `Estimation ${format} selection: ${label}`;
  }
  return `Estimation ${format}: ${label}`;
}

function sizeLabel(size, approximate = true) {
  if (!Number.isFinite(size)) {
    return "";
  }
  const prefix = approximate ? "~" : "";
  return `${prefix}${formatNumber(size / (1024 * 1024), size >= 100 * 1024 * 1024 ? 0 : 1)} Mo`;
}

function formatNumber(value, maximumFractionDigits) {
  return new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits,
  }).format(value);
}

function metadataText(media) {
  return [media.platform, durationLabel(media.duration_seconds)].filter(Boolean).join(" - ");
}

function dateTimeLabel(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function durationLabel(duration) {
  if (!Number.isFinite(duration)) {
    return "";
  }
  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = String(duration % 60).padStart(2, "0");
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${seconds}`;
  }
  return `${minutes}:${seconds}`;
}

async function startPolling(jobId) {
  window.clearTimeout(pollTimer);
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    showFormError("Le statut du job est indisponible.");
    return;
  }
  const job = await response.json();
  renderJob(job);
  await loadHistory();
  if (!terminalStates.has(job.status)) {
    pollTimer = window.setTimeout(() => startPolling(jobId), 1200);
  }
}

async function startBatchPolling(jobs) {
  window.clearTimeout(batchPollTimer);
  activeBatchJobs = jobs;
  batchJobs.hidden = jobs.length <= 1;
  if (jobs.length <= 1) {
    return;
  }
  await pollBatchJobs();
}

async function pollBatchJobs() {
  const responses = await Promise.all(activeBatchJobs.map(fetchBatchJob));
  activeBatchJobs = responses;
  renderBatchJobs(responses);
  if (responses.some((job) => !terminalStates.has(job.status))) {
    batchPollTimer = window.setTimeout(pollBatchJobs, 1200);
  }
}

async function fetchBatchJob(job) {
  try {
    const response = await fetch(`/api/jobs/${job.id}`);
    if (!response.ok) {
      return job;
    }
    return await response.json();
  } catch {
    return job;
  }
}

function renderBatchJobs(jobs) {
  const progressValues = jobs.map((job) =>
    terminalStates.has(job.status) ? 100 : job.progress_percent ?? 0
  );
  const progress = progressValues.reduce((total, value) => total + value, 0) / jobs.length;
  batchProgress.value = progress;
  const completed = jobs.filter((job) => terminalStates.has(job.status)).length;
  const running = jobs.length - completed;
  batchStatus.textContent = running > 0
    ? `${completed}/${jobs.length} - ${running} en cours`
    : `${completed}/${jobs.length}`;
  batchList.replaceChildren(...jobs.map(batchItem));
}

function batchItem(job) {
  const item = document.createElement("li");
  const label = document.createElement("strong");
  label.textContent = job.title || job.id;
  const state = document.createElement("span");
  state.textContent = batchItemStatus(job);
  item.append(label, state);
  return item;
}

function batchItemStatus(job) {
  if (Number.isFinite(job.progress_percent)) {
    return `${job.status} - ${formatNumber(job.progress_percent, 1)} %`;
  }
  const details = jobDetailsText(job);
  return details ? `${job.status} - ${details}` : job.status;
}

async function resumeJob(jobId) {
  jobResume.disabled = true;
  try {
    const response = await fetch(`/api/jobs/${jobId}/resume`, { method: "POST" });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "Le job n'a pas pu etre repris."));
    }
    renderJob(body);
    startPolling(body.id);
    await loadHistory();
  } catch (error) {
    showFormError(error.message);
  } finally {
    jobResume.disabled = false;
  }
}

async function pauseJob(jobId) {
  jobPause.disabled = true;
  try {
    const response = await fetch(`/api/jobs/${jobId}/pause`, { method: "POST" });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "Le job n'a pas pu etre mis en pause."));
    }
    renderJob(body);
    await loadHistory();
  } catch (error) {
    showFormError(error.message);
  } finally {
    jobPause.disabled = false;
  }
}

async function deleteJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json();
    showFormError(apiErrorMessage(body.detail, "Le job n'a pas pu etre supprime."));
    return;
  }
  const report = await response.json();
  if (renderedJob?.id === jobId) {
    currentJob.hidden = true;
    renderedJob = null;
  }
  await loadHistory();
  showCleanupReport(report);
}

async function clearHistory() {
  if (!window.confirm("Vider tout l historique inactif et supprimer les fichiers associes ?")) {
    return;
  }
  clearHistoryButton.disabled = true;
  try {
    const response = await fetch("/api/jobs", { method: "DELETE" });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "L historique n'a pas pu etre vide."));
    }
    if (renderedJob && canDelete(renderedJob)) {
      currentJob.hidden = true;
      renderedJob = null;
    }
    await loadHistory();
    showCleanupReport(body);
  } catch (error) {
    showFormError(error.message);
  } finally {
    clearHistoryButton.disabled = false;
  }
}

function renderJob(job) {
  renderedJob = job;
  currentJob.hidden = false;
  jobTitle.textContent = job.title || `Job ${job.requested_format.toUpperCase()}`;
  jobStatus.textContent = job.status;
  jobProgress.value = job.progress_percent ?? 0;
  jobProgress.removeAttribute("aria-busy");
  if (job.progress_percent === null) {
    jobProgress.removeAttribute("value");
    jobProgress.setAttribute("aria-busy", "true");
  }
  jobDetails.textContent = jobDetailsText(job);
  jobError.hidden = !job.error;
  jobError.textContent = apiErrorMessage(job.error, "");
  jobPause.hidden = !canPause(job);
  jobResume.hidden = !canResume(job);
  jobDownload.hidden = !job.download_url;
  if (job.download_url) {
    jobDownload.href = job.download_url;
  }
}

function canPause(job) {
  return job.id && ["queued", "extracting", "downloading", "processing"].includes(job.status);
}

function canResume(job) {
  if (!job.id || ["OUTPUT_FORMAT_UNAVAILABLE", "SOURCE_NO_STREAMS"].includes(job.error?.code)) {
    return false;
  }
  return ["interrupted", "failed", "paused"].includes(job.status);
}

function canDelete(job) {
  return job.id && ["completed", "failed", "expired", "interrupted"].includes(job.status);
}

function jobDetailsText(job) {
  const details = [];
  if (Number.isFinite(job.progress_percent)) {
    details.push(`${formatNumber(job.progress_percent, 1)} %`);
  }
  const transferred = transferLabel(job.downloaded_bytes, job.total_bytes);
  if (transferred) {
    details.push(transferred);
  }
  if (Number.isFinite(job.download_speed_bytes_per_second)) {
    details.push(`${sizeLabel(job.download_speed_bytes_per_second, false)}/s`);
  }
  if (Number.isFinite(job.eta_seconds)) {
    details.push(`reste ${durationLabel(job.eta_seconds)}`);
  }
  if (Number.isFinite(job.segment_start_seconds) && Number.isFinite(job.segment_end_seconds)) {
    details.push(`extrait ${segmentRangeLabel({
      start_seconds: job.segment_start_seconds,
      end_seconds: job.segment_end_seconds,
    })}`);
  }
  return details.join(" - ");
}

function transferLabel(downloaded, total) {
  if (Number.isFinite(downloaded) && Number.isFinite(total)) {
    return `${sizeLabel(downloaded, false)} / ${sizeLabel(total, false)}`;
  }
  if (Number.isFinite(downloaded)) {
    return sizeLabel(downloaded, false);
  }
  return "";
}

function showCleanupReport(report) {
  if (!cleanupReportToggle.checked) {
    return;
  }
  const message = cleanupReportText(report);
  if (cleanupReportDialog.showModal) {
    cleanupReportMessage.textContent = message;
    cleanupReportDialog.showModal();
    return;
  }
  window.alert(message);
}

function cleanupReportText(report) {
  const parts = [
    `${report.jobs_deleted} item(s) supprime(s)`,
    `${report.output_dirs_deleted} dossier(s) de sortie nettoye(s)`,
    `${report.temp_dirs_deleted} dossier(s) temporaire(s) nettoye(s)`,
    `${sizeLabel(report.bytes_reclaimed, false) || "0 Mo"} recupere(s)`,
  ];
  if (report.active_jobs_skipped > 0) {
    parts.push(`${report.active_jobs_skipped} job(s) actif(s) ignore(s)`);
  }
  return parts.join(". ") + ".";
}

function showFormError(message) {
  renderJob({
    requested_format: "mp4",
    status: "failed",
    progress_percent: 0,
    error: { message },
  });
}

function apiErrorMessage(error, fallback) {
  const knownMessages = {
    INVALID_URL: "Utilise une URL media publique en HTTP ou HTTPS.",
    MEDIA_TOO_LONG: "Le media depasse la limite de duree de cette instance.",
    MEDIA_TOO_LARGE: "Le fichier depasse la limite de taille de cette instance.",
    SEGMENT_OUT_OF_BOUNDS: "La decoupe demandee depasse la duree reelle du media.",
    OUTPUT_FORMAT_UNAVAILABLE:
      "Aucun format compatible ne respecte ce format, cette resolution et les limites.",
    SOURCE_AUTH_REQUIRED: "Cette source demande une authentification avant le telechargement.",
    SOURCE_NO_STREAMS:
      "Cette source demande probablement des credentials. Configure les cookies yt-dlp de l'instance, puis relance l'analyse.",
    COOKIES_UNAVAILABLE: "La source de cookies configuree est introuvable.",
    IMPORT_FILE_TOO_LARGE: "Le fichier depasse la limite de cette instance.",
    IMPORT_FORMAT_UNSUPPORTED: "Selectionne un fichier compatible avec l'importer choisi.",
    IMPORT_FILE_INVALID: "Le fichier ne contient aucune piste valide.",
    IMPORT_TOO_MANY_ROWS: "Le fichier contient trop de lignes pour cette instance.",
    TEXT_TRACK_FORMAT_INVALID: "Une ligne texte ne respecte pas le format Artiste - Titre.",
    PLAYLIST_IMPORTER_UNKNOWN: "Cet importer de playlist n'est pas disponible.",
    PLAYLIST_NOT_FOUND: "Cette playlist importee est introuvable.",
    MEDIA_SEARCH_AUTH_REQUIRED: "Le provider de recherche demande une authentification.",
    MEDIA_SEARCH_NO_RESULTS: "Aucun candidat trouve pour cette piste.",
    MEDIA_SEARCH_PROVIDER_UNKNOWN: "Ce provider de recherche n'est pas disponible.",
    MEDIA_SEARCH_TIMEOUT: "La recherche media a expire.",
    MEDIA_SEARCH_UNAVAILABLE: "Le provider de recherche est temporairement indisponible.",
    TRACK_NOT_FOUND: "Cette piste est introuvable dans la playlist.",
    CANDIDATE_NOT_FOUND: "Ce candidat n'est pas disponible pour cette piste.",
    QUEUE_FULL: "La queue de telechargement est pleine.",
  };
  return knownMessages[error?.code] || error?.message || fallback;
}

function updatePlaylistImportMode() {
  const textMode = playlistImporterKey.value === "text";
  playlistImportFile.accept = textMode ? ".txt,.text,text/plain" : ".csv,text/csv";
  playlistImportFileLabel.textContent = textMode ? "Texte libre" : "CSV Shazam";
  playlistImportHelp.textContent = textMode
    ? "Une piste par ligne: Artiste - Titre. Les lignes # et vides sont ignorees."
    : "L'import cree une playlist de revue sans lancer de telechargement.";
}

async function importPlaylist(event) {
  event.preventDefault();
  if (!playlistImportFile.files.length) {
    playlistImportMessage.textContent = "Selectionne un fichier a importer.";
    return;
  }
  playlistImportButton.disabled = true;
  playlistImportMessage.textContent = "Import en cours...";
  const data = new FormData(playlistImportForm);
  data.set("importer_key", playlistImporterKey.value);
  try {
    const response = await fetch("/api/playlists/import", {
      method: "POST",
      body: data,
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "L'import n'a pas pu etre termine."));
    }
    playlistImportForm.reset();
    updatePlaylistImportMode();
    resetPlaylistFilterControls();
    playlistImportMessage.textContent = playlistImportSummary(body.playlist);
    selectedPlaylistId = body.playlist.id;
    selectedPlaylistOffset = 0;
    selectedPlaylistTrackIds = new Set();
    await loadPlaylists();
    await loadPlaylistDetail(selectedPlaylistId, 0);
  } catch (error) {
    playlistImportMessage.textContent = error.message;
  } finally {
    playlistImportButton.disabled = false;
  }
}

function playlistImportSummary(playlist) {
  const rejected = playlist.rejected_row_count > 0
    ? `, ${playlist.rejected_row_count} avertissement(s)`
    : "";
  return `${playlist.track_count} piste(s) importee(s)${rejected}.`;
}

async function loadPlaylists() {
  const response = await fetch("/api/playlists?limit=12");
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  playlistList.replaceChildren(...payload.items.map(playlistListItem));
  if (!selectedPlaylistId && payload.items.length > 0) {
    selectedPlaylistId = payload.items[0].id;
    selectedPlaylistOffset = 0;
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
  }
}

function playlistListItem(playlist) {
  const item = document.createElement("li");
  item.className = "playlist-list-item";
  const button = document.createElement("button");
  button.type = "button";
  button.setAttribute("aria-pressed", String(playlist.id === selectedPlaylistId));
  const title = document.createElement("strong");
  title.textContent = playlist.name;
  const meta = document.createElement("span");
  meta.textContent = [
    `${playlist.track_count} piste(s)`,
    playlist.status,
    dateTimeLabel(playlist.created_at),
  ].filter(Boolean).join(" - ");
  button.append(title, meta);
  button.addEventListener("click", () => {
    if (selectedPlaylistId !== playlist.id) {
      selectedPlaylistTrackIds = new Set();
    }
    selectedPlaylistId = playlist.id;
    selectedPlaylistOffset = 0;
    loadPlaylistDetail(playlist.id, 0);
  });
  item.append(button);
  return item;
}

async function loadPlaylistDetail(playlistId, offset) {
  const params = new URLSearchParams({
    limit: String(playlistPageSize),
    offset: String(offset),
  });
  if (playlistFilters.q) {
    params.set("q", playlistFilters.q);
  }
  if (playlistFilters.resolution_status) {
    params.set("resolution_status", playlistFilters.resolution_status);
  }
  params.set("sort", playlistFilters.sort);
  params.set("direction", playlistFilters.direction);
  const response = await fetch(
    `/api/playlists/${encodeURIComponent(playlistId)}?${params}`,
  );
  const body = await response.json();
  if (!response.ok) {
    playlistImportMessage.textContent = apiErrorMessage(
      body.detail,
      "La playlist importee n'a pas pu etre chargee.",
    );
    return;
  }
  selectedPlaylistId = playlistId;
  selectedPlaylistOffset = body.offset;
  renderPlaylistDetail(body);
  await loadPlaylists();
}

function renderPlaylistDetail(detail) {
  playlistDetail.hidden = false;
  currentPlaylistTracks = detail.tracks;
  playlistDetailTitle.textContent = detail.playlist.name;
  playlistDetailMeta.textContent = [
    `${detail.total_tracks} piste(s)`,
    detail.playlist.status,
    detail.playlist.source_filename,
    playlistFilterSummary(),
    playlistSortSummary(),
  ].filter(Boolean).join(" - ");
  playlistIssues.replaceChildren(...detail.issues.map(playlistIssueItem));
  playlistIssues.hidden = detail.issues.length === 0;
  playlistTracks.replaceChildren(...detail.tracks.map(playlistTrackItem));
  const first = detail.total_tracks === 0 ? 0 : detail.offset + 1;
  const last = Math.min(detail.offset + detail.tracks.length, detail.total_tracks);
  playlistPageStatus.textContent = `${first}-${last} / ${detail.total_tracks}`;
  playlistPrev.disabled = detail.offset <= 0;
  playlistNext.disabled = detail.offset + detail.limit >= detail.total_tracks;
  renderPlaylistSelectionStatus();
}

function applyPlaylistFilters(event) {
  event.preventDefault();
  playlistFilters = {
    q: playlistSearch.value.trim(),
    resolution_status: playlistStatusFilter.value,
    sort: playlistSort.value,
    direction: playlistSortDirection.value,
  };
  selectedPlaylistOffset = 0;
  selectedPlaylistTrackIds = new Set();
  if (selectedPlaylistId) {
    loadPlaylistDetail(selectedPlaylistId, 0);
  }
}

function clearPlaylistFilters() {
  resetPlaylistFilterControls();
  selectedPlaylistOffset = 0;
  selectedPlaylistTrackIds = new Set();
  if (selectedPlaylistId) {
    loadPlaylistDetail(selectedPlaylistId, 0);
  }
}

function resetPlaylistFilterControls() {
  playlistSearch.value = "";
  playlistStatusFilter.value = "";
  playlistSort.value = "position";
  playlistSortDirection.value = "asc";
  playlistFilters = {
    q: "",
    resolution_status: "",
    sort: "position",
    direction: "asc",
  };
}

function playlistFilterSummary() {
  const parts = [];
  if (playlistFilters.q) {
    parts.push(`filtre: ${playlistFilters.q}`);
  }
  if (playlistFilters.resolution_status) {
    parts.push(`statut: ${playlistFilters.resolution_status}`);
  }
  return parts.join(", ");
}

function playlistSortSummary() {
  if (playlistFilters.sort === "position" && playlistFilters.direction === "asc") {
    return "";
  }
  const labels = {
    position: "ordre import",
    artist: "artiste",
    title: "titre",
    album: "album",
    resolution_status: "statut",
  };
  const direction = playlistFilters.direction === "desc" ? "desc" : "asc";
  return `tri: ${labels[playlistFilters.sort] || playlistFilters.sort} ${direction}`;
}

function playlistIssueItem(issue) {
  const item = document.createElement("li");
  const row = issue.row_number ? `Ligne ${issue.row_number}: ` : "";
  item.textContent = `${row}${issue.message}`;
  return item;
}

function playlistTrackItem(track) {
  const item = document.createElement("li");
  item.className = "playlist-track";
  const selectRow = document.createElement("label");
  selectRow.className = "playlist-track-select";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = selectedPlaylistTrackIds.has(track.id);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      selectedPlaylistTrackIds.add(track.id);
    } else {
      selectedPlaylistTrackIds.delete(track.id);
    }
    renderPlaylistSelectionStatus();
  });
  const selectLabel = document.createElement("span");
  selectLabel.textContent = "Selectionner";
  selectRow.append(checkbox, selectLabel);
  const title = document.createElement("strong");
  title.textContent = `${track.artist} - ${track.title}`;
  const album = document.createElement("span");
  album.textContent = track.album || "Album non renseigne";
  const status = document.createElement("small");
  status.textContent = track.resolution_status;
  const actions = document.createElement("div");
  actions.className = "playlist-track-actions";
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "quiet-button";
  edit.textContent = "Modifier";
  const resolve = document.createElement("button");
  resolve.type = "button";
  resolve.className = "quiet-button";
  resolve.textContent = track.resolution_status === "resolved" ? "Rechercher encore" : "Rechercher";
  edit.addEventListener("click", () => renderTrackEditForm(item, track));
  resolve.addEventListener("click", () => resolvePlaylistTrack(track.id, resolve));
  actions.append(edit, resolve);
  const queueItems = document.createElement("ol");
  queueItems.className = "track-queue-list";
  queueItems.replaceChildren(...(track.queue_items || []).map(queueItemLink));
  queueItems.hidden = !track.queue_items?.length;
  const candidates = document.createElement("ol");
  candidates.className = "candidate-list";
  candidates.replaceChildren(...(track.candidates || []).map((candidate) =>
    candidateItem(candidate, track.id)
  ));
  candidates.hidden = !track.candidates?.length;
  item.append(selectRow, title, album, status, actions, queueItems, candidates);
  return item;
}

function renderTrackEditForm(item, track) {
  const existing = item.querySelector(".playlist-track-edit");
  if (existing) {
    existing.remove();
    return;
  }
  const form = document.createElement("form");
  form.className = "playlist-track-edit";
  const artist = trackEditInput("Artiste", track.artist, 300);
  const title = trackEditInput("Titre", track.title, 500);
  const album = trackEditInput("Album", track.album || "", 500);
  const isrc = trackEditInput("ISRC", track.isrc || "", 20);
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.textContent = "Enregistrer";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "quiet-button";
  cancel.textContent = "Annuler";
  cancel.addEventListener("click", () => form.remove());
  form.append(artist.label, title.label, album.label, isrc.label, submit, cancel);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    updatePlaylistTrack(
      track.id,
      {
        artist: artist.input.value,
        title: title.input.value,
        album: album.input.value || null,
        isrc: isrc.input.value || null,
      },
      submit,
    );
  });
  item.append(form);
}

function trackEditInput(labelText, value, maxLength) {
  const label = document.createElement("label");
  const span = document.createElement("span");
  span.textContent = labelText;
  const input = document.createElement("input");
  input.type = "text";
  input.maxLength = maxLength;
  input.value = value;
  input.required = labelText === "Artiste" || labelText === "Titre";
  label.append(span, input);
  return { label, input };
}

async function updatePlaylistTrack(trackId, payload, button) {
  if (!selectedPlaylistId) {
    return;
  }
  button.disabled = true;
  playlistImportMessage.textContent = "Mise a jour de la piste...";
  try {
    const response = await fetch(
      `/api/playlists/${encodeURIComponent(selectedPlaylistId)}/tracks/${encodeURIComponent(trackId)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "La piste n'a pas pu etre modifiee."));
    }
    playlistImportMessage.textContent = "Piste mise a jour.";
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
  } catch (error) {
    playlistImportMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function resolvePlaylistTrack(trackId, button) {
  if (!selectedPlaylistId) {
    return;
  }
  button.disabled = true;
  playlistImportMessage.textContent = "Recherche en cours...";
  try {
    const response = await fetch(
      `/api/playlists/${encodeURIComponent(selectedPlaylistId)}/tracks/${encodeURIComponent(trackId)}/resolve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_key: "youtube", limit: 5 }),
      },
    );
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "La recherche n'a pas pu etre terminee."));
    }
    playlistImportMessage.textContent = `${body.candidates.length} candidat(s) trouve(s).`;
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
  } catch (error) {
    playlistImportMessage.textContent = error.message;
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
  } finally {
    button.disabled = false;
  }
}

function candidateItem(candidate, trackId) {
  const item = document.createElement("li");
  const title = document.createElement("a");
  title.href = candidate.source_url;
  title.rel = "noreferrer";
  title.textContent = candidate.title;
  const meta = document.createElement("span");
  meta.textContent = [
    candidate.creator,
    durationLabel(candidate.duration_seconds),
    candidate.provider_key,
  ].filter(Boolean).join(" - ");
  const controls = document.createElement("div");
  controls.className = "candidate-actions";
  const format = document.createElement("select");
  format.setAttribute("aria-label", "Format a ajouter");
  format.append(new Option("MP3", "mp3"), new Option("MP4", "mp4"));
  const option = document.createElement("select");
  option.setAttribute("aria-label", "Option de qualite");
  setCandidateOptionChoices(format, option);
  format.addEventListener("change", () => setCandidateOptionChoices(format, option));
  const submit = document.createElement("button");
  submit.type = "button";
  submit.className = "quiet-button";
  submit.textContent = "Ajouter";
  submit.addEventListener("click", () => queueCandidate(trackId, candidate.id, format, option, submit));
  controls.append(format, option, submit);
  item.append(title, meta, controls);
  return item;
}

function setCandidateOptionChoices(format, option) {
  if (format.value === "mp4") {
    option.replaceChildren(
      new Option("360p", "360"),
      new Option("480p", "480"),
      new Option("720p", "720"),
      new Option("1080p", "1080"),
    );
    option.value = "720";
    return;
  }
  option.replaceChildren(
    new Option("128 kb/s", "128"),
    new Option("192 kb/s", "192"),
    new Option("256 kb/s", "256"),
    new Option("320 kb/s", "320"),
  );
  option.value = "192";
}

async function queueCandidate(trackId, candidateId, format, option, button) {
  if (!selectedPlaylistId) {
    return;
  }
  button.disabled = true;
  playlistImportMessage.textContent = "Ajout a la queue...";
  const payload = { format: format.value };
  if (format.value === "mp4") {
    payload.resolution = Number.parseInt(option.value, 10);
  } else {
    payload.audio_bitrate_kbps = Number.parseInt(option.value, 10);
  }
  try {
    const response = await fetch(
      (
        `/api/playlists/${encodeURIComponent(selectedPlaylistId)}`
        + `/tracks/${encodeURIComponent(trackId)}`
        + `/candidates/${encodeURIComponent(candidateId)}/queue`
      ),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "Le candidat n'a pas pu etre ajoute."));
    }
    playlistImportMessage.textContent = "Candidat ajoute a la queue.";
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
    await loadHistory();
  } catch (error) {
    playlistImportMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function queueItemLink(queueItem) {
  const item = document.createElement("li");
  const label = document.createElement("span");
  label.textContent = `${queueItem.requested_format.toUpperCase()} - ${queueItem.status}`;
  item.append(label);
  if (queueItem.download_job_id) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "inline-action";
    button.textContent = "Historique";
    button.addEventListener("click", openHistoryDialog);
    item.append(button);
  }
  return item;
}

function selectCurrentPlaylistPage() {
  currentPlaylistTracks.forEach((track) => selectedPlaylistTrackIds.add(track.id));
  playlistTracks.replaceChildren(...currentPlaylistTracks.map(playlistTrackItem));
  renderPlaylistSelectionStatus();
}

function clearPlaylistSelection() {
  selectedPlaylistTrackIds = new Set();
  loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
}

function selectedTrackIdsOnCurrentPlaylist() {
  return currentPlaylistTracks
    .map((track) => track.id)
    .filter((trackId) => selectedPlaylistTrackIds.has(trackId));
}

async function resolveSelectedPlaylistTracks() {
  const trackIds = selectedTrackIdsOnCurrentPlaylist();
  if (!selectedPlaylistId || trackIds.length === 0) {
    playlistImportMessage.textContent = "Selectionne au moins une piste.";
    return;
  }
  playlistBatchResolve.disabled = true;
  playlistImportMessage.textContent = "Recherche en lot...";
  try {
    const response = await fetch(
      `/api/playlists/${encodeURIComponent(selectedPlaylistId)}/tracks/resolve-batch`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider_key: "youtube",
          limit: 5,
          tracks: trackIds.map((trackId) => ({ track_id: trackId })),
        }),
      },
    );
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "La recherche en lot a echoue."));
    }
    playlistImportMessage.textContent = batchSummary(body, "recherche");
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
  } catch (error) {
    playlistImportMessage.textContent = error.message;
  } finally {
    playlistBatchResolve.disabled = false;
  }
}

async function queueSelectedPlaylistTracks() {
  const selectedTracks = currentPlaylistTracks.filter((track) =>
    selectedPlaylistTrackIds.has(track.id)
  );
  const items = selectedTracks.flatMap((track) => {
    const candidate = firstUnqueuedCandidate(track);
    if (!candidate) {
      return [];
    }
    const payload = { track_id: track.id, candidate_id: candidate.id, format: playlistBatchFormat.value };
    if (playlistBatchFormat.value === "mp4") {
      payload.resolution = Number.parseInt(playlistBatchQuality.value, 10);
    } else {
      payload.audio_bitrate_kbps = Number.parseInt(playlistBatchQuality.value, 10);
    }
    return [payload];
  });
  if (!selectedPlaylistId || selectedTracks.length === 0) {
    playlistImportMessage.textContent = "Selectionne au moins une piste.";
    return;
  }
  if (items.length === 0) {
    playlistImportMessage.textContent = "Les pistes selectionnees n'ont pas de candidat disponible.";
    return;
  }
  playlistBatchQueue.disabled = true;
  playlistImportMessage.textContent = "Ajout en lot...";
  try {
    const response = await fetch(
      `/api/playlists/${encodeURIComponent(selectedPlaylistId)}/tracks/queue-batch`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      },
    );
    const body = await response.json();
    if (!response.ok) {
      throw new Error(apiErrorMessage(body.detail, "L'ajout en lot a echoue."));
    }
    playlistImportMessage.textContent = batchSummary(body, "ajout");
    await loadPlaylistDetail(selectedPlaylistId, selectedPlaylistOffset);
    await loadHistory();
  } catch (error) {
    playlistImportMessage.textContent = error.message;
  } finally {
    playlistBatchQueue.disabled = false;
  }
}

function firstUnqueuedCandidate(track) {
  const queuedCandidateIds = new Set((track.queue_items || []).map((item) => item.candidate_id));
  return (track.candidates || []).find((candidate) => !queuedCandidateIds.has(candidate.id));
}

function batchSummary(batch, label) {
  const queueFull = batch.stopped_on_queue_full ? " Queue pleine: traitement arrete." : "";
  return `${label}: ${batch.completed_count}/${batch.requested_count} OK, ${batch.failed_count} echec(s), ${batch.skipped_count} ignore(s).${queueFull}`;
}

function renderPlaylistSelectionStatus() {
  playlistSelectionStatus.textContent = `${selectedPlaylistTrackIds.size} piste(s) selectionnee(s)`;
}

function pagePlaylist(delta) {
  if (!selectedPlaylistId) {
    return;
  }
  const nextOffset = Math.max(0, selectedPlaylistOffset + delta);
  loadPlaylistDetail(selectedPlaylistId, nextOffset);
}

async function loadHistory() {
  const response = await fetch("/api/jobs?limit=12");
  if (!response.ok) {
    return;
  }
  const jobs = await response.json();
  historyList.replaceChildren(...jobs.map(historyItem));
}

function historyItem(job) {
  const item = document.createElement("li");
  item.className = "history-item";
  const summary = document.createElement("div");
  summary.className = "history-summary";

  const content = document.createElement("div");
  content.className = "history-content";
  const label = document.createElement("strong");
  label.textContent = job.title || job.requested_format.toUpperCase();
  const source = document.createElement("span");
  source.className = "history-source";
  source.textContent = job.source_url || "";
  content.append(label, source);

  const state = document.createElement("div");
  state.className = "history-actions";
  const statusText = document.createElement("span");
  statusText.textContent = job.download_url ? "" : job.status;
  if (job.download_url) {
    const link = document.createElement("a");
    link.href = job.download_url;
    setInlineContent(link, "Fichier", "file");
    state.append(link);
  } else {
    state.append(statusText);
    if (canPause(job)) {
      state.append(actionButton("Pause", () => pauseJob(job.id)));
    }
    if (canResume(job)) {
      state.append(actionButton("Reprendre", () => resumeJob(job.id)));
    }
  }
  const detailsId = `history-details-${job.id}`;
  const details = historyDetails(job);
  const detailsButton = actionButton("Details", () => {
    const isHidden = details.hidden;
    details.hidden = !isHidden;
    detailsButton.setAttribute("aria-expanded", String(isHidden));
  });
  detailsButton.setAttribute("aria-controls", detailsId);
  detailsButton.setAttribute("aria-expanded", "false");
  state.append(detailsButton);
  if (canDelete(job)) {
    state.append(actionButton("Supprimer", () => deleteJob(job.id)));
  }

  summary.append(content, state);
  details.id = detailsId;
  item.append(summary, details);
  return item;
}

function historyDetails(job) {
  const details = document.createElement("dl");
  details.className = "history-details";
  details.hidden = true;
  detailRows(job).forEach(([label, value]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    if (label === "URL") {
      const link = document.createElement("a");
      link.href = value;
      link.textContent = value;
      link.rel = "noreferrer";
      description.append(link);
    } else {
      description.textContent = value;
    }
    details.append(term, description);
  });
  return details;
}

function detailRows(job) {
  return [
    ["URL", job.source_url],
    ["Plateforme", job.platform],
    ["Format", formatRequestLabel(job)],
    ["Statut", job.status],
    ["Progression", Number.isFinite(job.progress_percent) ? `${formatNumber(job.progress_percent, 1)} %` : null],
    ["Transfert", transferLabel(job.downloaded_bytes, job.total_bytes)],
    ["Taille finale", sizeLabel(job.output_size_bytes, false)],
    ["Duree", durationLabel(job.duration_seconds)],
    ["Extrait", segmentDetailLabel(job)],
    ["Cree le", dateTimeLabel(job.created_at)],
    ["Termine le", dateTimeLabel(job.completed_at)],
    ["Erreur", apiErrorMessage(job.error, "")],
  ].filter((row) => row[1]);
}

function formatRequestLabel(job) {
  const parts = [job.requested_format?.toUpperCase()];
  if (Number.isFinite(job.requested_height)) {
    parts.push(`${job.requested_height}p`);
  }
  if (Number.isFinite(job.requested_audio_bitrate_kbps)) {
    parts.push(`${job.requested_audio_bitrate_kbps} kb/s`);
  }
  return parts.filter(Boolean).join(" ");
}

function segmentDetailLabel(job) {
  if (!Number.isFinite(job.segment_start_seconds) || !Number.isFinite(job.segment_end_seconds)) {
    return "";
  }
  return segmentRangeLabel({
    start_seconds: job.segment_start_seconds,
    end_seconds: job.segment_end_seconds,
  });
}

function actionButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "inline-action";
  setInlineContent(button, label, actionIcon(label));
  button.addEventListener("click", handler);
  return button;
}

function actionIcon(label) {
  const icons = {
    Details: "details",
    Pause: "pause",
    Reprendre: "play",
    Supprimer: "trash",
  };
  return icons[label] || "details";
}

loadHistory();
loadPlaylists();
