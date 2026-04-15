## Overview

Blink detection is an important task in biosignal analysis. In EEG, blinks are often treated as artifacts that must be detected before correction or removal. In EOG, blink events can also be directly analyzed as meaningful physiological signals.

Many existing approaches already exist, such as:

- **BLINKER (MATLAB)** for automated blink extraction and ocular index analysis
- **MNE-Python peak detection tools** such as `mne.preprocessing.peak_finder`

These methods are useful, but they are usually based on predefined signal rules, thresholds, or handcrafted logic.

This study explores a different direction:

- use an **LLM as a source of algorithmic discovery**
- ask the LLM to suggest or construct a **new blink detection algorithm**
- implement that algorithm
- evaluate and compare it against existing methods

---

## Central Research Idea

The main contribution of this project is to study whether an LLM can help generate a **novel detection algorithm** for blink regions.

This means the LLM is expected to do more than classify peaks or label regions. Instead, the LLM is expected to help with tasks such as:

- proposing a new detection logic
- combining multiple signal features in a new way
- suggesting new rules for onset, peak, and offset detection
- designing adaptive criteria for noisy or variable biosignals
- generating interpretable algorithm steps from signal behavior

In other words, the LLM acts as an **algorithm designer**, not only as a prediction model.

---

## Problem Statement

The problem addressed in this repository is:

> Can a large language model generate or inspire a new algorithm for blink region detection in EEG/EOG signals, and can that algorithm perform competitively or better than existing blink-detection methods?

The project focuses on detecting:

- blink onset
- blink peak
- blink offset
- full blink region

---

## Motivation

Existing blink-detection algorithms can work well, but they often depend on:

- fixed thresholds
- manual tuning
- channel-specific assumptions
- dataset-specific heuristics
- handcrafted feature logic

Because of this, their performance may vary across:

- subjects
- recording devices
- EEG vs. EOG modality
- sampling rates
- noise levels
- experimental settings

This motivates the search for a **new algorithmic formulation** that may generalize better or reveal a different way of modeling blink events.

An LLM may help by reasoning over prior knowledge, signal descriptions, candidate features, and examples to suggest a new detection strategy.

---

## Research Objective

The primary objective of this study is:

> To use a large language model to propose a new blink region detection algorithm, implement it, and compare its performance with existing blink detection methods.

The specific goals are:

- identify limitations of current blink-detection methods
- use an LLM to generate a new or improved detection algorithm
- implement the LLM-generated algorithm in code
- evaluate the proposed method on EEG/EOG data
- compare it against standard approaches

---

## Existing Baseline Methods

The proposed LLM-generated algorithm will be compared against existing methods.

### 1. BLINKER (MATLAB)

BLINKER is an existing toolbox for automated blink detection and extraction from EEG-related signals.

Repository:
- https://github.com/VisLab/EEG-Blinks

Documentation:
- https://vislab.github.io/EEG-Blinks/

### 2. MNE Peak Finder

MNE-Python provides `mne.preprocessing.peak_finder`, a fast and noise-tolerant peak-finding utility that can be used as a baseline for local peak detection in biosignals.

Documentation:
- https://mne.tools/stable/generated/mne.preprocessing.peak_finder.html

---

## Proposed Study Design

The study can be structured into the following stages:

### Stage 1: Review Existing Algorithms

Study how current blink detection methods work, including:

- threshold-based methods
- peak-based methods
- rule-based pipelines
- BLINKER
- MNE peak detection tools

### Stage 2: Ask the LLM to Propose a New Algorithm

Use the LLM to generate a novel algorithm for blink region detection.

The LLM may be prompted with:

- characteristics of blink waveforms
- known limitations of current methods
- examples of blink and non-blink signal patterns
- signal features such as amplitude, prominence, width, slope, symmetry, and temporal context

The expected output is not only a label, but a **new algorithmic procedure**.

For example, the LLM may suggest:

- a new combination of morphological constraints
- adaptive multi-stage peak selection
- context-aware blink boundary detection
- feature-driven rule synthesis
- hierarchical decision logic

### Stage 3: Implement the LLM-Generated Algorithm

Convert the algorithm proposed by the LLM into code.

This implementation may include:

- preprocessing
- candidate region selection
- peak identification
- onset and offset estimation
- post-processing rules

### Stage 4: Compare Against Existing Algorithms

Benchmark the LLM-generated algorithm against:

- BLINKER
- MNE-based peak detection
- any simple threshold baseline
- any handcrafted baseline developed in this project

### Stage 5: Evaluate Performance

Evaluate whether the LLM-generated algorithm is:

- accurate
- robust
- interpretable
- generalizable
- computationally practical

---

## Role of the LLM in This Project

In this repository, the LLM is mainly used as an **algorithm discovery tool**.



### Important distinction

This project asks:

- not only **“Can an LLM detect blink regions?”**
- but more importantly **“Can an LLM invent or suggest a better algorithm for blink region detection?”**

---

## Example Conceptual Workflow

```text
EEG / EOG signal
      ↓
Review existing methods
      ↓
Extract known blink characteristics
      ↓
Prompt LLM to propose a new detection algorithm
      ↓
Translate proposed algorithm into code
      ↓
Run on annotated datasets
      ↓
Compare with BLINKER and MNE
      ↓
Analyze strengths and weaknesses
