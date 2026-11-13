import hashlib
import importlib.metadata
import json
import os
import threading
import time
from datetime import UTC, datetime

import psutil

from analyse_toxicite.prediction.decoupage import decouper


def categoriser(score, threshold, high):
    if score >= high:
        return "tres_toxique"
    if score >= threshold:
        return "legerement_toxique"
    return "non_toxique"


class ServicePrediction:
    def __init__(self, settings):
        self.settings = settings
        self.tokenizer = None
        self.model = None
        self.lock = threading.Lock()
        self.slot = threading.BoundedSemaphore(settings.inference_concurrency)
        self.load_metrics = {}

    def charger(self):
        with self.lock:
            if self.model is not None:
                return
            os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
            os.environ.setdefault("OMP_NUM_THREADS", str(self.settings.torch_threads))
            os.environ.setdefault("MKL_NUM_THREADS", str(self.settings.torch_threads))
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            os.environ.setdefault("RAYON_NUM_THREADS", "1")
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            start = time.perf_counter()
            torch.set_num_threads(self.settings.torch_threads)
            if torch.get_num_interop_threads() != 1:
                torch.set_num_interop_threads(1)
            kwargs = {
                "revision": self.settings.model_revision,
                "cache_dir": self.settings.model_cache_dir,
                "trust_remote_code": False,
            }
            tokenizer = AutoTokenizer.from_pretrained(self.settings.model_id, **kwargs)
            model = AutoModelForSequenceClassification.from_pretrained(
                self.settings.model_id,
                use_safetensors=False,
                dtype=getattr(torch, self.settings.model_dtype),
                **kwargs,
            )
            labels = {int(key): value.lower() for key, value in model.config.id2label.items()}
            if labels != {0: "toxic"} or model.config.num_labels != 1:
                raise ValueError(f"Tête de classification inattendue: {labels}")
            model.to(self.settings.model_device).eval()
            self.max_length = min(
                tokenizer.model_max_length,
                model.config.max_position_embeddings - model.config.pad_token_id - 1,
            )
            self.tokenizer = tokenizer
            self.model = model
            self.config = {
                "model_id": self.settings.model_id,
                "revision": self.settings.model_revision,
                "label": "toxic",
                "activation": "sigmoid",
                "aggregation": "max-v1",
                "max_length": self.max_length,
                "toxicity_threshold": self.settings.toxicity_threshold,
                "high_score_threshold": self.settings.high_score_threshold,
                "device": self.settings.model_device,
                "dtype": self.settings.model_dtype,
                "batch_size": self.settings.inference_batch_size,
                "torch_threads": self.settings.torch_threads,
                "torch_version": importlib.metadata.version("torch"),
                "transformers_version": importlib.metadata.version("transformers"),
            }
            self.config_hash = hashlib.sha256(
                json.dumps(self.config, sort_keys=True).encode()
            ).hexdigest()
            self.load_metrics = {
                "load_seconds": time.perf_counter() - start,
                "rss_mb": psutil.Process().memory_info().rss / 1024**2,
            }

    def predire(self, text):
        if not text.strip():
            raise ValueError("Texte vide")
        self.charger()
        import torch

        with self.slot:
            start = time.perf_counter()
            tokens = self.tokenizer.encode(
                text, add_special_tokens=False, truncation=False, verbose=False
            )
            scores = []
            batch = []
            with torch.inference_mode():
                for passage in decouper(tokens, self.tokenizer, self.max_length):
                    batch.append(passage)
                    if len(batch) == self.settings.inference_batch_size:
                        scores.extend(self._calculer(batch, torch))
                        batch = []
                if batch:
                    scores.extend(self._calculer(batch, torch))
            if not scores:
                raise ValueError("Aucun token exploitable")
            score = max(scores)
            toxic = score >= self.settings.toxicity_threshold
            return {
                "prediction": "toxique" if toxic else "non_toxique",
                "toxicity_score": score,
                "confidence_score": score if toxic else 1 - score,
                "category": categoriser(
                    score, self.settings.toxicity_threshold, self.settings.high_score_threshold
                ),
                "date": datetime.now(UTC),
                "model": self.config,
                "config_hash": self.config_hash,
                "passage_scores": scores,
                "token_count": len(tokens),
                "calibrated": False,
                "latency_seconds": time.perf_counter() - start,
                "rss_mb": psutil.Process().memory_info().rss / 1024**2,
            }

    def _calculer(self, batch, torch):
        inputs = self.tokenizer.pad(batch, padding=True, return_tensors="pt")
        inputs = {key: value.to(self.settings.model_device) for key, value in inputs.items()}
        logits = self.model(**inputs).logits
        if logits.ndim != 2 or logits.shape[1] != 1:
            raise ValueError("Sortie du modèle incompatible")
        if not torch.isfinite(logits).all():
            raise ValueError("Sortie numérique non finie")
        return torch.sigmoid(logits[:, 0]).cpu().tolist()
