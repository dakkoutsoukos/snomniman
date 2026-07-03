"""The curated manual content - one ManualPage per major feature.

Organized the same way as :mod:`snomniman.knowledge.library`: one tuple per
category, assembled into :data:`PAGES` at the bottom. Pages explain **how** to
use a feature; they deliberately do not repeat the science (that lives in
``snomniman.knowledge`` and is reached via ``related_knowledge_articles``).

The set is *initial* and designed to grow - one page per new panel/operation/
export workflow, exactly as the Knowledge Center grows one article per new
operation/diagnostic. ``integrity_problems()`` and the "every registered
ProcessingStep has a manual page" test guard against drift.
"""

from __future__ import annotations

from .page import (
    AI,
    EXPLORER,
    EXPORT,
    GETTING_STARTED,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
    WORKSPACE,
    ManualPage,
)

# --------------------------------------------------------------------------- #
# Getting Started
# --------------------------------------------------------------------------- #

_GETTING_STARTED: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="getting_started.first_five_minutes",
        category=GETTING_STARTED,
        title="Your first five minutes",
        summary="A quick orientation tour for a measurement you have never seen before.",
        purpose=(
            "SNOMNIMAN is built so a new measurement explains itself: open it, and the "
            "Explorer already knows what channels exist, what the Scientific Briefing has "
            "to say about it, and what processing steps apply. This page is the shortest "
            "path from 'just opened a file' to 'I understand what I'm looking at'."
        ),
        steps=(
            "Open a measurement (File > Open Measurement...) - see 'Opening a measurement'.",
            "Look at the channel image that appears; use the Channels dock on the left to "
            "switch between harmonics/channels.",
            "Open the Briefing tab (right-hand Inspect dock) and read the Scientific "
            "Briefing - a deterministic orientation to the measurement.",
            "Scroll to Suggested Next Steps on the same tab: each card is a grounded, "
            "explainable recommendation - click 'Preview' to try one in the Processing "
            "Workspace, or 'Learn more' / 'How to use this' to understand it first.",
            "Check the Diagnostics and Metadata tabs for computed facts and instrument "
            "metadata.",
            "When you're ready to search for anything else, press F1 to open the Manual.",
        ),
        related_pages=(
            "explorer.channel_browser",
            "explorer.diagnostics",
            "ai.scientific_briefing",
            "workspace.overview",
        ),
    ),
    ManualPage(
        page_id="getting_started.opening_a_measurement",
        category=GETTING_STARTED,
        title="Opening a measurement",
        summary="Load a neaSNOM measurement directory, or reopen a saved project.",
        purpose=(
            "SNOMNIMAN reads a vendor measurement directory directly (no conversion step) "
            "and can also reopen a previously saved SNOMNIMAN project (a `.snomproj` "
            "bundle) exactly where you left off, including its full processing history."
        ),
        steps=(
            "File > Open Measurement... (Ctrl+O) - pick a neaSNOM measurement folder to "
            "start a new project with that one measurement.",
            "File > Add Measurement... (Ctrl+Shift+A) - add another measurement to the "
            "currently open project (see 'The Measurement Manager').",
            "File > Open Project... (Ctrl+Shift+O) - reopen a saved `.snomproj` bundle: "
            "every measurement, its processing history, view state, and overlays return "
            "exactly as saved.",
            "File > New Project (Ctrl+N) - start over with an empty project.",
        ),
        related_pages=(
            "getting_started.first_five_minutes",
            "getting_started.opening_a_spectrum",
            "explorer.measurement_manager",
            "shortcuts.reference",
        ),
        related_knowledge_articles=("concept.immutable_measurements",),
    ),
    ManualPage(
        page_id="getting_started.opening_a_spectrum",
        category=GETTING_STARTED,
        title="Opening a spectrum",
        summary=(
            "Point-spectroscopy and hyperspectral measurements open the same way as "
            "images - the Explorer adapts its affordances honestly to what the data is."
        ),
        purpose=(
            "A point spectrum, a line of spectra, or a hyperspectral cube is opened with "
            "the same File > Open Measurement... dialog as an image. SNOMNIMAN detects the "
            "data kind from the measurement itself and switches the central view and the "
            "available tools accordingly - it never guesses or forces image-only tools "
            "onto spectral data."
        ),
        steps=(
            "File > Open Measurement... and pick a point-spectroscopy or hyperspectral "
            "measurement folder, exactly as for an image.",
            "A single point spectrum or a line scan opens in the spectrum plot view; a "
            "hyperspectral cube opens in the linked band-map + spectrum view - click a "
            "pixel to see its spectrum, or select a region to see the mean spectrum.",
            "Image-only affordances (Measure ROI drawing on a 2-D image, Comparison mode, "
            "the contact sheet, GSF channel export) decline honestly with an explanatory "
            "message rather than crashing or silently doing the wrong thing - see "
            "'Why is this export/tool disabled?'.",
        ),
        related_pages=(
            "getting_started.opening_a_measurement",
            "troubleshooting.export_disabled_for_spectrum",
        ),
        related_knowledge_articles=("concept.point_spectrum", "concept.hyperspectral_cube"),
    ),
)

# --------------------------------------------------------------------------- #
# Explorer
# --------------------------------------------------------------------------- #

