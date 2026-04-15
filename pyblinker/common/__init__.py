"""Shared utilities used by all epoch-detection strategy packages.

Modules
-------
bad_epochs
    Valid-epoch index resolution and bad-epoch simulation.
epoch_input
    PreparedEpochDetectionInput dataclass and the preparation function.
epoch_io
    Blink-table normalization and epoch metadata attachment.
epoch_channel
    EpochChannelBlinkResult dataclass and concatenated-signal mapping.
result_aggregation
    Channel-summary aggregation and candidate channel selection.
pipeline_utils
    Helpers shared across multiple strategy pipelines:
    empty-annotation factory, blink-table finalization,
    epoch-boundary building, and signal-by-epoch extraction.
validation
    Generic blink-table matching metrics used by the evaluation layer.
"""
