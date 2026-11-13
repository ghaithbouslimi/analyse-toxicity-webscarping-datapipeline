import pytest

from analyse_toxicite.prediction.decoupage import decouper
from analyse_toxicite.prediction.service import categoriser


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "non_toxique"),
        (0.4999, "non_toxique"),
        (0.5, "legerement_toxique"),
        (0.7999, "legerement_toxique"),
        (0.8, "tres_toxique"),
        (1, "tres_toxique"),
    ],
)
def test_frontieres(score, expected):
    assert categoriser(score, 0.5, 0.8) == expected


def test_decoupage_sans_perte():
    class Tokenizer:
        def num_special_tokens_to_add(self, pair=False):
            return 2

        def prepare_for_model(self, tokens, **kwargs):
            return {"input_ids": [-1, *tokens, -2]}

    tokens = list(range(1300))
    passages = list(decouper(tokens, Tokenizer(), 512))
    assert len(passages) == 3
    assert all(len(item["input_ids"]) <= 512 for item in passages)
    assert [token for item in passages for token in item["input_ids"][1:-1]] == tokens
