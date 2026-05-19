---
title: 'pyblinker: Eye-Blink Detection and Feature Extraction from EEG, EOG, and Video-Based Measures'
tags:
  - Python
  - neuroscience
  - eye aspect ratio
  - EEG
  - EOG

authors:

  - name: Rodney Petrus Balandong
    orcid: 0000-0003-2567-9745
    affiliation: "1"

affiliations:
 - name: Faculty of Science and Technology, Universiti Malaysia Sabah, Malaysia
   index: 1

date: 19 August 2025
bibliography: paper.bib

---

# Summary

`pyblinker` is a Python package primarily intended for automated detection of eye-blink artifacts in diverse biosignals,
including electroencephalography (EEG), electrooculography (EOG), and Eye Aspect Ratio (EAR). It addresses the limitations of
existing MATLAB-based tools like BLINKER [@Kleifges2017],
offering a Python-based, open-source solution for researchers analyzing various types of physiological data.

A key benefit of `pyblinker` is its enhanced functionality and broader applicability compared to `BLINKER`. By expanding input compatibility beyond EEG/EOG to include EAR, and by integrating seamlessly with the MNE-Python ecosystem,
`pyblinker` provides a more versatile and accessible tool. This facilitates efficient and reproducible biosignal analysis
workflows across neuroscience and related fields, ultimately streamlining research and improving data quality.

## Features

`pyblinker` provides a comprehensive set of tools for blink analysis, including:

* Extraction of eye blinks from EEG, EOG, and EAR data.
* Compatibility with both continuous and epoch-based datasets.
* Support for single-channel and multi-channel signals.
* Computation of blink characteristics such as amplitude, duration, and peak-to-peak interval.
* Per-epoch feature extraction, including EAR metrics, energy features, frequency-domain measures, blink morphology, and waveform features.
* Generation of blink time series for visualization and validation.

# Statement of need
Accurate analysis of eye-blink is paramount in biosignal research, providing crucial insights into physiological and
cognitive processes across diverse modalities beyond traditional EEG, such as EOG and even video-based EAR. However, manual identification and annotation of these artifacts is notoriously time-consuming, demands specialized expertise,
and becomes a significant bottleneck, especially with the increasing scale of modern biosignal datasets.

The MATLAB-based BLINKER [@Kleifges2017] algorithm offers automated ocular index extraction specifically from
EEG and EOG data.  This MATLAB package automatically identifies blink-related  components in EEG/EOG, calculates indices,
generates reports, and provides summaries. Despite its sophistication for EEG/EOG, BLINKERS has limitations hindering broader use.  Firstly, `BLINKER` input is strictly limited to EEG or EOG channels, excluding valuable ocular measures like EAR derived
from video eye-tracking, which are increasingly integrated into multimodal biosignal analysis. Secondly, and critically for many researchers, `BLINKERS` reliance on MATLAB creates a significant barrier to entry. The requirement for a proprietary MATLAB license restricts access, particularly within the growing open-source and
Python-centric scientific community, limiting the adoption of this otherwise valuable tool.

The scientific community, particularly in neuroscience and related fields, increasingly uses Python for biosignal analysis,
with MNE-Python [@Gramfort2013] becoming a leading open-source platform.
MNE-Python's open nature, extensive features, and community support make it ideal for EEG, MEG, and broader biosignal research.
Integrating specialized tools into MNE-Python offers seamless workflows, access to diverse algorithms, coding best practices,
and established biosignal analysis conventions. For example, MNE-Python's epoching is standard for time-windowed biosignal
analysis related to events of interest. Integrating eye-blink detection within this framework allows straightforward derivation of
artifact metrics within relevant epochs, crucial for many biosignal studies. Furthermore, the trend towards agentic code development favors Python tools for automated workflows.
A Python-based solution like `pyblinker` is more readily integrated into automated biosignal analysis pipelines than MATLAB-based alternatives.


# Acknowledgements

Development of `pyblinker` was funded by the Ministry of Higher Education Malaysia (grants FRGS-EC 026-2024 to RPB).

# References
