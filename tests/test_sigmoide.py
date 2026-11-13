from types import SimpleNamespace

import pytest
import torch

from analyse_toxicite.prediction.service import ServicePrediction


def test_logit_unique_utilise_sigmoide(settings):
    service = ServicePrediction(settings)
    service.model = lambda **kwargs: SimpleNamespace(logits=torch.tensor([[0.0]]))

    class Tokenizer:
        def pad(self, batch, **kwargs):
            return {"input_ids": torch.tensor([[1, 2]])}

    service.tokenizer = Tokenizer()
    assert service._calculer([{}], torch) == [0.5]


def test_sortie_incompatible_rejetee(settings):
    service = ServicePrediction(settings)
    service.model = lambda **kwargs: SimpleNamespace(logits=torch.tensor([[0.0, 0.0]]))

    class Tokenizer:
        def pad(self, batch, **kwargs):
            return {"input_ids": torch.tensor([[1, 2]])}

    service.tokenizer = Tokenizer()
    with pytest.raises(ValueError, match="Sortie du modèle"):
        service._calculer([{}], torch)


def test_nan_rejete(settings):
    service = ServicePrediction(settings)
    service.model = lambda **kwargs: SimpleNamespace(logits=torch.tensor([[float("nan")]]))

    class Tokenizer:
        def pad(self, batch, **kwargs):
            return {"input_ids": torch.tensor([[1, 2]])}

    service.tokenizer = Tokenizer()
    with pytest.raises(ValueError, match="non finie"):
        service._calculer([{}], torch)