_EXPLORER: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="explorer.channel_browser",
        category=EXPLORER,
        title="The Channel Browser",
        summary="The left-hand dock listing every channel/harmonic in the active measurement.",
        purpose=(
            "A single neaSNOM measurement usually contains many channels: topography, "
            "several optical harmonics (O0, O1, O2, ...) each with amplitude and phase, "
            "and reference channels. The Channel Browser is how you move between them "
            "without leaving the current view."
        ),
        steps=(
            "Click a channel in the Channels dock to display it in the central view.",
            "The list updates automatically when you switch the active measurement in the "
            "Measurement Manager, or after a processing operation adds a new derived "
            "channel to the history.",
        ),
        related_pages=("explorer.measurement_manager", "explorer.comparison_mode"),
        related_knowledge_articles=("concept.harmonics", "concept.near_field_microscopy"),
    ),
    ManualPage(
        page_id="explorer.comparison_mode",
        category=EXPLORER,
        title="Comparison mode",
        summary="View two or more channels side by side instead of one at a time.",
        purpose=(
            "Comparison mode replaces the single-channel view with a linked side-by-side "
            "layout, so you can judge amplitude against phase, or a raw channel against a "
            "processed one, without mentally holding one image in memory while looking at "
            "the other."
        ),
        steps=(
            "Above the central view, click one of the 'Compare:' preset buttons (each "
            "preset picks a useful pair/group of channels automatically).",
            "Click 'Single' to return to the one-channel view.",
            "Click 'Contact sheet' to see every harmonic at once instead of a chosen pair.",
        ),
        related_pages=("explorer.channel_browser",),
    ),
    ManualPage(
        page_id="explorer.measurement_manager",
        category=EXPLORER,
        title="The Measurement Manager",
        summary="The left-hand dock that turns a project into a collection of measurements.",
        purpose=(
            "A SNOMNIMAN project can hold more than one measurement at once. The "
            "Measurement Manager lists every measurement in the open project, lets you "
            "switch the active one (its processing history, view, and overlays are "
            "preserved, with no disk reload), and doubles as a lightweight experiment "
            "browser for multi-select actions."
        ),
        steps=(
            "Click a measurement to make it active in the central view and Inspect tabs.",
            "Use Add/Close (or the File menu equivalents) to grow or shrink the project.",
            "Multi-select measurements to Compare them side by side (reuses the Comparison "
            "viewer), or to run a batch recipe across the selection.",
            "'Compare active overlay across measurements' overlays the same measurement or "
            "line/ROI selection across every selected measurement.",
        ),
        related_pages=(
            "getting_started.opening_a_measurement",
            "workspace.batch",
            "explorer.experiment_tab",
        ),
        related_knowledge_articles=("concept.immutable_measurements", "concept.provenance"),
    ),
    ManualPage(
        page_id="explorer.metadata",
        category=EXPLORER,
        title="The Metadata tab",
        summary="Shows the instrument/acquisition metadata attached to the active measurement.",
        purpose=(
            "Every measurement carries metadata read from the vendor file - acquisition "
            "parameters, conventions (units, coordinate origin), and instrument settings. "
            "The Metadata tab is a read-only, structured view of exactly what was recorded; "
            "SNOMNIMAN never guesses a missing value, it shows it as unknown."
        ),
        steps=("Select the Metadata tab in the Inspect dock while any measurement is active.",),
        related_pages=("explorer.provenance",),
    ),
    ManualPage(
        page_id="explorer.provenance",
        category=EXPLORER,
        title="The Provenance tab",
        summary="Shows the full derivation graph (DAG) behind the currently displayed dataset.",
        purpose=(
            "Every processed dataset in SNOMNIMAN is a node in a provenance DAG that "
            "records its raw source(s), every processing step applied, their parameters, "
            "and software/operation versions. The Provenance tab renders that DAG for the "
            "active channel, so you can always answer 'exactly how was this produced?'."
        ),
        steps=(
            "Select the Provenance tab while a processed (non-raw) channel is displayed.",
            "Each node shows the step, its parameters, and version; raw sources show the "
            "file path and a sha256 hash.",
            "For a portable, prose + machine-readable version of the same information, use "
            "'Generate Reproducibility Report...' on the Experiment tab.",
        ),
        related_pages=("explorer.experiment_tab", "workspace.overview"),
        related_knowledge_articles=("concept.provenance",),
    ),
    ManualPage(
        page_id="explorer.diagnostics",
        category=EXPLORER,
        title="The Diagnostics tab",
        summary="Deterministic, computed facts about the active channel - never an opinion.",
        purpose=(
            "The Diagnostics tab surfaces quantities SNOMNIMAN computes directly from the "
            "data: tilt/slope, RMS roughness, harmonic amplitude decay, a signal-vs-noise "
            "classification per harmonic, dynamic range/statistics, and a value-distribution "
            "histogram. These are observations, not recommendations - the AI Scientist's "
            "Suggested Next Steps reasons over these same facts, but the Diagnostics tab "
            "itself never tells you what to do."
        ),
        steps=(
            "Select the Diagnostics tab while any measurement is active; values update for "
            "whichever channel/measurement is currently focused.",
            "Use the histogram to see the value distribution of the active channel.",
        ),
        related_pages=("ai.scientific_briefing", "explorer.measure_panel"),
        related_diagnostics=(
            "topography_slope",
            "rms_roughness",
            "harmonic_decay",
            "harmonic_signal_noise",
            "dynamic_range",
        ),
        related_knowledge_articles=("concept.histogram",),
    ),
    ManualPage(
        page_id="explorer.experiment_tab",
        category=EXPLORER,
        title="The Experiment tab",
        summary="Project-wide, cross-measurement view: diagnostics table, batch results, reports.",
        purpose=(
            "Where the other Inspect tabs describe one measurement, the Experiment tab "
            "aggregates the whole open project: a diagnostics table across every "
            "measurement, cross-measurement ROI/line statistics, the results of the most "
            "recent batch recipe run, and the entry points for generating the three report "
            "documents. It creates nothing new - it is a read-only projection of "
            "information the rest of the app already computed."
        ),
        steps=(
            "Select the Experiment tab; it reflects whichever measurements are selected in "
            "the Measurement Manager.",
            "Use 'Export CSV...' to save the cross-measurement statistics table.",
            "After a batch run (see 'Batch processing'), its per-measurement outcomes "
            "appear here as a 'Batch results' section.",
            "Use 'Generate Experiment Report...', 'Generate Publication Package...', or "
            "'Generate Reproducibility Report...' to produce a document - see 'Export' for "
            "details on each.",
        ),
        related_pages=("explorer.measurement_manager", "workspace.batch", "export.reports"),
        related_knowledge_articles=("concept.scientific_reporting",),
    ),
    ManualPage(
        page_id="explorer.measure_panel",
        category=EXPLORER,
        title="The Measure tab",
        summary="Draw a line profile or a region (ROI) and read off quantitative numbers.",
        purpose=(
            "The Measure tab is how you get numbers out of an image or spectrum instead of "
            "just looking at it: line-profile peak/width/spacing features, region "
            "statistics, region-vs-region comparison, and - for spectral measurements - "
            "ROI spectrum overlays. Every result can be copied or exported to CSV with a "
            "provenance header."
        ),
        steps=(
            "Select the Measure tab, then draw a line or a rectangular ROI on the central "
            "image (or, for a spectral measurement, on the spectrum/band map).",
            "Read the computed numbers in the panel: for a line, peak/width/spacing; for a "
            "region, statistics; select two regions to compare them.",
            "For spectral measurements, use 'Overlay ROI spectra' to plot the mean spectrum "
            "of each selected region together.",
            "Click 'Copy' to copy the numbers, or 'Export CSV...' to save them with a "
            "provenance-header CSV (includes a `wavenumber_cm1` column for spectral ROIs).",
        ),
        related_pages=("explorer.diagnostics", "export.csv"),
        related_knowledge_articles=("concept.profile_analysis", "concept.region_comparison"),
    ),
)

