"""Pinned local models. Download is explicit; inference defaults to offline."""
def download_models(config):
    # Public weights/config only; no remote Python or pickle weights are fetched.
    from huggingface_hub import snapshot_download
    for kind in ("embedding", "reranker"):
        snapshot_download(config[f"{kind}_model"], revision=config[f"{kind}_revision"],
                          allow_patterns=["*.json", "*.txt", "*.safetensors", "*.model"],
                          max_workers=2)


def local_snapshot(model_id, revision):
    # Pass a filesystem path to Sentence Transformers, not a repo ID. With a
    # repo ID it may request model-card metadata even with local_files_only=True.
    from huggingface_hub import snapshot_download
    return snapshot_download(model_id, revision=revision, local_files_only=True)


class LocalModels:
    def __init__(self, config):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(config["threads"])
        torch.manual_seed(42)
        self.config = config
        snapshot = local_snapshot(config["embedding_model"], config["embedding_revision"])
        self.encoder = SentenceTransformer(snapshot,
                                          device=config["device"], local_files_only=True,
                                          trust_remote_code=False, model_kwargs={"use_safetensors": True})
        self.encoder.max_seq_length = config["max_model_tokens"]
        self._reranker = None

    def encode(self, texts, kind):
        if kind not in {"query", "passage"}:
            raise ValueError("Embedding kind must be query or passage")
        texts = [f"{kind}: {t}" for t in texts]
        lengths = [len(self.encoder.tokenizer.encode(t, add_special_tokens=True, truncation=False)) for t in texts]
        if max(lengths, default=0) > self.config["max_model_tokens"]:
            raise ValueError(f"Embedding input too long ({max(lengths)} tokens); shorten chunks, never silently truncate")
        return self.encoder.encode(texts, batch_size=self.config["batch_size"], normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False).astype("float32")

    def rerank(self, query, texts):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            snapshot = local_snapshot(self.config["reranker_model"], self.config["reranker_revision"])
            self._reranker = CrossEncoder(snapshot,
                                         device=self.config["device"], local_files_only=True,
                                         trust_remote_code=False, max_length=self.config["max_model_tokens"],
                                         model_kwargs={"use_safetensors": True})
        pairs = [(query, t) for t in texts]
        lengths = [len(self._reranker.tokenizer.encode(q, t, truncation=False)) for q, t in pairs]
        if max(lengths, default=0) > self.config["max_model_tokens"]:
            raise ValueError("Reranker input too long; shorten query/chunks instead of truncating")
        return self._reranker.predict(pairs, batch_size=self.config["batch_size"],
                                      show_progress_bar=False, convert_to_numpy=True).reshape(-1)
