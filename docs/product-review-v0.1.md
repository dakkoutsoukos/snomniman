# Product Review - Measurement Explorer v0.1

**Status:** Product critique (not architecture). **Date:** 2026-06-26
**Reviewer stance:** an experienced s-SNOM / nano-FTIR researcher who uses neaPLOT
daily, is technically proficient, and cares only about getting scientific work done.

This is a deliberately critical review of the **running** Measurement Explorer as
it exists today - opened on the real CdO nanoparticle measurement (150 x 150 over
10 um, PsHet at 5973 cm^-1, optical O0-O5, mechanical M0-M5, references, and
topography). It evaluates SNOMNIMAN as a *product*, not as an architecture. It
prefers uncomfortable truths to polite praise. It is the intended **product
backlog** for the next several iterations.

It is checked against the project's own yardsticks: `product-philosophy.md`
("researchers should remember their measurements, not the software"),
`measurement-explorer.md` (the experience this was built to deliver), and
`vision.md` (which asks us to speak about neaPLOT cautiously). Where this review
names a neaPLOT "friction," it means friction common to vendor / click-driven
analysis workflows, stated only where I am confident - not a claim about any one
tool's internals.

---

## Executive summary - the one uncomfortable truth

**v0.1 is a genuinely excellent place to *understand* a measurement and a place
where I cannot yet *do* anything with it.**

Everything the Explorer promises about comprehension, it delivers: I open a folder
and instantly see one coherent measurement with its real parameters, I flip
channels with zero latency and keep my zoom, phase renders honestly as an angle,
and I can always see the conventions and that "this is the raw measurement." That
is real, and parts of it already feel better than what I am used to.

