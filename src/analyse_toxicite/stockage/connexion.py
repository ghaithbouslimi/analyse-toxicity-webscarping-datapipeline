from pymongo import MongoClient


def connecter(settings):
    client = MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=30000,
        tz_aware=True,
    )
    try:
        client.admin.command("ping")
    except Exception:
        client.close()
        raise
    return client
