# -*- coding: utf-8 -*-
"""Token-fertility profiler: how many tokens common LLM tokenizers spend
per unit of Burmese text, measured with a declared methodology instead
of the uncited 4x-9x (up to 13x) figures circulating for this language.

Requires the optional ``fertility`` extra for the tokenizer backends
(``pip install burmesenlp[fertility]``); script segmentation and corpus
loading have no extra dependency. See :mod:`burmesenlp.fertility.measure`
for the denominator/caveat contract and :mod:`burmesenlp.fertility.backends`
for which tokenizers are covered and why.
"""
from .measure import (
    Denominators,
    FertilityResult,
    aggregate_distribution,
    measure_text,
)
from .script import ScriptRun, segment_script_runs

__all__ = [
    "Denominators",
    "FertilityResult",
    "measure_text",
    "aggregate_distribution",
    "ScriptRun",
    "segment_script_runs",
]
