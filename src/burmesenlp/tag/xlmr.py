"""XLM-RoBERTa POS tagger (engine="xlmr").

Wraps ``aungthuhein-dev/burmese-pos-xlmr`` on the Hugging Face Hub. This
model predicts the myPOS tagset (``n``, ``v``, ``ppm``, ``part``, ``conj``,
``adj``, ``adv``, ``pron``, ``num``, ``tnum``, ``punct``, ``sym``, ``abbr``,
``fw``, ``interj``), which is *not* mapped onto burmesenlp's rule-engine
tagset (``NOUN``/``VERB``/``POSTP``/``SFP``/... used by chunking, sentence
segmentation, clause parsing and the gazetteer). Use this engine through
:func:`burmesenlp.tag.pos_tag` for standalone tagging only -- it is not
wired into :class:`burmesenlp.pipeline.BurmeseNLP`.

Requires the optional ``xlmr`` extra (``pip install burmesenlp[xlmr]``);
``transformers``/``torch`` are imported lazily so the base install stays
lightweight.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..lexicon import Lexicon
from ..models.cache import model_cache_dir

MODEL_ID = "aungthuhein-dev/burmese-pos-xlmr"


class XLMRTagger:
    """POS tagger backed by :data:`MODEL_ID` (myPOS tagset, raw labels)."""

    def __init__(
        self,
        lexicon: Optional[Lexicon] = None,
        *,
        model_id: Optional[str] = None,
    ):
        del lexicon  # unused; kept for TaggerFactory interface parity
        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - exercised without extra
            raise ImportError(
                'engine="xlmr" requires the optional ML extra: '
                "pip install burmesenlp[xlmr]"
            ) from exc

        self._model_id = model_id or MODEL_ID
        cache_dir = str(model_cache_dir())
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._model_id, cache_dir=cache_dir
        )
        self._model = AutoModelForTokenClassification.from_pretrained(
            self._model_id, cache_dir=cache_dir
        )
        self._model.eval()
        self._id2label = self._model.config.id2label

    def tag(
        self,
        words: Sequence[str],
        *,
        mwe=None,
        mwe_pos=None,
    ) -> List[Tuple[str, str]]:
        """Tag pre-segmented *words*; myPOS labels, first-subword-only.

        ``mwe``/``mwe_pos`` are accepted for interface parity with
        :class:`burmesenlp.tag.rule.POSTagger` but ignored: this model has
        no notion of the rule engine's merged-idiom overrides.
        """
        del mwe, mwe_pos
        words = list(words)
        if not words:
            return []

        import torch

        encoding = self._tokenizer(
            words,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
        )
        with torch.no_grad():
            logits = self._model(**encoding).logits
        pred_ids = logits.argmax(dim=-1)[0].tolist()
        word_ids = encoding.word_ids(batch_index=0)

        tags: List[Optional[str]] = [None] * len(words)
        for token_index, word_index in enumerate(word_ids):
            if word_index is None or tags[word_index] is not None:
                continue  # only the first subword of each word carries the label
            tags[word_index] = self._id2label[pred_ids[token_index]]

        # Words past the tokenizer's truncation limit have no prediction.
        return [(w, t if t is not None else "UNK") for w, t in zip(words, tags)]