But as a working scientist, the session ends the moment I want to act. I cannot
level the topography, I cannot normalize O2 by its reference, I cannot draw a line
across a particle and read a profile, I cannot pull a number out of a region, I
cannot read the colorbar (there isn't one), and I cannot get a figure out except by
screenshotting. So the honest summary is: **this is the best near-field *viewer* I
have used, and it is not yet a tool I can replace neaPLOT with**, because replacing
neaPLOT means *finishing an analysis*, and right now I can only look.

That is not a criticism of the strategy ("explore before you process" is correct).
It is a statement of where the product is: exploration is ~70% of the way to
delightful, and *action* is at zero by design. The five highest-impact gaps below
are all about closing the distance between "I understand this scan" and "I can
trust and use what I'm seeing."

**Top five findings, by user impact:**
1. **No colorbar and no contrast control.** I cannot quantitatively read or trust
   an image whose scale I cannot see or adjust. This undercuts the whole "honest"
   promise more than anything else in the product.
2. **No analysis actions at all** (leveling, referencing/normalization, line
   profiles, ROI statistics, spectra). I can understand a measurement but not
   work on it.
3. **No multi-channel view.** Near-field science *is* cross-channel correlation
   (does O2 localize on the topography? how does O2 compare to O3?). I can only see
   one channel at a time; the synchronized cross-channel cursor and harmonic
   contact sheet that were designed are not here.
4. **The cursor readout is in the wrong place and too sparse.** It lives in the
   bottom status bar, far from my pointer, and shows three curated values rather
   than the cross-channel picture I actually want.
5. **No way out.** No figure/data export; the only escape is an OS screenshot,
   which severs the figure from its provenance - exactly the failure mode the
   philosophy warns against.

The rest of this document expands and ranks these.

---

## 1. First impression

**What immediately feels good.**
- **It opens as one thing.** Pointing it at the measurement folder and getting a
  single labeled measurement - not 56 `.gsf` files and a separate `.txt` to
  cross-reference by hand - is the strongest first impression. This alone changes
  my mental model from "files" to "measurement."
- **It already knows what this is.** The identity strip (image; raw measurement;
  150 x 150 px; 10 x 10 um; 5973 cm^-1; PsHet; the date; neaspec) tells me what I'm
  looking at before I touch anything. I did not have to open a parameters file.
- **A real image is on screen instantly,** correctly oriented, with a scale bar.
  The default (O2 amplitude) is the right first thing to show.
- **It feels safe.** Nothing suggests I can break or overwrite anything, and the
  "this is the raw measurement" line is quietly reassuring.

**What immediately feels confusing or missing.**
- **There is no legend for the colors.** My eyes go to the image, then immediately
  ask "bright = how much?" and there is no answer on screen. For a quantitative
  instrument this is the first thing that erodes confidence.
- **The title is the raw folder name** ("2026-06-16 190234 PH CdO Dense ROI 2").
  It is decipherable but it reads like a filename, not a measurement name. The
  timestamp noise is front-and-center.
- **I don't know what I can do.** There are no visible actions - no toolbar, no
  obvious "fit," "contrast," "compare," or "export." A newcomer cannot tell whether
  this is a viewer or a workbench. (It is, today, a viewer - but nothing says so.)
- **The hover readout is easy to miss.** The richest live information - the values
  under my cursor - is in the bottom-left/right of the status bar, the last place I
  look while studying an image in the center.
- **Empty-state is a dead end.** Launched with no measurement, I get an OS folder
  picker and nothing else - no recent measurements, no sample data, no guidance.

**Expectations created vs. confidence inspired.** The polish of the open creates an
expectation that this is a full analysis tool; the absence of any action then
quietly disappoints that expectation. Confidence in *what the data is* is high;
confidence in *what I can do and whether I can trust the rendered values* is low,
almost entirely because of the missing colorbar/contrast and the missing actions.

---

## 2. Workflow review

### Opening a measurement
- **Good:** one gesture, no wizard, no per-file work; the measurement appears whole.
- **Friction:** the OS folder picker has no notion of "a measurement" - I navigate a
  generic directory tree and can select the wrong (non-measurement) folder; the
  error only appears after I choose. No recent list, no library of the four sibling
  runs sitting right next to it, no thumbnails. One measurement per window, with no
  way to move between the runs of a session.

### Understanding what was loaded
- **Good:** the identity strip plus the metadata panel give me the real acquisition
  context with units and even the *source* of each value.
- **Friction / overload:** the metadata inspector is a four-column tree (Field,
  Value, Unit, Source) shown all at once. The Source column is a trust feature I
  love in principle, but on first read it is visual noise next to every row. There
  is redundancy too: pixels and field size appear in both the identity strip and the
  Scan section. And the genuinely "rarely needed" material the backend preserves -
  the verbatim vendor header - is not surfaced at all, so the one place I might go to
  settle an argument about a raw parameter isn't reachable from the GUI.

### Browsing channels
- **Good:** channels grouped by physical meaning (optical / mechanical / topography
  / references) instead of cryptic filenames is exactly right, and stepping between
  them is instant and keeps my zoom and pan. This is already a better browsing
  experience than hunting through files.
- **Friction:** I browse by mouse only - there is no keyboard stepping through
  O0..O5, which is the single most common motion and should feel like turning a
  dial. Mechanical channels (M0..M5) get equal billing with the optical orders even
  though for most near-field work they are diagnostic, not the science; that doubles
  the size of the list I scan past. And nothing tells me which orders carry signal
  vs. noise - I have to click O5 to discover it's noise, every time.

### Comparing harmonics / channels
- **This is the biggest workflow hole.** I cannot put O2 and O3 side by side, I
  cannot see all optical orders as a contact sheet, and I cannot view O2 next to its
  reference or next to the topography. Comparison today means clicking back and
  forth and holding the previous image in my memory. For near-field work, where the
  whole point is correlating channels at the same location, single-image-at-a-time is
  a fundamental limitation, not a polish issue.
- **Compounding friction:** switching channels resets the representation to
  amplitude. If I am comparing *phase* across O2/O3/O4, every channel change throws
  me back to amplitude and I must re-toggle to phase. The tool forgets what I was
  doing.

### Inspecting metadata
- **Good:** grouped, typed, unit-bearing, and honest about unknowns ("unknown"
  rather than a guessed value) and about provenance of each value. This is a real
  strength and already better than reading a flat `.txt`.
- **Friction:** it is a static dump - I cannot search it, copy a value cleanly, or
  collapse the parts I never look at. The Source column should probably be
  progressive (on demand) rather than always-on.

### Understanding provenance
- **Good and distinctive:** a plain-language "This is the raw measurement - nothing
  has been done to it," plus the import node with its sources, hashes, reader, and
  software versions. Nothing I use today puts lineage in front of me like this.
- **Friction:** for a raw measurement there is exactly one node, so the panel can
  feel like ceremony right now - its real value appears only once derivations exist.
  Deterministic-flag and full software-version rows are shown at a level of
  prominence that belongs deeper (rarely-needed tier). The provenance tab competes
  with metadata for the same dock and is easy to forget is there.

### Orienting yourself in the data
- **Good:** conventions are always visible (nm, lower-left, phase as imported), the
  scale bar is physical, and the image is correctly oriented.
- **Friction:** orientation *within* the image is weaker than it should be. There is
  no colorbar, no histogram, no obvious "fit/reset view," and the live readout that
  would tell me "what is at this particle" is parked in the status bar. The
  excellent zoom/pan (inherited from the plotting layer) is undiscoverable - there
  is no visible affordance telling me I can zoom, reset, or right-click for more.

---

## 3. Compared against neaPLOT (experience, not features)

**Already better:**
- **The unit of work is the measurement, not the file.** Opening is comprehension,
  not assembly. This is the clearest experiential win.
- **Acquisition context is present and trustworthy.** Parameters with units and
  their source sit beside the data instead of in a separate text file I consult by
  hand.
- **Provenance and immutability are first-class.** I can see that the raw is
  untouched and where it came from; that is reassurance I do not normally get.
- **Phase is rendered honestly** with a cyclic colormap and a fixed angular range,
  so it reads as an angle. Channel switching is instantaneous and keeps my view.

**Still worse or not yet competitive:**
- **I can't finish anything.** The decisive gap: in my normal tool I level
  topography, subtract a background, normalize by a reference, take a line profile,
  reduce an ROI, FFT an interferogram, and export a figure. Here I can do none of
  these. As a place to *complete* an analysis, it is not yet a contender.
- **No colorbar / contrast control.** Reading and adjusting the intensity scale is
  table stakes for an imaging tool; its absence is felt immediately.
- **No multi-panel / synchronized comparison.** Correlating channels is core
  near-field practice and is missing.
- **No measurement library / batch.** I work in sessions of many scans; opening one
  folder at a time through an OS dialog is a step back from a tool that lists my
  acquisitions.

**Missing entirely (today):** processing of any kind, spectra/interferogram
handling, line profiles, ROI statistics, export (figure or data), masking,
cross-measurement comparison, and any notion of a saved project/session.

**Net:** SNOMNIMAN already wins the *first five minutes* of understanding. neaPLOT
still wins the *next two hours* of doing. A researcher's day is mostly the second
thing.

---

## 4. Scientific confidence

**Where it earns trust:**
- **Immutability and provenance** are visible and reassuring; I am not afraid of
  corrupting anything.
- **Explicit conventions** (nm, lower-left, phase as imported) are always on screen,
  so I am never silently guessing units or orientation.
- **Honesty about unknowns** - blank acquisition fields read "unknown," never a
  fabricated number.
- **Phase handling** is principled: shown as imported, no silent unwrap/re-reference.

**Where I hesitate:**
- **I cannot see the value scale.** Without a colorbar, "bright" is qualitative. A
  quantitative instrument that shows me a picture I cannot put numbers to undercuts
  its own credibility. This is the single biggest trust gap, and it is ironic given
  how strong the rest of the transparency story is.
- **I cannot see how the image was scaled.** The display uses a robust percentile
  range, which is a *good* default - but it is invisible and unchangeable. I do not
  know that 1st/99th-percentile clipping is happening, so I might misread saturation
  or contrast. A scaling choice the researcher cannot see is, by this project's own
  philosophy, a silent transformation of what is shown (even if not of the data).
- **No cross-check against a reference tool is surfaced.** The backend is
  golden-tested, but as a user I have no in-product way to confirm "this matches what
  my established tool shows," which is what would actually earn my switch.
- **Discoverability gaps read as missing capability.** Because zoom/reset/export are
  hidden, I may conclude the tool *can't* do them, which lowers my estimate of its
  maturity unfairly.

**Verdict:** the *data* is trustworthy and the conventions are exemplary; the
*rendering* is not yet self-explaining (no colorbar, invisible scaling), and that is
where confidence leaks.

---

## 5. AI readiness

The Explorer is unusually well-prepared for AI, precisely because the architecture
already treats everything as a measurement plus structured derivations, metadata,
and provenance. AI would not be a bolt-on; it would have real structure to consume.

- **Where AI would feel natural:**
  - **Orientation on open** - a one-paragraph "what am I looking at": "10 x 10 um
    PsHet scan at 5973 cm^-1; strongest optical contrast in O2/O3; O5 is
    noise-dominated; a reference is present; topography shows dense particle
    coverage." This is the highest-value, lowest-risk AI touch and it maps exactly
    to the orientation gap in Section 1.
  - **Channel triage** - flagging which orders carry signal vs. noise, which would
    directly remove the "click O5 to find out it's noise" friction.
  - **Explain-this-region** - select a particle and ask "what is this," answered in
    context as a structured annotation.
  - **Provenance narration** - "how was this made," read from the graph in plain
    language (trivial now, valuable once derivations exist).
- **Where AI would feel intrusive:** anything that blocks the open, auto-runs on
  every hover, animates, or pushes a chat panel into the center. The science must
  stay the hero; AI belongs at the edge of attention, opt-in, and silent until asked.
- **Where AI would remove the most friction:** orientation + channel triage +
  cross-measurement recall ("this resembles yesterday's run on the same ROI").
- **Where AI must never intervene:** it must never alter the rendered values, the
  scaling, the conventions, or the data; never assert a measured value; never turn a
  suggestion into an action without an explicit, recorded, researcher-initiated step.
  The product's existing posture (measurement is sacred; AI proposes, the scientist
  disposes) is exactly right and must be held.