# --------------------------------------------------------------------------- #
# Processing Workspace
# --------------------------------------------------------------------------- #

_WORKSPACE_CORE: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="workspace.overview",
        category=WORKSPACE,
        title="The Processing Workspace",
        summary=(
            "One generic surface for every processing operation: Preview, then Accept "
            "or Cancel."
        ),
        purpose=(
            "Every registered operation - from a simple plane fit to a two-measurement "
            "arithmetic combination - runs through this one workspace, never a bespoke "
            "dialog. It lists every operation (grouped, with unavailable ones greyed out "
            "and a plain-English reason why), builds the parameter form automatically from "
            "the operation's declared parameters, and always follows the same lifecycle: "
            "Preview shows exactly what will change before anything is committed."
        ),
        steps=(
            "Select the Process tab. The tree lists every operation grouped by namespace "
            "(e.g. 'image', 'spectrum'), plus a 'Recipes' group.",
            "Click an operation to see its description, requirements, version, and - if "
            "unavailable for the current channel - the reason why (e.g. a missing "
            "capability, or it has already been applied).",
            "For a multi-input operation (e.g. Arithmetic), the 'Inputs' group appears - "
            "pick the other measurement(s) it needs from the dropdowns.",
            "Fill in the 'Parameters' form (auto-generated from the operation's own "
            "parameter definitions - a checkbox for a flag, a spin box for a number, a "
            "combo box for a choice, etc.).",
            "Click Preview: a 'What will change' / 'What stays the same' / 'Provenance to "
            "be recorded' summary appears, and the form locks.",
            "Click Accept to commit the result as a new derived dataset (the raw "
            "measurement is never modified), or Cancel to discard the preview and keep "
            "editing.",
            "The channel/measurement's full history is visible in Provenance at any time.",
        ),
        related_pages=("workspace.recipes", "workspace.batch", "explorer.provenance"),
        related_knowledge_articles=("concept.immutable_measurements", "concept.provenance"),
    ),
    ManualPage(
        page_id="workspace.recipes",
        category=WORKSPACE,
        title="Processing recipes",
        summary=(
            "Capture a measurement's processing history as a portable, reusable, "
            "named sequence."
        ),
        purpose=(
            "A recipe is a named `(operation, version, parameters)` sequence captured from "
            "a measurement's existing history. It is not a second processing engine - "
            "replaying a recipe just loops the same operations you could apply by hand, "
            "recording the identical provenance. Recipes are how you apply the same "
            "processing to many measurements consistently."
        ),
        steps=(
            "With a processed measurement active, open the Process tab and click 'Save "
            "current history as recipe...'; give it a name. It is saved as a portable "
            "`.snomrecipe` file.",
            "Click 'Load recipe...' to bring a saved recipe into the tree as a second kind "
            "of item alongside operations.",
            "Select a recipe in the tree to inspect its steps, then Preview/Accept/Cancel "
            "it exactly like a single operation - it either applies cleanly to the current "
            "measurement or is skipped with an honest reason if incompatible.",
            "Select a recipe and click 'Delete this recipe' to remove it.",
            "To run one recipe across many measurements at once, see 'Batch processing'.",
        ),
        related_pages=("workspace.overview", "workspace.batch"),
        related_knowledge_articles=("concept.processing_recipe",),
    ),
    ManualPage(
        page_id="workspace.batch",
        category=WORKSPACE,
        title="Batch processing",
        summary="Replay one recipe across many measurements, independently, with live progress.",
        purpose=(
            "Batch processing is a thin orchestration layer over recipe replay - it loops "
            "the same 'apply a recipe' logic across a set of measurements, one at a time. "
            "Each measurement's outcome is recorded honestly as success, skipped (an "
            "expected incompatibility - not an error), or failed (a genuinely unexpected "
            "error); no outcome aborts the run for the remaining measurements."
        ),
        steps=(
            "In the Measurement Manager, select 'All' or select specific measurements.",
            "Trigger a batch run (from the Measurement Manager's batch action); choose "
            "which saved recipe to apply and confirm.",
            "A progress dialog shows live progress and lets you request a clean stop "
            "between measurements.",
            "When it finishes, the per-measurement outcomes appear in the Experiment tab's "
            "'Batch results' section.",
        ),
        related_pages=(
            "workspace.recipes",
            "explorer.measurement_manager",
            "explorer.experiment_tab",
        ),
        related_knowledge_articles=("concept.processing_recipe",),
    ),
)

