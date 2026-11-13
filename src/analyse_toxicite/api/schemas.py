from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class PredictionEntree(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(
        default=None,
        min_length=1,
        description="Texte à analyser. Omettre ce champ pour extraire l’article depuis source_url.",
    )
    source_url: HttpUrl | None = Field(
        default=None,
        description=(
            "URL de l’article à extraire si text est absent ; sinon, métadonnée du texte fourni."
        ),
    )

    @field_validator("text")
    @classmethod
    def texte_requis(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Le texte doit contenir des caractères visibles")
        return value

    @model_validator(mode="after")
    def texte_ou_url(self):
        if self.text is None and self.source_url is None:
            raise ValueError("Fournir text ou source_url")
        return self


class ArticleSortie(BaseModel):
    article_id: str
    title: str
    source_url: str
    canonical_url: str
    site: str
    language: str
    published_at: datetime | None
    collected_at: datetime
    http_status: int
    text_characters: int
    content_hash: str
    status: str


class PredictionSortie(BaseModel):
    prediction_id: str
    prediction: str
    toxicity_score: float
    confidence_score: float
    category: str
    date: datetime
    model: dict[str, Any]
    config_hash: str
    passage_scores: list[float]
    token_count: int
    calibrated: bool
    latency_seconds: float
    rss_mb: float
    article: ArticleSortie | None = None