**Readiness verdict:** structurally ready and philosophically aligned. The one
prerequisite is experiential, not technical: AI output needs a *home* in the UI (an
unobtrusive orientation strip and a per-region annotation surface) that does not yet
exist. Build the place before the intelligence.

---

## 6. Product polish (high impact, low effort)

These are perceived-quality wins that do not require major engineering:
- **Add a colorbar with units** beside the image. Single highest
  perceived-quality-per-effort change in the entire product.
- **Move the live readout to the cursor** (or echo it prominently near the image),
  and show coordinate + value with units right where my eyes already are.
- **Give the measurement a clean title.** Parse a friendly name from the folder
  ("CdO Dense ROI 2") and demote the raw timestamp string to a subtitle/tooltip.
- **Keyboard stepping** through harmonics (arrow keys) and amplitude/phase (a single
  key), so browsing feels like turning a dial.
- **Persist representation across channel switches** (if I'm on phase, stay on phase
  when I step to the next order).
- **A visible "fit / reset view" control** and a hint that the image zooms/pans, so
  the good interactions stop being hidden.
- **Trim the active-channel caption.** "state: raw  range [..]  colormap: viridis"
  is engineer-facing; a researcher wants the channel, the representation, and the
  unit. The numeric range is replaced by the colorbar; the colormap name is
  irrelevant.