_WORKSPACE_OPERATIONS: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="workspace.image.plane_level",
        category=WORKSPACE,
        title="Plane Level (how to use it)",
        summary="Fit and subtract a polynomial surface from a real-valued channel.",
        purpose="Removes global tilt or bow from a topography (or other real) channel.",
        steps=(
            "Select 'image.plane_level' in the Process tab tree (available for real-valued "
            "channels, typically Z/topography).",
            "Set 'channel' if it did not default to the one you want.",
            "Set 'order' (1 = plane, 2/3 = a fitted bowl/higher-order surface).",
            "Preview, check the residual in the summary, then Accept or Cancel.",
        ),
        related_pages=("workspace.overview", "workspace.image.line_flatten"),
        related_knowledge_articles=("operation.image.plane_level",),
        related_operations=("image.plane_level",),
        related_diagnostics=("topography_slope", "rms_roughness"),
    ),
    ManualPage(
        page_id="workspace.image.line_flatten",
        category=WORKSPACE,
        title="Line Flatten (how to use it)",
        summary="Remove a per-scan-line baseline from a real-valued channel.",
        purpose=(
            "Corrects line-to-line offsets (scan artifacts) that a single global plane fit "
            "cannot - a different, complementary tool to Plane Level, not a replacement."
        ),
        steps=(
            "Select 'image.line_flatten' in the tree.",
            "Set 'channel', then 'method' (median / mean / polynomial baseline per line).",
            "If 'method' is polynomial, set 'order'.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=("workspace.overview", "workspace.image.plane_level"),
        related_knowledge_articles=("operation.image.line_flatten",),
        related_operations=("image.line_flatten",),
    ),
    ManualPage(
        page_id="workspace.image.fix_zero",
        category=WORKSPACE,
        title="Fix Zero (how to use it)",
        summary="Shift a real-valued channel so a chosen reference sits at zero.",
        purpose="Sets a height datum (the zero point of a topography/real channel).",
        steps=(
            "Select 'image.fix_zero' in the tree.",
            "Set 'channel'.",
            "Choose 'reference': minimum, mean, or median - the value that becomes zero.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=("operation.image.fix_zero",),
        related_operations=("image.fix_zero",),
    ),
    ManualPage(
        page_id="workspace.image.reference_normalize",
        category=WORKSPACE,
        title="Reference Normalize (how to use it)",
        summary="Normalize an optical channel by its matching reference channel, automatically.",
        purpose=(
            "Divides an O{n} channel by its matching R_O{n} reference; it needs no "
            "parameters - it auto-detects the matching pairs present in the measurement."
        ),
        steps=(
            "Select 'image.reference_normalize' in the tree (available only when a "
            "matching reference channel exists).",
            "There are no parameters to set - Preview to see exactly which pair it will "
            "use, then Accept or Cancel.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=("operation.image.reference_normalize",),
        related_operations=("image.reference_normalize",),
    ),
    ManualPage(
        page_id="workspace.image.phase_offset",
        category=WORKSPACE,
        title="Phase Offset (how to use it)",
        summary="Re-reference a complex channel's phase by a constant offset.",
        purpose=(
            "Shifts the phase origin without altering amplitude or the phase "
            "relationships within the image."
        ),
        steps=(
            "Select 'image.phase_offset' in the tree (available for complex/optical "
            "channels).",
            "Set 'channel' (required).",
            "Choose 'reference': subtract the image mean, or a fixed 'value_rad' you enter "
            "directly.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=("workspace.overview", "workspace.image.region_phase_reference"),
        related_knowledge_articles=("operation.image.phase_offset",),
        related_operations=("image.phase_offset",),
    ),
    ManualPage(
        page_id="workspace.image.normalize_amplitude",
        category=WORKSPACE,
        title="Normalize Amplitude (how to use it)",
        summary="Rescale a complex channel's amplitude to a chosen reference value.",
        purpose=(
            "Puts amplitude on a comparable scale (e.g. across measurements) without "
            "touching phase."
        ),
        steps=(
            "Select 'image.normalize_amplitude' in the tree (complex/optical channels).",
            "Set 'channel' (required).",
            "Choose 'reference': the image maximum, or the image mean.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=("workspace.overview", "workspace.image.region_amplitude_reference"),
        related_knowledge_articles=("operation.image.normalize_amplitude",),
        related_operations=("image.normalize_amplitude",),
    ),
    ManualPage(
        page_id="workspace.image.phase_unwrap",
        category=WORKSPACE,
        title="Phase Unwrap (how to use it)",
        summary="Produce a continuous (unwrapped) phase channel from a wrapped one.",
        purpose=(
            "Unwrapped phase is always its own new channel, produced only by this explicit "
            "operation - phase is never silently unwrapped."
        ),
        steps=(
            "Select 'image.phase_unwrap' in the tree (complex/optical channels).",
            "Set 'channel' (required) - there are no other parameters.",
            "Preview: check the result for unwrapping artifacts before accepting.",
            "Accept to add the new unwrapped-phase channel, or Cancel.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=("operation.image.phase_unwrap",),
        related_operations=("image.phase_unwrap",),
    ),
    ManualPage(
        page_id="workspace.image.crop",
        category=WORKSPACE,
        title="Crop (how to use it)",
        summary="Trim a channel to a rectangular sub-region.",
        purpose="Restricts subsequent viewing/processing/export to a chosen sub-area.",
        steps=(
            "Select 'image.crop' in the tree.",
            "Set 'x_min' / 'x_max' / 'y_min' / 'y_max' (all required).",
            "Preview to check the cropped extent, then Accept or Cancel.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=("operation.image.crop",),
        related_operations=("image.crop",),
    ),
    ManualPage(
        page_id="workspace.image.arithmetic",
        category=WORKSPACE,
        title="Arithmetic (how to use it)",
        summary="Combine two measurements' channels: A-B, B-A, or |A-B|.",
        purpose=(
            "The first two-input operation in SNOMNIMAN - it needs a second measurement, "
            "not just a second parameter."
        ),
        steps=(
            "Open (or Add) both measurements you want to combine into the same project.",
            "Select 'image.arithmetic' in the tree; the 'Inputs' group appears.",
            "Pick 'Measurement A' and 'Measurement B' from the dropdowns (they list other "
            "open measurements).",
            "Set 'channel' and 'mode' (a_minus_b / b_minus_a / absolute_difference).",
            "Preview and Accept/Cancel; the result is recorded in the primary "
            "measurement's history with both parents in its provenance.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=("operation.image.arithmetic",),
        related_operations=("image.arithmetic",),
    ),
    ManualPage(
        page_id="workspace.image.region_phase_reference",
        category=WORKSPACE,
        title="Region Phase Reference (how to use it)",
        summary="Re-reference phase using the mean phase inside a chosen rectangular region.",
        purpose=(
            "A region-aware alternative to Phase Offset when you want to reference "
            "against a specific area (e.g. a known-flat substrate) rather than the "
            "whole image."
        ),
        steps=(
            "In the Measure tab (or directly in the Process tab's ROI picker), draw the "
            "rectangular region you want to reference against.",
            "Select 'image.region_phase_reference' in the tree; set 'channel' and the "
            "region bounds (x_min/x_max/y_min/y_max) - the ROI picker fills these from your "
            "drawn region.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=(
            "workspace.overview",
            "workspace.image.phase_offset",
            "explorer.measure_panel",
        ),
        related_knowledge_articles=("operation.image.region_phase_reference",),
        related_operations=("image.region_phase_reference",),
    ),
    ManualPage(
        page_id="workspace.image.region_amplitude_reference",
        category=WORKSPACE,
        title="Region Amplitude Reference (how to use it)",
        summary="Normalize amplitude using the mean amplitude inside a chosen rectangular region.",
        purpose=(
            "A region-aware alternative to Normalize Amplitude for referencing "
            "against a specific area instead of the whole image."
        ),
        steps=(
            "Draw the rectangular region to reference against (Measure tab or the "
            "Process tab's ROI picker).",
            "Select 'image.region_amplitude_reference' in the tree; set 'channel' and the "
            "region bounds.",
            "Preview and Accept/Cancel.",
        ),
        related_pages=(
            "workspace.overview",
            "workspace.image.normalize_amplitude",
            "explorer.measure_panel",
        ),
        related_knowledge_articles=("operation.image.region_amplitude_reference",),
        related_operations=("image.region_amplitude_reference",),
    ),
    ManualPage(
        page_id="workspace.spectrum.fft_interferogram",
        category=WORKSPACE,
        title="FFT Interferogram (how to use it)",
        summary=(
            "Transform an interferogram into a spectrum via apodization, zero-fill, "
            "phase correction, and FFT."
        ),
        purpose=(
            "The one operation whose output is a different kind of data than its input - "
            "an interferogram in, a spectrum out."
        ),
        steps=(
            "Select 'spectrum.fft_interferogram' in the tree (available for interferometric "
            "measurements).",
            "Set 'channel'.",
            "Choose 'apodization' (a windowing function; the default is a 3-term "
            "Blackman-Harris window).",
            "Set 'zero_fill' (extra zero-padding factor) and 'phase_correction' (default "
            "'mertz').",
            "Preview the resulting spectrum, then Accept or Cancel.",
        ),
        related_pages=("workspace.overview",),
        related_knowledge_articles=(
            "operation.spectrum.fft_interferogram",
            "concept.interferogram",
            "concept.apodization",
        ),
        related_operations=("spectrum.fft_interferogram",),
    ),
)

_WORKSPACE: tuple[ManualPage, ...] = _WORKSPACE_CORE + _WORKSPACE_OPERATIONS

# --------------------------------------------------------------------------- #
# AI (the AI Scientist as seen in the UI)
# --------------------------------------------------------------------------- #

_AI: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="ai.scientific_briefing",
        category=AI,
        title="Reading the Scientific Briefing",
        summary="A deterministic, text orientation to the active measurement, on the Briefing tab.",
        purpose=(
            "The Briefing composes the Description API and Diagnostics Engine into a "
            "single readable orientation - what the measurement is, what its computed "
            "facts show - entirely from deterministic sources. It is not model-generated "
            "prose about the raw pixels."
        ),
        steps=(
            "Select the Briefing tab while a measurement is active.",
            "Read the briefing text at the top - it updates for whichever measurement/"
            "channel is focused.",
            "Scroll down to Suggested Next Steps - see 'Suggested Next Steps' for how to "
            "use those cards.",
        ),
        related_pages=("ai.suggested_next_steps", "explorer.diagnostics"),
        related_knowledge_articles=("ai.scientific_briefing",),
    ),
    ManualPage(
        page_id="ai.suggested_next_steps",
        category=AI,
        title="Suggested Next Steps",
        summary=(
            "Ranked, explainable recommendation cards - and why some operations "
            "never appear as one."
        ),
        purpose=(
            "Each card is produced by a deterministic rule reasoning over the Diagnostics "
            "Engine's computed facts, not inferred from the raw array by a model. A card "
            "only appears when a rule's applicability/prerequisite/exclusion conditions are "
            "met and the operation has not already been applied; an operation with no "
            "validated recommendation rule (or whose conditions are not met) simply never "
            "produces a card - that is not a bug, it is the deterministic engine declining "
            "to guess."
        ),
        steps=(
            "On the Briefing tab, each card shows: the recommended operation, a strength "
            "badge, a rationale, an evidence ('Why:') list, the expected outcome, and any "
            "caveats ('Consider:').",
            "Click 'Preview' to open that operation in the Processing Workspace, "
            "pre-filled with the recommended parameters - it still goes through the same "
            "Preview -> Accept/Cancel lifecycle, it is never applied automatically.",
            "Click 'Learn more' for the scientific background (opens the matching "
            "Knowledge Center article), or 'How to use this' for the operation's own "
            "Manual page.",
            "If an operation you expected to see recommended is missing, it may be already "
            "applied, its prerequisites unmet, or - honestly - no validated recommendation "
            "rule exists for it yet; every operation is still reachable directly from the "
            "Process tab regardless.",
        ),
        related_pages=(
            "ai.scientific_briefing",
            "ai.reasoning_and_provenance",
            "workspace.overview",
        ),
        related_knowledge_articles=("ai.suggested_next_steps", "ai.deterministic_reasoning"),
    ),
    ManualPage(
        page_id="ai.reasoning_and_provenance",
        category=AI,
        title="Why the AI never decides for you",
        summary="What 'recommend, never execute' looks like in the running app.",
        purpose=(
            "SNOMNIMAN's AI features only ever produce a recommendation card or briefing "
            "text; the only thing that ever changes a dataset is you clicking Accept in the "
            "Processing Workspace. This page is about that boundary as you'll actually see "
            "it in the UI, not the underlying rule-engine design (see the linked Knowledge "
            "articles for that)."
        ),
        steps=(
            "A Suggested Next Steps card never runs anything by itself - 'Preview' only "
            "opens the Processing Workspace pre-filled; you still Accept or Cancel.",
            "The Briefing text is generated from `describe` + `diagnostics` output, not "
            "read from the raw array by a model - if you disable/have no narrative "
            "provider configured, the facts and recommendations are unchanged (only the "
            "prose framing differs).",
            "Every operation's provenance node records exactly what ran and with what "
            "parameters, whether you started from a recommendation card or picked the "
            "operation yourself - see the Provenance tab.",
        ),
        related_pages=("ai.suggested_next_steps", "explorer.provenance"),
        related_knowledge_articles=("ai.deterministic_reasoning", "ai.why_ai_does_not_decide"),
    ),
)

# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #

_EXPORT: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="export.zarr",
        category=EXPORT,
        title="Exporting processed data (Zarr)",
        summary="Save the full processed dataset, loss-lessly, as a Zarr store.",
        purpose=(
            "The canonical, round-trip-exact way to hand off a dataset to another "
            "SNOMNIMAN session or a script."
        ),
        steps=(
            "File > Export > Processed Data (Zarr)...",
            "Choose a destination; the whole dataset (every channel, coordinates, and "
            "metadata) is written loss-lessly.",
        ),
        related_pages=("export.gsf", "explorer.provenance"),
    ),
    ManualPage(
        page_id="export.gsf",
        category=EXPORT,
        title="Exporting a channel (GSF)",
        summary=(
            "Export one channel's grid as a Gwyddion Simple Field file, with a "
            "provenance sidecar."
        ),
        purpose=(
            "GSF is a widely supported grid format (e.g. Gwyddion); the sidecar file "
            "carries the provenance a plain GSF grid cannot, so the exported grid remains "
            "traceable outside SNOMNIMAN."
        ),
        steps=(
            "Display the channel you want to export.",
            "File > Export > Channel (GSF)... and choose a destination.",
            "Not available for point-spectroscopy measurements (there is no 2-D grid to "
            "export) - see 'Why is this export disabled?'.",
        ),
        related_pages=("export.zarr", "troubleshooting.export_disabled_for_spectrum"),
    ),
    ManualPage(
        page_id="export.csv",
        category=EXPORT,
        title="Exporting measurement numbers (CSV)",
        summary=(
            "Export line-profile, region, or cross-measurement statistics as "
            "provenance-headed CSV."
        ),
        purpose=(
            "Every numeric result in SNOMNIMAN can leave the app as a CSV file with a "
            "commented provenance header (source, sha256, conventions, provenance chain, "
            "software version, timestamp) - a spreadsheet with an audit trail attached."
        ),
        steps=(
            "From the Measure tab: 'Copy' copies the current numbers, 'Export CSV...' "
            "saves them (includes a `wavenumber_cm1` column for spectral ROIs).",
            "From File > Export > Measurement (CSV)...: exports the Measure tab's current "
            "result the same way.",
            "From the Experiment tab: 'Export CSV...' saves the cross-measurement "
            "diagnostics/statistics table instead.",
        ),
        related_pages=("explorer.measure_panel", "explorer.experiment_tab"),
    ),
    ManualPage(
        page_id="export.figure",
        category=EXPORT,
        title="Exporting a figure",
        summary=(
            "Export the current view as a publication-quality PDF, PNG, or SVG, "
            "with a provenance sidecar."
        ),
        purpose=(
            "Turns whatever is on screen into a citable, reproducible figure file - "
            "vector formats included."
        ),
        steps=(
            "Click 'Export figure...' in the view-control row above the central view, or "
            "File > Export > Figure...",
            "Choose a format (PDF/PNG/SVG) and a destination; a provenance sidecar file is "
            "written alongside it.",
        ),
        related_pages=("export.reports",),
    ),
    ManualPage(
        page_id="export.reports",
        category=EXPORT,
        title="Generating a report",
        summary="Three deterministic documents composed entirely from already-computed facts.",
        purpose=(
            "Reports never introduce new science or AI interpretation - they format facts "
            "the app already computed (metadata, diagnostics, processing history, applied "
            "recipes, batch runs, ROI/profile/histogram summaries) into a shareable "
            "document. PDF is not offered (a laid-out document format is a heavyweight "
            "dependency with no present justification); a figure already exports as vector "
            "PDF separately - see 'Exporting a figure'."
        ),
        steps=(
            "On the Experiment tab, choose one of: 'Generate Experiment Report...' (a full "
            "project summary), 'Generate Publication Package...' (a curated subset for a "
            "paper/SI: metadata, tables, already-exported figures), or 'Generate "
            "Reproducibility Report...' (for one measurement: how exactly it was produced, "
            "in prose plus the machine-readable provenance DAG as an appendix).",
            "Pick a destination file; the extension you choose (`.md` or `.html`) selects "
            "the output format.",
        ),
        related_pages=("explorer.experiment_tab", "explorer.provenance", "export.figure"),
        related_knowledge_articles=("concept.scientific_reporting",),
    ),
)

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #

_SETTINGS: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="settings.overview",
        category=SETTINGS,
        title="Settings",
        summary="SNOMNIMAN currently has no configurable settings or preferences.",
        purpose=(
            "This page exists so 'Settings' is honestly answered rather than silently "
            "missing from the Manual: there is no Settings/Preferences dialog today, and "
            "window layout/geometry and recent-file history are not persisted between "
            "sessions. Every project's full state instead persists explicitly via File > "
            "Save Project - see 'Opening a measurement'. If configurable options are added "
            "in the future, this page documents them."
        ),
        steps=(),
        related_pages=("getting_started.opening_a_measurement",),
    ),
)

# --------------------------------------------------------------------------- #
# Shortcuts
# --------------------------------------------------------------------------- #

_SHORTCUTS: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="shortcuts.reference",
        category=SHORTCUTS,
        title="Keyboard shortcut reference",
        summary="Every keyboard shortcut currently wired in SNOMNIMAN.",
        purpose="A complete reference, kept in sync with the File and Help menus - not a guess.",
        steps=(
            "Ctrl+N - New Project",
            "Ctrl+Shift+O - Open Project...",
            "Ctrl+O - Open Measurement...",
            "Ctrl+Shift+A - Add Measurement...",
            "Ctrl+S - Save Project",
            "Ctrl+Shift+S - Save Project As...",
            "Ctrl+Q - Exit",
            "F1 - Open the Manual (and focus its search box)",
        ),
        related_pages=("getting_started.opening_a_measurement",),
    ),
)

