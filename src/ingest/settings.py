"""Embedding settings shared by the models and the ingest code (no heavy imports here)."""

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
# bge v1.5 retrieval: queries carry an instruction, passages are embedded as-is
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
