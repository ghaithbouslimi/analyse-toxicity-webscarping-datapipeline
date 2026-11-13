from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Parametres(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(8000, ge=1, le=65535)
    api_host_port: int = Field(8005, ge=1, le=65535)
    api_max_pending_requests: int = Field(2, ge=1)
    mongodb_uri: str = "mongodb://localhost:27018"
    mongodb_database: str = "analyse_toxicite"
    collection_window_days: int = Field(14, gt=0)
    max_articles_per_site: int = Field(30, gt=0)
    http_timeout_seconds: float = Field(20, gt=0)
    http_max_attempts: int = Field(3, gt=0)
    request_delay_seconds: float = Field(2, gt=0)
    max_concurrent_requests: int = Field(4, gt=0)
    model_id: str = "unitary/multilingual-toxic-xlm-roberta"
    model_revision: str = Field(..., pattern=r"^[a-f0-9]{40}$")
    model_device: str = "cpu"
    model_dtype: Literal["float32", "float16", "bfloat16"] = "float16"
    model_cache_dir: str = "cache/modeles"
    inference_batch_size: int = Field(1, gt=0)
    inference_concurrency: int = Field(1, gt=0)
    torch_threads: int = Field(1, gt=0)
    toxicity_threshold: float = Field(0.5, ge=0, le=1)
    high_score_threshold: float = Field(0.8, ge=0, le=1)
    max_text_characters: int = Field(20000, gt=0)
    sources_file: Path = Path("configuration/sources.yaml")

    @model_validator(mode="after")
    def verifier_seuils(self):
        if self.toxicity_threshold >= self.high_score_threshold:
            raise ValueError("TOXICITY_THRESHOLD doit précéder HIGH_SCORE_THRESHOLD")
        return self


def charger_sources(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
