import logging


def configurer(niveau):
    logging.basicConfig(
        level=niveau, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True
    )
