# Architectural Plan: Pluggable Blink Detection Pipeline with Epoch-Aware and Long Eye Closure Support

---

## 1. Strategy Landscape and What Each Strategy Actually Does

The original plan treated Step 1 as a simple swap — three strategies producing the same DataFrame. But your updated thinking reveals something more nuanced. The strategies don't just differ in *how* they find candidates; they differ in *what kind of information they produce* and *how much of the downstream pipeline they actually need*. This realization reshapes the architecture significantly.

### 1.1 Strategy A — Original BLINKER (`get_blink_position`)

This remains the baseline. It uses BLINKER's own peak/valley detection on the raw continuous (or concatenated-good-epochs) signal. It produces point-estimate candidates (a peak sample index), and it relies on every subsequent step — fitting (Step 2), statistics (Step 3), good-blink masking (Step 4), property computation (Step 5), and pAVR filtering (Step 6) — because BLINKER's internal logic was designed as a tightly coupled sequence where each step feeds the next. This is the "full pipeline" track.

### 1.2 Strategy B — MNE `find_eog_events` (Available but Not Preferred)

This strategy uses MNE's correlation-based or threshold-based EOG event detection. You've correctly identified its fundamental weakness: it requires the user to specify a `thresh` parameter, and that threshold is arbitrary and dataset-dependent. What works for a clean lab recording with cooperative participants will miss blinks entirely in a noisy clinical dataset, or drown in false positives for a drowsy subject with slow, low-amplitude blinks. This is the exact problem that autoreject's data-driven thresholding was designed to eliminate.

That said, Strategy B still has value as a *fast, lightweight reference* implementation. It's computationally cheap, well-understood, and its failure modes are well-documented in the literature. For benchmarking purposes, having it available to compare against the more sophisticated strategies is useful. The plan should keep it as an option but clearly mark it as a manually-tuned baseline rather than a recommended production strategy.

Because `find_eog_events` produces point-estimate candidates (sample indices of detected events), its output shape is similar to Strategy A's, and it feeds into the full Steps 2–6 pipeline without modification.

### 1.3 Strategy C — Autoreject as a Blink Region Finder

This is where the design gets genuinely novel, and the document you shared articulates the conceptual insight beautifully. Let me restate the core logic in architectural terms so the plan captures it precisely.

**The sub-epoching trick.** Your long epochs (30–60 seconds) are temporarily divided into many short, non-overlapping windows (e.g., 500ms or 1 second). Each mini-window becomes a "trial" in autoreject's terminology. Autoreject then learns, from the distribution of amplitudes across all these mini-windows, what "normal" looks like for each channel. Mini-windows that deviate from normal get flagged in the `reject_log`, which is a binary matrix of shape (n_windows × n_channels).

**The spatial filtering step.** A flagged mini-window is only a blink *candidate* if the channels that were flagged are frontal (Fp1, Fp2, and their neighbors). If the flagged channels are temporal or occipital, the anomaly is more likely a muscle artifact or alpha burst, not a blink. So Strategy C applies a spatial mask to the reject_log: it only keeps rows where the flagged-bad columns intersect with a predefined set of blink-relevant channels.

**The output is a region, not a point.** Unlike Strategies A and B, which produce a peak sample index that you then extend into a region, Strategy C directly produces the time window that was flagged. This is actually a better fit for what `FitBlinks` (Step 2) needs, because FitBlinks works with blink onset/offset regions anyway. The candidate DataFrame from Strategy C would contain the start and end sample of each flagged window, and Step 2 can refine these boundaries during fitting.

**Why it's data-adaptive.** The threshold autoreject uses is not manually set. Global Autoreject finds a per-channel threshold via cross-validation across all the mini-windows. This means the sensitivity automatically adjusts to the noise level of your specific recording. A clean dataset gets a tight threshold (only genuine blinks are flagged); a noisy dataset gets a looser threshold (only the truly extreme deviations are flagged, not the general noise floor). This directly addresses the weakness you identified in Strategy B.

**How bad-epoch dropping interacts.** Because genuinely bad epochs were already removed before this point, the mini-windows that autoreject sees are drawn from clean data. This means autoreject's learned thresholds are not polluted by catastrophic artifacts, making them tighter and more sensitive to the moderate-amplitude deviations that blinks produce. This is a clever interaction between the earlier quality control step and Strategy C's repurposing of autoreject.

### 1.4 Strategies D, E, F, and Beyond — The Partial Pipeline Concept

Your observation that some strategies might not need all of Steps 2–6 introduces an important architectural concept: **pipeline steps should be individually optional, not hardcoded as a monolithic sequence.**

