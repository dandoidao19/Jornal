import hashlib
import json
import os
import re

import requests
import trafilatura

DIR_CONFIG = os.path.join(os.path.dirname(__file__), "..", "data")


def _limpar_saida(texto: str) -> str:
    """Remove bloco de raciocínio, emojis e espaços extras do texto da IA."""
    t = (texto or "").strip()
    t = re.sub(r"```[a-z]*", "", t)
    # remove bloco "thinking" (raciocínio vazado pelo modelo)
    t = re.sub(r"(?is)thinking[\s\S]*?/thinking", "", t)
    # remove emojis e símbolos
    t = re.sub(
        r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2705\U0001F1E6-\U0001F1FF]", "", t
    )
    # colapsa múltiplos espaços e quebras em uma frase contínua
    t = re.sub(r"\s+", " ", t).strip()
    # remove rodapés repetidos típicos
    t = re.sub(r"(?i)\s*cr[eé]ditos?:?\s*$", "", t).strip()
    return t


def carregar_chaves() -> dict:
    """Lê chaves de API de variáveis de ambiente ou de data/config.json."""
    chaves = {
        "gemini": os.environ.get("GEMINI_API_KEY", ""),
        "groq": os.environ.get("GROQ_API_KEY", ""),
    }
    try:
        cfg_path = os.path.join(DIR_CONFIG, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            chaves["gemini"] = chaves["gemini"] or cfg.get("gemini_api_key", "")
            chaves["groq"] = chaves["groq"] or cfg.get("groq_api_key", "")
    except Exception:
        pass
    return chaves


def disponivel() -> bool:
    chaves = carregar_chaves()
    return bool(chaves["gemini"] or chaves["groq"])


def _cache_artigo(url: str) -> str | None:
    """Cacheia o texto bruto do artigo em data/artigos/<hash>.txt."""
    try:
        pasta = os.path.join(DIR_CONFIG, "artigos")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, hashlib.md5(url.encode()).hexdigest() + ".txt")
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        pass
    return None


def _salvar_artigo(url: str, texto: str):
    try:
        pasta = os.path.join(DIR_CONFIG, "artigos")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, hashlib.md5(url.encode()).hexdigest() + ".txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
    except Exception:
        pass


def _resolver_url(url: str) -> str:
    """Segue redirects (ex.: links do Google News) até a URL final real."""
    try:
        r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
        final = r.url or url
        if final and "google.com/rss" not in final:
            return final
        return url
    except Exception:
        return url


def extrair_artigo(url: str) -> str:
    """Baixa e extrai o texto principal do artigo (com cache em disco)."""
    url_real = _resolver_url(url)
    cacheado = _cache_artigo(url_real)
    if cacheado:
        return cacheado
    try:
        html = trafilatura.fetch_url(url_real)
        texto = trafilatura.extract(html) if html else None
    except Exception:
        texto = None
    if not texto or len(texto.strip()) < 100:
        # fallback: baixar com requests e tentar extrair
        try:
            r = requests.get(url_real, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            texto = trafilatura.extract(r.text) if r.status_code == 200 else None
        except Exception:
            texto = None
    texto = (texto or "").strip()
    if len(texto) >= 100:
        _salvar_artigo(url_real, texto)
    return texto


def _chamar_gemini(prompt: str, chave: str, modelo: str = "gemini-2.0-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    r = requests.post(
        url,
        params={"key": chave},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    dados = r.json()
    return _limpar_saida(dados["candidates"][0]["content"]["parts"][0]["text"])


def _chamar_groq(prompt: str, chave: str, modelo: str = "qwen/qwen3.6-27b") -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {chave}"},
        json={
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=60,
    )
    r.raise_for_status()
    return _limpar_saida(r.json()["choices"][0]["message"]["content"])


def _prompt(noticia: dict, artigo: str, indice: int, total: int) -> str:
    resumo = (noticia.get("resumo") or "").strip()
    if artigo:
        corpo = "ARTIGO COMPLETO DA FONTE (é a fonte oficial de informação):\n" + artigo[:6000]
    else:
        corpo = (
            "O texto completo não pôde ser acessado. Use APENAS o resumo abaixo. "
            "Resumo disponível: " + (resumo or "não informado.")
        )
    return f"""
Você é o editor-chefe de um noticiário diário em português do Brasil.
Sua tarefa: escrever a narração oral de UMA notícia com 3 a 4 frases curtas.

REGRAS OBRIGATÓRIAS:
- Leia TODO o artigo e resuma SOMENTE as partes importantes para o público entender o essencial.
- Use LINGUAGEM SIMPLES, oral e jornalística, sem jargão técnico.
- NÃO copie frases do artigo: escreva com suas palavras.
- NÃO repita o título palavra por palavra.
- Explique o contexto em 1 frase e o impacto/desdobramento se houver.
- Mencione a fonte de forma natural e variada (não use sempre o mesmo formato).
- NÃO invente fatos, números ou citações ausentes no texto.
- NÃO use listas, travessões, markdown ou rótulos. Responda apenas o texto final.
- Varie a abertura para não soar repetitivo entre notícias.

TÍTULO: {noticia.get('titulo', '')}
CATEGORIA: {noticia.get('categoria', 'Geral')}
FONTE: {noticia.get('fonte', '')}
POSIÇÃO NA EDIÇÃO: {indice} de {total}

{corpo}
"""


def montar_roteiro_ia(noticia: dict, indice: int = 1, total: int = 1) -> str | None:
    """Gera narração lendo o artigo completo. Retorna None se indisponível."""
    chaves = carregar_chaves()
    url = noticia.get("url", "")
    artigo = extrair_artigo(url) if url else ""
    prompt = _prompt(noticia, artigo, indice, total)
    if chaves["gemini"]:
        for modelo in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-8b"]:
            try:
                return _chamar_gemini(prompt, chaves["gemini"], modelo)
            except Exception:
                continue
    if chaves["groq"]:
        for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]:
            try:
                return _chamar_groq(prompt, chaves["groq"], modelo)
            except Exception:
                continue
    return None