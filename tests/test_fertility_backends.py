"""Real-tokenizer tests for burmesenlp.fertility.backends -- requires the
[fertility] extra installed and downloads real vocab files on first run.
Gated behind BURMESENLP_FERTILITY_TEST=1, same pattern as bench/xlmr.
"""

import os

import pytest

pytestmark = [
    pytest.mark.fertility,
    pytest.mark.skipif(
        os.environ.get("BURMESENLP_FERTILITY_TEST") != "1",
        reason="Set BURMESENLP_FERTILITY_TEST=1 to download tokenizer vocabs and run real checks",
    ),
]

MYANMAR_ONLY = "မြန်မာနိုင်ငံ၏သည်ခုနှစ်တွင်ရာခိုင်နှုန်းတိုးတက်ခဲ့သည်။"


def test_cl100k_base_never_spans_a_full_myanmar_character():
    """Mechanically confirmed claim (not inferred from decode artifacts):
    every token cl100k_base produces for Myanmar text is <3 bytes -- i.e.
    strictly less than one complete Myanmar character's UTF-8 encoding
    (always 3 bytes), so no token can represent even one full character,
    let alone a multi-character merge."""
    from burmesenlp.fertility.backends import load_backend

    backend = load_backend("cl100k_base")
    ids = backend.encode(MYANMAR_ONLY)
    lengths = backend.token_byte_lengths(ids)
    assert max(lengths) < 3
    assert all(length in (1, 2) for length in lengths)


def test_o200k_base_produces_real_multi_character_merges():
    from burmesenlp.fertility.backends import load_backend

    backend = load_backend("o200k_base")
    ids = backend.encode(MYANMAR_ONLY)
    lengths = backend.token_byte_lengths(ids)
    assert max(lengths) >= 3
    assert all(length >= 3 for length in lengths)  # every token is >= one full character


def test_qwen_and_mistral_byte_length_schemes_are_detected_correctly():
    """Qwen2.5 is byte-level BPE (piece char count == byte length);
    Mistral is a literal-Unicode (SentencePiece-derived) vocab (needs
    UTF-8-encoding the piece text). Getting this backwards would silently
    corrupt every byte-length claim for whichever tokenizer got the wrong
    formula -- verified against a known single-character round trip.

    Mistral prepends a synthetic leading-space token (SentencePiece's own
    convention, confirmed empirically: encoding "က" alone yields a
    1-byte "▁" token before the 3-byte character token) that Qwen does
    not add -- itself a concrete illustration of why per-run-independent
    tokenization (measure.CAVEAT_PER_RUN_OVERSTATES_TOTAL) overstates the
    true whole-document total more for SentencePiece-style tokenizers
    than byte-level ones.
    """
    from burmesenlp.fertility.backends import load_backend

    qwen = load_backend("qwen2.5")
    assert qwen._byte_level is True
    mistral = load_backend("mistral")
    assert mistral._byte_level is False

    # Qwen: no synthetic prefix, exactly 3 bytes for one Myanmar character.
    qwen_ids = qwen.encode("က")
    assert sum(qwen.token_byte_lengths(qwen_ids)) == 3

    # Mistral: a synthetic 1-byte leading-space token, then the 3-byte
    # character -- 4 bytes total, by design, not a bug.
    mistral_ids = mistral.encode("က")
    mistral_lens = mistral.token_byte_lengths(mistral_ids)
    assert sum(mistral_lens) == 4
    assert mistral_lens == [1, 3]


def test_all_four_backends_load_and_encode():
    from burmesenlp.fertility.backends import TOKENIZER_NAMES, load_backend

    for name in TOKENIZER_NAMES:
        backend = load_backend(name)
        ids = backend.encode(MYANMAR_ONLY)
        assert len(ids) > 0
