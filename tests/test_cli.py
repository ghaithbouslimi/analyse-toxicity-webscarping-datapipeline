import socket
import sys
from unittest.mock import Mock

import pytest
import uvicorn

from analyse_toxicite import cli


def test_port_occupe_signale_avant_demarrage(settings, monkeypatch, capsys):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        settings.api_host = "127.0.0.1"
        settings.api_port = listener.getsockname()[1]
        monkeypatch.setattr(cli, "Parametres", lambda: settings)
        monkeypatch.setattr(cli.faulthandler, "enable", Mock())
        monkeypatch.setattr(sys, "argv", ["toxicite", "servir"])
        run = Mock()
        monkeypatch.setattr(uvicorn, "run", run)
        with pytest.raises(SystemExit) as result:
            cli.main()
    assert result.value.code == 1
    assert "Le port est indisponible" in capsys.readouterr().err
    run.assert_not_called()


def test_port_libre_demarre_uvicorn(settings, monkeypatch):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        settings.api_port = probe.getsockname()[1]
    settings.api_host = "127.0.0.1"
    monkeypatch.setattr(cli, "Parametres", lambda: settings)
    fault_handler = Mock()
    monkeypatch.setattr(cli.faulthandler, "enable", fault_handler)
    monkeypatch.setattr(sys, "argv", ["toxicite", "servir"])
    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    cli.main()
    fault_handler.assert_called_once_with()
    run.assert_called_once_with(
        "analyse_toxicite.api.application:creer_application",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
    )