- **Make the metadata Source column progressive** (reveal on demand) so the default
  view is calm.
- **Render units properly** (cm^-1 as a superscript, keep um as um) in labels.
- **Mark or de-emphasize noise-dominated channels** once a simple heuristic exists,
  so the eye goes to the orders that matter.

---

## 7. Roadmap prioritization

Ranked by user impact, ignoring implementation difficulty, and consistent with
"explore before you process" (deepen understanding before adding transformation).

### Must have (before a credible v1.0)
1. **Colorbar + visible, adjustable contrast/levels** (with a histogram). *Reason:*
   you cannot trust or quantitatively read an image otherwise; it is the biggest
   confidence gap.
2. **Multi-channel comparison** - side-by-side panels with a *synchronized
   cross-channel cursor*, and a harmonic contact sheet. *Reason:* cross-channel
   correlation is the core of near-field analysis; single-image browsing cannot
   support it.
3. **Cursor readout relocated and expanded** - at/near the pointer, reporting the
   value across the channels on screen, with units. *Reason:* this is the live
   "what is here" that makes exploration feel alive.
4. **Line profile and ROI statistics** (min/max/mean/std, area). *Reason:* the most
   basic quantitative reading a researcher does; still read-only and safe.
5. **Export of the current view** as a figure *that carries its provenance/caption*
   (not a bare screenshot). *Reason:* the only way to get work out today severs the
   figure from its data; this is an identity-level failure to fix early.
6. **First processing derivations - topography leveling and reference
   normalization** - as explicit, recorded, non-destructive steps. *Reason:* this is
   the line between "viewer" and "tool you can finish an analysis in"; it is what
   actually competes with neaPLOT. (Sequence it *after* the exploration items above,
   per the philosophy.)