Consider a hypothetical Strategy D that uses a highly sophisticated detector which already fits blink shapes internally (perhaps a deep learning model trained on blink morphology). Such a strategy might produce output rich enough that Step 2 (FitBlinks) is redundant or even counterproductive — refitting an already-fitted blink could distort it. Similarly, a strategy that uses its own amplitude-based filtering might render Step 3 (blink statistics) or Step 4 (good-blink masking) unnecessary.

The architectural implication is that each strategy should declare which downstream steps it requires. The pipeline orchestrator reads this declaration and executes only the requested steps. The declaration could be as simple as a list of step numbers or step names that the strategy wants the orchestrator to run. By default (for Strategies A, B, and C), all steps are enabled. But the interface allows future strategies to opt out of specific steps.

This also opens the door to an interesting experimental question: even for existing strategies, what happens if you skip Step 3 or Step 6? The comparison harness (described later) can systematically ablate individual steps and measure the impact on final blink quality, giving you empirical evidence for which steps are truly necessary versus which are legacy holdovers from MATLAB BLINKER.

---

## 2. Long Eye Closure Detection: A Distinct but Related Contribution

Long eye closures are fundamentally different from blinks, and most blink detection algorithms either ignore them or actively reject them. A blink is a fast, reflexive event — typically 100–400ms — characterized by a sharp rise and fall in the EOG/EEG signal. A long eye closure is a sustained event — often 500ms to several seconds — where the eyelids remain closed, producing a prolonged signal deflection that eventually returns to baseline when the eyes reopen. They occur during drowsiness, fatigue, microsleeps, and voluntary sustained closures.

### 2.1 Why Existing Algorithms Miss Them

BLINKER's fitting step (Step 2, `FitBlinks`) uses a model that assumes blink-like morphology: a roughly symmetric or mildly asymmetric peak with a well-defined rise and fall. A long eye closure has a rise, then a plateau (or slow drift), then a fall. The fitting model either rejects this shape as a bad fit, or it tries to fit just the closing or opening transient and misses the sustained closure in between. Similarly, the amplitude statistics in Step 3 and the good-blink mask in Step 4 are calibrated for blink-like amplitudes and durations, so a long closure's atypical duration gets it filtered out.

The MNE approach (`find_eog_events`) is explicitly peak-centric — it looks for sharp peaks, which a long closure doesn't produce. Autoreject-based detection (Strategy C) is actually the most promising for long closures, because a 500ms mini-window containing a sustained closure would have elevated amplitude across its entire duration, making it clearly anomalous. But the spatial filtering and downstream steps would still need to distinguish a closure from a blink.

### 2.2 Architectural Approach: Parallel Detection Track

Rather than trying to force long eye closures through the same pipeline as blinks, the plan treats them as a **parallel detection track** that shares infrastructure but has its own logic. The design works as follows.

**Detection.** Long closures are identified either as candidates that were rejected by the blink pipeline (they were detected by Step 1 but failed the fitting or morphology checks in Steps 2–4) or as prolonged amplitude deviations found by a dedicated duration-aware detector. The autoreject-based Strategy C is particularly well-suited here: if you use a longer sub-window (e.g., 1–2 seconds), the reject_log will naturally capture sustained closures as anomalous windows, and you can distinguish them from blinks by their duration.

**Characterization.** Instead of computing blink-specific kinematics (velocity ratios, closing/opening time), the long closure track computes closure-specific properties: total closure duration, closing speed (from the onset transient), opening speed (from the offset transient), plateau amplitude, and plateau stability (how much the signal drifts during the closed period). These are distinct from blink properties and serve different downstream analyses (drowsiness assessment, fatigue monitoring, microsleep detection).

**Integration.** The blink pipeline and the long closure pipeline share the same signal accessor and epoch metadata infrastructure. Their outputs are stored in parallel structures — `detector.all_data_info` for blinks and a corresponding `detector.all_closure_info` for long closures — so that downstream consumers can access both.

### 2.3 The Boundary Between Blink and Long Closure

There's an ambiguous zone — roughly 300–600ms — where an event could be either a slow blink or a short closure. The plan handles this with a **classification step** after both tracks have run. Events in the ambiguous duration range are compared on morphology: if the shape is roughly symmetric (rise ≈ fall, no plateau), it's classified as a slow blink and routed to the blink output. If it has a discernible plateau or strong asymmetry (fast close, slow open, or vice versa), it's classified as a short closure. This classification can be rule-based initially and upgraded to a learned classifier later if needed.

---

## 3. Revised Pipeline Architecture

Bringing all of this together, the revised architecture has the following components.

### 3.1 The Strategy Interface (Revised)

