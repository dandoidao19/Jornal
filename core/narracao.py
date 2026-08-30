import asyncio
import os

import edge_tts

VOZ = "pt-BR-FranciscaNeural"


async def _gerar_async(texto: str, caminho: str, voz: str = VOZ):
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(caminho)


def gerar_narracao(texto: str, caminho: str, voz: str = VOZ) -> None:
    """Gera um arquivo MP3 de narração com a voz escolhida (grátis, sem chave)."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    asyncio.run(_gerar_async(texto, caminho, voz))