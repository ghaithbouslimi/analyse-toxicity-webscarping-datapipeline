from unittest.mock import MagicMock, Mock

import pytest
from pymongo.errors import AutoReconnect

from analyse_toxicite.stockage import connexion


def test_ping_en_echec_ferme_client(settings, monkeypatch):
    client = MagicMock()
    client.admin.command.side_effect = AutoReconnect("MongoDB indisponible")
    monkeypatch.setattr(connexion, "MongoClient", Mock(return_value=client))
    with pytest.raises(AutoReconnect, match="MongoDB indisponible"):
        connexion.connecter(settings)
    client.close.assert_called_once_with()