# --------------------------------------------------------------------------- #
# Troubleshooting
# --------------------------------------------------------------------------- #

_TROUBLESHOOTING: tuple[ManualPage, ...] = (
    ManualPage(
        page_id="troubleshooting.operation_unavailable",
        category=TROUBLESHOOTING,
        title="Why is an operation greyed out in the Process tab?",
        summary=(
            "The Workspace always tells you why, in plain language - it never just "
            "hides the option."
        ),
        purpose=(
            "An operation is unavailable for one of a small number of honest reasons: the "
            "active channel is missing a capability the operation requires (e.g. it needs a "
            "complex/optical channel and you have topography selected), it has already been "
            "applied earlier in this channel's history, or (for multi-input operations) no "
            "compatible second measurement is open."
        ),
        steps=(
            "Click the greyed-out operation in the tree anyway - its detail panel states "
            "the specific reason it is unavailable.",
            "For a capability mismatch, switch to a channel that has the required "
            "capability (e.g. select an optical amplitude/phase channel, not topography).",
            "For a multi-input operation, open/add the second measurement first.",
        ),
        related_pages=("workspace.overview",),
    ),
    ManualPage(
        page_id="troubleshooting.preview_shows_no_change",
        category=TROUBLESHOOTING,
        title="Why does Preview show no visible change?",
        summary="Usually the operation genuinely had nothing to correct - not a bug.",
        purpose=(
            "Some operations are corrective (e.g. Plane Level on an already-flat surface, "
            "Fix Zero when the reference is already at zero): if the input already "
            "satisfies the operation's goal, the preview is legitimately a near-identity "
            "transform. Read the preview's 'What will change' text, which states this "
            "explicitly rather than leaving you to guess."
        ),
        steps=(
            "Read the Preview panel's 'What will change' section before assuming nothing "
            "happened.",
            "Check the Provenance tab after Accept - the new node's parameters confirm "
            "exactly what was computed, even if the visual difference is small.",
        ),
        related_pages=("workspace.overview", "explorer.provenance"),
    ),
    ManualPage(
        page_id="troubleshooting.export_disabled_for_spectrum",
        category=TROUBLESHOOTING,
        title="Why is GSF export / Comparison / the contact sheet disabled?",
        summary="Image-only tools honestly decline for point-spectroscopy and hyperspectral data.",
        purpose=(
            "GSF export, Comparison mode, and the harmonic contact sheet all assume a "
            "single 2-D image grid. A point spectrum, a line of spectra, or a "
            "hyperspectral cube is not that - rather than silently doing the wrong thing or "
            "crashing, these tools decline with an explanatory message. This is a "
            "deliberate scope boundary, not a missing feature to work around."
        ),
        steps=(
            "For a hyperspectral cube, use the linked band-map + spectrum view instead "
            "(click a pixel or select an ROI to see its spectrum) - GSF export works on "
            "whichever band is currently displayed.",
            "For a point spectrum/line scan, use the spectrum plot view and the Measure "
            "tab's spectral mode ('Overlay ROI spectra', CSV export) instead of the "
            "image-only tools.",
        ),
        related_pages=("getting_started.opening_a_spectrum", "export.gsf"),
        related_knowledge_articles=("concept.point_spectrum", "concept.hyperspectral_cube"),
    ),
    ManualPage(
        page_id="troubleshooting.cannot_edit_raw_data",
        category=TROUBLESHOOTING,
        title="Why can't I edit a value directly?",
        summary=(
            "Raw measurement data is immutable by design - every change is a new "
            "derived dataset."
        ),
        purpose=(
            "SNOMNIMAN never offers in-place editing of pixel values or metadata, because "
            "reproducibility depends on the raw measurement never changing underneath its "
            "provenance chain. What looks like 'fixing' a value (e.g. a bad zero point) is "
            "always an explicit, recorded processing operation instead."
        ),
        steps=(
            "Use the Process tab to apply the operation that expresses the correction you "
            "want (e.g. Fix Zero, Plane Level, Crop) - it produces a new derived channel, "
            "leaving the original untouched and traceable in Provenance.",
            "A metadata correction is also a tracked step, not a silent overwrite.",
        ),
        related_pages=("workspace.overview", "explorer.provenance"),
        related_knowledge_articles=("concept.immutable_measurements",),
    ),
    ManualPage(
        page_id="troubleshooting.measurement_wont_open",
        category=TROUBLESHOOTING,
        title="A measurement folder won't open",
        summary="SNOMNIMAN only reads formats it has a dedicated, validated reader for.",
        purpose=(
            "Rather than guess at an unfamiliar file layout, SNOMNIMAN declines to open a "
            "measurement it does not recognize. This is intentional: an incorrect guess "
            "about units/axes/conventions would be a scientific correctness risk, not just "
            "an inconvenience."
        ),
        steps=(
            "Confirm the folder is a neaSNOM measurement directory (imaging or "
            "point-spectroscopy) - other vendor formats are not yet supported.",
            "Check the error message shown - it names what was expected and what was "
            "found.",
        ),
        related_pages=("getting_started.opening_a_measurement",),
    ),
)

PAGES: tuple[ManualPage, ...] = (
    _GETTING_STARTED
    + _EXPLORER
    + _WORKSPACE
    + _AI
    + _EXPORT
    + _SETTINGS
    + _SHORTCUTS
    + _TROUBLESHOOTING
)
