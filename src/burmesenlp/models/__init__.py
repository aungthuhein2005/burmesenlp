"""Model loading architecture for v2+ hybrid and v3 deep-learning backends.

v1 is entirely rule-based: this package ships **no** model weights and
does not depend on TensorFlow, PyTorch, or Hugging Face.  Future CRF,
FastText, Transformer, SentencePiece, and EvoPiece artifacts will be
registered here and cached under the model cache directory.
"""

from __future__ import annotations

from .cache import clear_model_cache, model_cache_dir
from .loader import ModelError, load_model
from .registry import available_models, model_info, register_model

__all__ = [
    "ModelError",
    "available_models",
    "clear_model_cache",
    "load_model",
    "model_cache_dir",
    "model_info",
    "register_model",
]