### Should have
7. **AI orientation paragraph on open** + channel signal/noise triage (Section 5).
8. **Measurement library / recent + cross-measurement comparison** (the four CdO
   runs as a session, side by side).
9. **Verbatim vendor header view** (the rarely-needed tier, reachable but tucked
   away) - completes the transparency promise.
10. **Reference-beside-signal view** as a first-class one-gesture comparison.
11. **Saved project / session** (view state, which measurements are open).
12. **A real cross-check against an established tool**, surfaced or documented, to
    earn trust for the switch.

### Nice to have
13. Per-channel/region statistics overlays and richer annotations.
14. Light/dark theme and display preferences (interpolation, gamma).
15. Spectra/interferogram exploration once those readers exist (the model already
    generalizes to a wavenumber axis).
16. Keyboard-driven command surface for power users.

---

## 8. Things to remove or suppress

Being ruthless, in service of "remember the measurement, not the software":
- **The engineer-facing parts of the active-channel caption** (range numbers once a
  colorbar exists; the colormap name always). They are noise to a scientist.
- **The always-on Source column** in metadata - keep the capability (it is a genuine
  trust feature) but make it progressive so the default view is calm.
- **Top-level prominence of deterministic flags and full software-version lists** in
  provenance - true and valuable, but rarely-needed tier; nest them deeper.
- **Equal visual weight for mechanical channels.** For most near-field work they are
  diagnostic; consider a collapsed/secondary grouping rather than a peer of the
  optical orders. (Keep them reachable - some users need them.)
- **Redundant facts** shown identically in both the identity strip and the metadata
  Scan section - pick the canonical home for each.
- **Do not add** any control that does not help me understand or act on a
  measurement. The current restraint (no toolbar clutter) is a strength; protect it
  as actions are added, per the project's new GUI rule.

The theme of this section: nothing here is *wrong*, but several things are *louder
than their value*. Quiet them so the science stays the hero.

---

## 9. Vision test

**"If I used neaPLOT every day, would I voluntarily switch today?"**

**No - not yet.** I would *keep it open beside* neaPLOT as the nicest way to open
and understand a scan, and I would do my actual analysis in neaPLOT. Switching means
finishing work, and today I cannot finish any work here.

**Obstacles, most to least important:**
1. **No analysis actions** (leveling, normalization, line profiles, ROI stats,
   spectra). Until I can *do* something, it cannot be my primary tool.
2. **No colorbar / contrast control.** I will not trust quantitative claims from an
   image whose scale I cannot see or set.
3. **No multi-channel comparison.** My core method - correlating channels at a
   location - is unsupported.
4. **No export that preserves provenance.** I cannot get a defensible figure out.
5. **No measurement library / session.** My day is many scans; one-folder-at-a-time
   is too slow to live in.
6. **Trust by track record.** It is new, and nothing in-product reconciles its
   output with the tool I already trust.
7. **Polish frictions** (readout placement, representation reset, cryptic title,
   hidden zoom) - individually small, collectively they make it feel like v0.1.

The encouraging read of that list: items 2-7 are weeks of focused product work, not
years, and item 1 is exactly the planned next phase. The Explorer has already won
the hardest, most differentiating part - making a measurement *understood* - which
is the part most tools never get right. What remains is largely conventional
imaging-tool capability plus polish. That is a very good position to be in: the soul
is right; the muscle is missing.

---

## How to use this document

Treat the **Must have** list as the v1.0 product backlog and the ranked obstacles in
Section 9 as the definition of "ready to switch." Re-run this review (as
`product-review-v0.2.md`, etc.) after each iteration and watch the obstacle list
shrink. The success metric is not feature count; it is the answer to the vision-test
question flipping from "no" to "yes," and ultimately to the North Star in
`measurement-explorer.md`: a researcher who closes the laptop thinking not "that was
good software," but "I never want to go back."

The strongest validation step is one this review cannot substitute for: **put it in
front of two or three colleagues who live in neaPLOT, open a measurement, and ask
them to narrate their thoughts without help.** Their stumbles will confirm or
reorder this list faster than any amount of internal critique.

See also: [`product-philosophy.md`](product-philosophy.md),
[`measurement-explorer.md`](measurement-explorer.md), [`vision.md`](vision.md),
[`architecture.md`](architecture.md).