Every Step 1 strategy must satisfy a contract that includes three elements. First, the `detect` method, which accepts the signal, parameters, and epoch metadata, and returns a candidate DataFrame. Second, a `required_steps` declaration, which is a list of downstream step identifiers that this strategy needs (defaulting to all of Steps 2–6). Third, a `supports_closure_detection` flag, indicating whether this strategy can also produce long closure candidates (true for Strategy C, false for A and B by default).

### 3.2 The Step Registry

Instead of hardcoding Steps 2–6 as a fixed sequence, each step is registered as a named, callable unit in a step registry. The orchestrator looks up which steps a strategy requires and executes only those, in order. Each step has a defined input schema (what DataFrame columns and auxiliary data it expects) and output schema (what it adds or modifies). This makes it safe to skip steps — the orchestrator can verify that the remaining steps have their input requirements met even after a step is removed.

### 3.3 The Epoch Metadata Object (Unchanged from Original Plan)

This carries epoch boundaries, the bad epoch mask, and annotation provenance. It's consumed by every strategy and is available to all downstream steps for boundary-aware processing.

### 3.4 The Signal Accessor (Unchanged from Original Plan)

Abstracts over Raw vs. Epochs objects. Handles concatenation of good epochs, index remapping, and boundary-guarded segment extraction for the fitting step.

### 3.5 The Pipeline Orchestrator (Revised)

The orchestrator now does the following sequence. First, it instantiates the chosen strategy. Second, it calls the strategy's `detect` method to get candidates. Third, it reads the strategy's `required_steps` and executes only those steps from the registry. Fourth, if the strategy supports closure detection, it runs the parallel long closure track. Fifth, it collects all outputs into a unified result object that contains both blink and closure data.

### 3.6 The Long Closure Track

A parallel processing path that receives either dedicated closure candidates from a strategy that supports them, or receives rejected candidates from the blink pipeline, and characterizes them with closure-specific properties. It has its own simpler step sequence: closure boundary refinement, plateau detection, closure property computation, and duration-based quality filtering.

### 3.7 The Comparison Harness (Revised)

Now supports not just strategy comparison but also **step ablation studies**. You can run Strategy A with all steps, then Strategy A with Step 3 skipped, then Strategy A with Steps 3 and 6 skipped, and compare the final outputs. This gives you empirical evidence for the contribution of each step, which is valuable both for understanding the pipeline and for designing lean future strategies.

---

## 4. Sub-Window Size Selection for Strategy C

Since the document raised this as an open question, the plan should include a principled approach. The sub-window size controls a tradeoff between temporal resolution and statistical stability. A 500ms window gives you good temporal localization (you know roughly when the blink happened within a half-second) but produces more windows with partial blinks at boundaries. A 1-second window is more stable (most blinks fit entirely within one window) but gives coarser localization.

The recommended approach is to use the **expected blink duration as a guide**: choose a sub-window size of roughly 2–3× the typical blink duration (150–400ms), putting you in the 400ms–1000ms range. Starting at 500ms for normal populations and 1000ms for drowsy/fatigued populations (where blinks and closures are slower) is a reasonable default. The comparison harness can then sweep sub-window sizes to find the optimal value for a given dataset.

---

## 5. Summary of All Components

**Strategy Interface** — defines `detect`, `required_steps`, and `supports_closure_detection` for all candidate finders.

**Strategy A (BLINKER)** — existing `get_blink_position`, full pipeline, epoch-aware via bad epoch mask.

**Strategy B (MNE find_eog_events)** — threshold-based reference baseline, full pipeline, kept for benchmarking but not recommended as primary due to manual threshold dependence.

**Strategy C (Autoreject Region Finder)** — sub-epochs long signals into mini-windows, uses Global Autoreject to find amplitude-anomalous regions, applies spatial filtering to isolate frontal-channel anomalies as blink candidates, and naturally supports long eye closure detection via longer sub-windows.

**Strategies D–F (Future)** — accommodated by the step registry and `required_steps` mechanism, allowing any subset of Steps 2–6 to be skipped when a strategy's output is already rich enough.

**Step Registry** — Steps 2–6 as individually callable, skippable units with defined input/output schemas.

**Long Eye Closure Track** — parallel detection and characterization path for sustained closures, with its own property computation and a blink-vs-closure classifier for ambiguous-duration events.

**Epoch Metadata and Signal Accessor** — shared infrastructure for epoch-aware processing across all strategies and steps.

**Pipeline Orchestrator** — routes candidates through the appropriate steps based on strategy requirements, runs the closure track when supported, and collects unified outputs.

**Comparison and Ablation Harness** — supports both cross-strategy comparison and within-strategy step ablation for systematic experimentation.

---

