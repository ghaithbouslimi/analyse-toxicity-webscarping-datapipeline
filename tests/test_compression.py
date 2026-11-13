import asyncio
import gzip

import httpx

from analyse_toxicite.collecte.telechargement import Telechargeur


def test_reponse_gzip_decodee_une_fois(settings, source):
    def handle(request):
        text = "User-agent: *\nDisallow:" if request.url.path == "/robots.txt" else "contenu"
        return httpx.Response(
            200, content=gzip.compress(text.encode()), headers={"Content-Encoding": "gzip"}
        )

    async def exercise():
        async with Telechargeur(settings, transport=httpx.MockTransport(handle)) as client:
            response = await client.obtenir("https://example.com/article", source)
            assert response.text == "contenu"

    asyncio.run(exercise())
