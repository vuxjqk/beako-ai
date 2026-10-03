"""Local embedding model (fastembed / ONNX on CPU: free, no API key, no torch).

BAAI/bge-small-en-v1.5 was chosen after a trial on known Re:ZERO questions (see
data/reports/chunk_report.md); it also provides the tokenizer used for chunk sizing, so a
chunk's token count is what the model actually sees.
"""

import os
from functools import cached_property
from pathlib import Path

import fastembed
from fastembed import TextEmbedding
from tokenizers import Tokenizer

from src.ingest.settings import MODEL_NAME, QUERY_PREFIX

CACHE_DIR = os.getenv("EMBED_CACHE_DIR", "data/models")
BATCH_SIZE = 16


class Embedder:
    def __init__(self, threads: int | None = None):
        self.model = TextEmbedding(MODEL_NAME, cache_dir=CACHE_DIR, threads=threads or os.cpu_count())
        # A private copy for counting: the model's own tokenizer must keep padding/truncation
        self._tok = Tokenizer.from_str(self.model.model.tokenizer.to_str())
        self._tok.no_truncation()
        self._tok.no_padding()

    @cached_property
    def version(self) -> str:
        """fastembed release + the exact model snapshot the weights were loaded from."""
        model_dir = Path(getattr(self.model.model, "_model_dir", ""))
        return f"fastembed=={fastembed.__version__}; snapshot={model_dir.name or 'unknown'}"

    def count_tokens(self, texts: list[str]) -> list[int]:
        """Tokens excluding the [CLS]/[SEP] pair the model adds."""
        if not texts:
            return []
        return [len(e.ids) - 2 for e in self._tok.encode_batch(texts)]

    def embed_passages(self, texts: list[str]):
        return self.model.embed(texts, batch_size=BATCH_SIZE)

    def embed_query(self, query: str) -> list[float]:
        return next(iter(self.model.embed([QUERY_PREFIX + query]))).tolist()
