# Beta Readiness Review - v1

**Status:** Product readiness review (not architecture). **Date:** 2026-06-28
**Reviewer stance:** an experienced s-SNOM / nano-FTIR researcher who lives in
neaPLOT, is technically proficient, and is being asked one question only:

> Can I use SNOMNIMAN for an entire working day without opening neaPLOT?

This document treats SNOMNIMAN as a **product entering internal beta**. It contains
no code and proposes no new architecture. It is the successor to
[`product-review-v0.1.md`](product-review-v0.1.md) (the read-only-viewer critique of
2026-06-26): where that review asked "can I *understand* a measurement," this one
asks "can I *finish my work*." It is checked against the project's own yardsticks -
[`product-philosophy.md`](product-philosophy.md) ("remember the measurement, not the
software"; "everything is a derivation of an immutable measurement"),
[`measurement-explorer.md`](measurement-explorer.md) (the North Star), and
[`vision.md`](vision.md) (speak of neaPLOT cautiously). Every "friction" named is
either observed in the running Explorer or read directly from the code; where it
means a vendor / click-driven workflow friction, it is stated only where I am
confident.

The success test for this document: every recommendation must remove a *real
workflow barrier* to a full day of work, not add another capability for its own
sake. The project maxim applies to product scope too - "two things we can defend
over four we can't."

---

## Executive summary - the one sentence that matters

**v0.1 was the best place to understand a scan and a place where I could only look.
v1 is a place where I can do a complete imaging analysis - and a place I cannot yet
leave with anything but a picture.**

Since v0.1, the entire "action" half of the product arrived, and it is good: I can
read the value scale (colorbar + histogram + contrast), compare harmonics
side-by-side with a synchronized cursor, draw a line and read a profile, reduce a
region to statistics, level topography, normalize an optical order by its reference,
unwrap phase, crop - each as an explicit, previewed, provenance-recorded derivation
that never touches the raw - and export a publication figure that carries a
regeneratable provenance record instead of a bare screenshot. On top of that sit
three things neaPLOT does not have at all: a deterministic Diagnostics panel, an AI
Scientific Briefing with grounded Suggested Next Steps, and a Knowledge Center that
teaches the science in context. **For a single imaging scan, ending in a figure,
SNOMNIMAN is now genuinely competitive - and on transparency, reproducibility, and
teaching it already wins.**

So why is the answer to the headline question still "not for a whole day"? Because
the **last mile of a real workday is missing**, and it is missing as a tight,
addressable cluster rather than as a deep architectural hole:

1. **My work cannot leave the building as data.** After I level and normalize, my
   only output is a figure. I cannot save the processed dataset, I cannot export the
   profile or region numbers, and I cannot reopen this session tomorrow. (The backend
   can already write Zarr and GSF; the GUI simply does not call it.)
2. **I work in sessions of many scans; SNOMNIMAN opens one.** There is no File ->
   Open, no recent list, no way to hold two measurements at once. A research day is
   the four sibling runs sitting next to each other, and I would relaunch the app for
   each one and lose my measurements every time.
3. **One table-stakes processing step is absent: line-by-line flattening.** Plane
   leveling alone does not remove the per-scan-line offsets real topography carries,
   so cleaning many real scans still sends me back to another tool.

Everything else (spectroscopy, batch, a real AI narrator) is either genuinely
out-of-scope for an imaging v1 or explicitly optional by design. The encouraging
read: the gating cluster above is days-to-weeks of focused product work that
**reuses abstractions that already exist** (the io writers, the processing registry +
generic Workspace, the provenance DAG, the viz measurement objects). No new subsystem
is required to make SNOMNIMAN finishable.

**Readiness verdict:** ready for a *controlled* internal beta with friendly users
today; ready for an *open* beta once the egress + persistence cluster (Section 3,
Critical) lands.

---

## 1. Complete workflow review

A full session, stage by stage, as the running Explorer actually behaves
(`python -m snomniman.gui <measurement-dir>`), on the real CdO measurement.

### 1.1 Open a measurement
- **Works:** one gesture - point at a folder, get one coherent measurement, not 56
  `.gsf` files plus a `.txt`. A clean error dialog if the folder is not a measurement.
- **Friction:** the *only* ways in are the launch-time CLI argument or a one-shot OS
  folder dialog. There is **no File menu, no Open, no Open Recent, no menu bar at
  all** (confirmed: the window installs no `QMenuBar`/`QAction`). Once a measurement
  is open you cannot open another without relaunching. The empty state is a bare
  folder dialog - no recent measurements, no sample data, no guidance. The title is
  the raw folder name, timestamp noise and all (v0.1 carryover).

### 1.2 Understand what was loaded - *the crown jewel*
- **Works, and leads the field:** the always-on identity strip (kind; raw vs derived;
  pixels; um; cm^-1; detection; source; date; vendor), the conventions line in the
  status bar (nm, lower-left, phase as imported), the grouped/typed metadata
  inspector with unit *and source* per value, the plain-language provenance ("This is
  the raw measurement - nothing has been done to it"), the Diagnostics tab
  (tilt/roughness/harmonic decay/channel stats), and the AI Briefing tab. A newcomer
  knows what they are looking at before touching anything.
- **Friction:** the metadata "Source" column is always on (v0.1 asked for progressive
  disclosure; still always-on) and the inspector cannot be searched or copied from;
  the **verbatim vendor header is preserved in the backend but not viewable in the
  GUI** (v0.1 Should-have, still open) - so the one place to settle an argument about a
  raw parameter is unreachable.

### 1.3 Browse channels
- **Works:** channels grouped by physical meaning (optical / mechanical / topography /
  references), instant switching that keeps zoom and pan, and an amp/phase toggle that
  appears only when the channel offers the choice.
- **Friction:** browsing is **mouse-only - there is no keyboard stepping** through
  O0..O5 (the single most common motion; confirmed no shortcuts anywhere). Stepping to
  a new channel **resets the representation to that channel's default**, so comparing
  *phase* across orders throws me back to amplitude on every step (v0.1 carryover).
  Mechanical M0..M5 get equal visual weight with the optical orders even though they
  are usually diagnostic. Nothing marks which orders are signal vs. noise.

### 1.4 Compare harmonics / channels - *was the biggest v0.1 hole; now solved*
- **Works:** a "Single" detailed view plus four comparison presets (Amplitude/Phase,
  Optical/Topography, Sample/Reference, Harmonic series) and a harmonic contact sheet,
  all with a **synchronized cross-channel crosshair and a single shared readout**.
  This is the core of near-field practice and it is now well supported.
- **Friction:** the comparison layouts are fixed presets - I cannot hand-pick an
  arbitrary set (say O2 phase vs O3 phase vs Z). The contact sheet is optical
  amplitude only.

### 1.5 Measure features (read-only observations)
- **Works:** line / rectangle / polygon overlays, live recompute as I drag, a session
  history (rename / hide / delete), and results across every visible channel - a
  profile plot for lines, a min/median/mean/max/std/area table for regions. These are
  observations; they never create a derived dataset. Measurements survive channel
  changes.
- **Friction (a data-egress problem in miniature):** the **profile plot is normalized
  0..1 per curve**, so I can compare shapes but cannot read an absolute step height
  off the plot (the legend shows only the [min..max unit] range); there is no value
  cursor on the profile. And there is **no way to export the profile samples or the
  region statistics** - no CSV, no first-class copy - so the numbers are trapped on
  screen. Measurements are session-only and are cleared when I derive a new dataset.

### 1.6 Process data - *the line between viewer and tool; now crossed*
- **Works, and is distinctive:** one generic, registry-driven Processing Workspace
  lists every registered operation (grouped, with availability and a plain reason when
  it does not apply), builds each parameter form automatically, and runs one identical
  Preview -> (what changes / what stays / the provenance to be recorded) ->
  Accept/Cancel derivation. The raw is never mutated; a "Back to <original>" control
  walks the history. A Suggested Next Step from the AI previews straight into this same
  Workspace - no special execution path.
- **Friction:** the **operation vocabulary is four** (`image.plane_level`,
  `image.reference_normalize`, `image.phase_unwrap`, `image.crop`). Missing the
  table-stakes ones: **line-by-line flatten / row alignment**, background subtraction,
  height zero/offset, rotate, masking/threshold, higher-order leveling. History is
  linear (no branching, no redo). And the derived result **cannot be saved** (see 1.8).

### 1.7 Return to raw
- **Works, and is on-philosophy:** the "<- Back to <title>" history stack, the
  always-visible "this is the raw measurement," and structural immutability make it
  impossible to fear corrupting anything. This is exactly "everything is a derivation
  of an immutable measurement," made tangible.

### 1.8 Get the work out
- **Works:** "Export figure..." writes a publication figure (PDF / PNG / SVG; vector
  for PDF/SVG) **with a `.provenance.json` sidecar** - the full, regeneratable
  `FigureSpec` plus a human-readable caption (measurement, sha256, panels, levels,
  scale bar, overlays, conventions, software versions, timestamp). This is a real
  identity win over a screenshot and answers v0.1 obstacle #4.
- **Friction (the headline gap):** a **figure is the only thing that can leave the
  app.** There is **no dataset export** (the io layer has `write_zarr` and `write_gsf`;
  the GUI calls neither), **no measurement-data export** (1.5), and **no project /
  session save-and-reopen** - which means the Phase 4 exit criterion ("an interactive
  session is saved and exactly reproduced from the project + raw files") is not yet
  met from the GUI. In-app figure polish (caption editing, multi-export, clipboard) is
  also absent.

### 1.9 Learn an unfamiliar concept
- **Works, and is unique:** the Knowledge Center tab (browse tree + search +
  cross-linked articles) and "Learn more" deep-links from the Workspace and from AI
  recommendations. The software teaches the science while you use it.
- **Friction:** deep-links exist today only from operations; diagnostics rows,
  harmonics, provenance, and metadata are not yet linked (the mechanism is generic, so
  this is reach, not redesign). Content is an initial curated set.

---

## 2. Workflow gaps - where a researcher must still leave SNOMNIMAN

Ranked by impact on "a full day without neaPLOT."

| # | Gap | Why it forces an exit | Note |
|---|-----|-----------------------|------|
| G1 | **Cannot save the processed dataset or the session** | The day ends with a figure and nothing else; cannot hand cleaned data to a colleague / Origin / Python / Gwyddion, cannot resume tomorrow | Backend `write_zarr` + `write_gsf` exist, unwired; pipeline DAG already designed for serialization |
| G2 | **Cannot export measurement numbers** (profile samples, region stats) | The quantitative results - step heights, particle widths, ROI means - must be retyped from the screen | Reuses existing `ProfileSet` / `RegionReport` |
| G3 | **One measurement at a time; no library / recent / Open** | A real session is many sibling scans; relaunching per scan and losing session measurements is unworkable | No menu/recent infra exists yet |
| G4 | **No line-by-line flatten** (and no background subtraction) | Real scanner topography has per-line offsets/bow that plane-level cannot remove; cleaning many scans needs another tool | A registered `ProcessingStep`; no GUI work needed |
| G5 | **No spectroscopy / nano-FTIR / hyperspectral** | If the day includes point spectra or a cube, SNOMNIMAN cannot open it at all | Whole-modality; arguably out of imaging-v1 scope (roadmap Phase 5/6) |
| G6 | **No batch** | Cannot apply one recipe across a folder of scans unattended | `snomniman.batch` is an empty stub (roadmap Phase 6) |
| G7 | **Daily ergonomics**: keyboard harmonic stepping; representation persistence; arbitrary comparison layout; vendor-header view; metadata search/copy; absolute-value profile | Each is small; collectively they make a power user feel slowed down | Polish tier |

The shape of this list is the whole story: **G1-G4 are a small, reuse-only cluster
that turns "I did the analysis" into "I kept and shared the analysis."** G5-G6 are
deliberate scope decisions for later phases. G7 is polish.

---

## 3. Beta blockers

### Critical - must land before an open beta
- **C1. Save / export the processed dataset.** Wire the existing `write_zarr` (and/or
  `write_gsf`) into the GUI as "Export data...". Without it a beta tester literally
  cannot keep their work. (G1)
- **C2. Export measurement data.** Profile samples and region statistics to CSV, plus
  copy-to-clipboard on the stats table. Cheap; removes a guaranteed daily exit. (G2)
- **C3. Open more than one measurement.** At minimum a File -> Open that replaces or
  adds a measurement without relaunch; ideally a small Recent list. A session is
  multi-scan. (G3)
- **C4. `image.line_flatten`.** A registered ProcessingStep for line-by-line offset/
  bow removal - the most-missed topography operation. Implement + register + declare
  params/capabilities + Knowledge article (the no-drift test will require it); zero GUI
  work by design. (G4)

### High - strongly recommended for beta
- **H1. Project save / reopen.** Serialize the provenance DAG (the pipeline layer is
  designed for exactly this) so a session reopens and replays from project + raw -
  meeting the Phase 4 exit criterion. Naturally follows C1.
- **H2. Keyboard navigation.** Arrow keys step harmonics; a single key toggles
  amplitude/phase; *persist the representation across channel switches*. Makes browsing
  feel like turning a dial.
- **H3. Round out topography processing.** Background subtraction and height
  zero/offset (and likely rotate) - the operations researchers reach for right after
  leveling.
- **H4. Absolute-value line profile + on-profile value readout.** Measurement honesty:
  let me read a real height at a point, not only a normalized shape.
- **H5. Verbatim vendor header view + metadata search/copy.** Completes the
  transparency promise (v0.1 carryover); both are presentation-only.

### Medium - can follow the first beta
- M1. Cross-measurement comparison (two scans side by side).
- M2. Free-form comparison layout (hand-pick panes).
- M3. "Learn more" deep-links from diagnostics rows, harmonics, provenance, metadata
  (mechanism already generic).
- M4. Signal-vs-noise channel triage marking - **only after** it passes the Scientific
  Validation process (see Section 7); do not ship it on intuition.
- M5. Figure polish: caption editing, multi-panel export selection, clipboard copy.

### Future - explicitly not required for v1
- F1. nano-FTIR / hyperspectral readers + spectral viewer (roadmap Phase 5/6).
- F2. The batch engine (roadmap Phase 6).
- F3. Additional vendor readers; scripting API; packaging/installers (roadmap Phase 8;
  each gets its own ADR).
- F4. A concrete AI narrative provider. **Not a blocker by design** - the deterministic
  Briefing and Suggested Next Steps are complete without it (AI rule 2: AI never gates
  understanding).

---

## 4. neaPLOT comparison - complete workflows, not feature lists

The honest test is not "who has more buttons" but "where does the researcher switch
back, and why."

- **Workflow A - open and understand one scan.** SNOMNIMAN already wins: the unit of
  work is the measurement (not files), acquisition context and provenance sit beside
  the data, phase renders honestly, and Diagnostics + Briefing orient you immediately.
  *Switch-back point: none.*

- **Workflow B - level, reference-normalize, read a profile, export a figure for a
  talk.** SNOMNIMAN now does this end-to-end, and the exported figure carries a
  regeneratable provenance record - arguably *better* than the vendor-tool habit of a
  bare PNG. *Switch-back point: only if the topography needs line-by-line flattening
  (G4), or if I need the cleaned data file afterwards (G1).*

- **Workflow C - process a day of scans and export the data for Origin / Python.**
  neaPLOT still wins decisively: SNOMNIMAN cannot save the data (G1/G2), cannot open
  the many scans of a session (G3), and cannot batch (G6). *This is the switch-back
  point*, and it is the single most important one for daily adoption.

- **Workflow D - nano-FTIR spectra / hyperspectral.** neaPLOT only; SNOMNIMAN cannot
  open the data at all (G5).

**Where would a researcher still switch back, and why?** The moment they need to
**(a) keep or share the processed data**, **(b) work across many scans in one
session**, or **(c) touch spectroscopy.** (a) and (b) are the beta-gating cluster
(Section 3 Critical + H1); (c) is a deliberate future phase.

**How SNOMNIMAN eliminates each transition:** C1/C2 remove the data-egress wall;
C3/H1 remove the one-scan-at-a-time wall; C4/H3 remove the topography-cleaning wall;
F1 (later) brings the spectroscopy cohort in. None of these requires new architecture
- each reuses an abstraction already in the codebase.

---

## 5. User testing plan - a lightweight friction-discovery protocol

Goal: **discover where real researchers stumble**, not collect satisfaction scores.
Observe behavior; let the software fail in front of you.

### Cohorts and what each is best at revealing
- **Graduate student (daily neaPLOT user)** - first-five-minutes and processing
  friction: can they finish a real figure with no help?
- **Experienced researcher / postdoc** - scientific trust: do provenance, conventions,
  and diagnostics earn the switch? Do they believe the numbers?
- **PI** - defensibility: is the output reproducible and citable years later (the
  figure-regeneration story)? Would they let a paper depend on it?
- **Facility / instrument scientist** - onboarding and edge cases across many real
  measurement directories; vendor-header and metadata-completeness questions.

### Method
- 5-8 sessions, ~45 minutes, one observer, screen + audio recorded.
- Each participant uses **their own** measurement directory. No training, no manual.
- Think-aloud; the observer stays silent except to say "what did you expect there?"
- Record: every hesitation, every click that expected an action and got none, every
  moment they reach for neaPLOT (and at which task), and every literal "I wish it did
  X." The verbatim wish-list is the backlog.

### Tasks (each maps to a workflow; tasks 6-7 are designed to surface the Critical gaps)
1. Open your own scan and tell me what it is.
2. Tell me which harmonics carry signal and which are noise.
3. Level the topography and normalize O2 by its reference.
4. Measure a step height (or particle width) and a region's statistics.
5. Export a figure for your group meeting, and explain to me where it came from.
6. Hand me the processed data and the numbers from task 4. *(surfaces G1/G2)*
7. Open a second scan from the same session and compare them. *(surfaces G3)*

### Success metrics (behavioral, not opinion)
- Task completion without help (per task).
- Time to first image; number of "where is / can I" stalls.
- **Count of forced exits to another tool, and at which task** - the primary metric.
- Can they articulate the provenance of their exported figure unprompted?
- Unprompted "I would use this for X."
- **Explicit non-metric:** a 1-5 "do you like it" score. Likeability is not adoption.

Re-run after each iteration; feed results into the next `product-review-v0.x` and into
this document's obstacle list. The bar from `measurement-explorer.md` is unchanged: a
researcher who closes the laptop thinking not "good software," but "I never want to go
back."

---

## 6. Product readiness score

Each area scored out of 5, with justification grounded in the running app.

| Area | Score | One-line justification |
|------|:-----:|------------------------|
| Scientific correctness | 5.0 | Immutable raw; explicit conventions; complex semantics; golden/synthetic-validated backend; defers what it cannot defend |
| Reproducibility | 4.0 | Provenance DAG on every derivation + regeneratable figures; held back only because the GUI cannot yet persist the project/data |
| Trust | 4.5 | Visible value scale (colorbar/histogram/contrast), immutability and lineage front-and-center, honest unknowns |
| Usability | 3.5 | Core loop is coherent and low-friction once inside; dragged down by egress, single-measurement, no keyboard |
| Discoverability | 3.0 | No menu/toolbar, hidden zoom/pan, CLI/dialog-only open; breadth is real but not visible to a newcomer |
| AI integration | 4.0 | Exemplary architecture (grounded, deterministic, recommend-not-execute, optional); narrative seam has no provider yet (by design) |
| Teaching capability | 4.5 | Knowledge Center is genuinely distinctive and drift-guarded; breadth and deep-links still growing |

**Justifications.**

- **Scientific correctness - 5.0.** This is the project's strongest pillar and it
  shows: raw data is immutable, conventions (nm, lower-left, phase as imported) are
  explicit and on-screen, complex channels are first-class, the backend is validated
  against synthetic and golden data, and - decisively - the project *declines* to ship
  judgments it cannot defend (the deferred phase-unwrap rule). Nothing observed
  overstates what is measured.

- **Reproducibility - 4.0.** Every derivation records a provenance node (sources,
  params, software + operation versions); the exported figure carries a full
  regeneratable spec and caption. It is not 5.0 because reproducibility currently lives
  **in memory and in the figure sidecar** - the GUI cannot save the project or the
  processed dataset, so a session cannot be reopened and replayed. Wiring `write_zarr`
  + DAG serialization (C1/H1) closes this to 5.0.

- **Trust - 4.5.** The v0.1 trust gap (an image whose scale you cannot see) is fixed:
  colorbar + histogram + explicit contrast make the scale visible and adjustable, and
  scaling is no longer a silent transformation. Immutability and provenance are
  reassuring. Held a half-point by the absence of any in-product cross-check against an
  established tool (v0.1 carryover) and by the normalized-only profile, which can
  mislead about absolute values.

- **Usability - 3.5.** Inside a session the loop (open -> browse -> compare -> measure
  -> process -> export) is genuinely pleasant. The score reflects the workday edges:
  data and numbers cannot leave, only one measurement opens at a time, there is no
  keyboard navigation, and representation resets on channel change. Solid, clearly
  pre-beta-polish.

- **Discoverability - 3.0.** The lowest score and the cheapest to raise. There is no
  menu bar and no toolbar; the strong zoom/pan is undiscoverable; opening is CLI- or
  dialog-only; capability is spread across tabs a first-timer must stumble into. The
  breadth is real - it is just invisible.

- **AI integration - 4.0.** Architecturally close to ideal: the Briefing and Suggested
  Next Steps are deterministic, grounded in describe + diagnostics, recommend-but-never-
  execute, and fully useful with no provider configured. Below 5.0 only because the
  narrative layer is an empty seam (by design) and AI still lives in tabs rather than as
  the ambient orientation strip v0.1 envisioned.

- **Teaching capability - 4.5.** The Knowledge Center is a real differentiator -
  teach-while-working, a no-drift article-per-operation invariant, and the same curated
  base that will ground a future narrator. Below 5.0 only on reach (deep-links from one
  surface so far) and breadth (an initial curated set).

**Overall: ~4.0/5 - "ready for a controlled internal beta, not yet an open one."**
The science, reproducibility-of-record, trust, AI, and teaching pillars are
beta-ready. The gate is the workday-completion cluster: persistence, data egress, and
multi-measurement sessions.

---

## 7. Roadmap - driven by observed gaps, built on existing architecture

Ordered by "removes a real barrier to a full day." Every item maps to a gap in Section
2, **reuses an abstraction that already exists**, and introduces **no new
architectural subsystem** (Rule 7; the user's constraint). The work is product depth,
not platform breadth.

### Now - the beta-gating cluster (egress + persistence + one operation)
1. **Export data** - wire `write_zarr` and `write_gsf` into the GUI. *(C1/G1; io
   writers already exist.)*
2. **Export measurement results** - profile and region statistics to CSV + clipboard.
   *(C2/G2; uses `ProfileSet` / `RegionReport`.)*
3. **`image.line_flatten`** - a registered ProcessingStep for line-by-line offset/bow
   removal, with its Knowledge article. *(C4/G4; engine + Workspace + no-drift test
   already carry it - zero GUI code.)*
4. **Open another measurement + Recent + a File menu.** *(C3/G3; GUI-only.)*

### Next - close the reproducibility loop and the daily ergonomics
5. **Project save / reopen** by serializing the provenance DAG -> meets the Phase 4
   exit criterion. *(H1; pipeline is designed for this.)*
6. **Keyboard navigation + persist representation.** *(H2.)*
7. **Background subtraction + height zero/offset** (and likely rotate). *(H3; new
   ProcessingSteps, no GUI work.)*
8. **Absolute-value profile + on-profile value readout.** *(H4.)*
9. **Verbatim vendor-header view + metadata search/copy.** *(H5.)*

### Then - deepen within scope
10. Cross-measurement comparison; "Learn more" from diagnostics/harmonics/provenance/
    metadata; figure caption editing. *(M1/M3/M5.)*
11. **A validated signal-vs-noise channel-triage diagnostic.** Run it through the
    Scientific Validation process (the [`phase-wrapping-analysis.md`](phase-wrapping-analysis.md)
    template: question -> literature -> candidate criterion -> synthetic + real-data
    validation -> decide) *before* shipping any recommendation or marking. If it cannot
    be defended on present data, say so and defer - exactly as the phase-unwrap rule was
    deferred. *(M4; this also subsumes the "harmonic ranking" question.)*

### Future - their own ADRs, not v1
12. nano-FTIR / hyperspectral readers + spectral viewer (Phase 5/6); the batch engine
    (Phase 6); a concrete optional AI provider; additional vendor readers / scripting /
    packaging (Phase 8). *(F1-F4.)*

**Discipline check.** Items 1-2 reuse the io writers; 3, 7, 11 are new
`ProcessingStep`s / diagnostics that the generic Workspace and Diagnostics panel
surface automatically; 4-9 are presentation; 5 reuses the pipeline DAG. Nothing here
adds a plugin system, a cloud, or a speculative abstraction. The product now drives the
engineering, and the engineering it asks for is *use what we built*.

---

## How to use this document

Treat **Section 3 Critical (C1-C4)** as the open-beta gate and **Section 4's
switch-back points** as the definition of "ready for a full day." Re-run this review
as `beta-readiness-v2.md` after each iteration and watch the switch-back points
disappear, just as the v0.1 obstacle list has already largely cleared. The metric is
unchanged and is not feature count: it is the headline question flipping from "not for
a whole day" to "I never opened neaPLOT today."

The strongest validation step is the one this document cannot substitute for: **put it
in front of two or three colleagues who live in neaPLOT, ask them to finish a real
analysis, and watch where they reach for the other tool.** Their forced exits will
order this backlog faster than any internal critique.

See also: [`product-review-v0.1.md`](product-review-v0.1.md) (the prior iteration),
[`product-philosophy.md`](product-philosophy.md),
[`measurement-explorer.md`](measurement-explorer.md), [`roadmap.md`](roadmap.md),
[`vision.md`](vision.md), [`phase-wrapping-analysis.md`](phase-wrapping-analysis.md)
(the Scientific Validation template).
