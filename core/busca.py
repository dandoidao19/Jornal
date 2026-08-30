import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import feedparser
import requests

from .categorias import classificar, normalizar, resumo_curto
from .imagens import extrair_imagem

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_RSS_BR = "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419"

# Feeds brasileiros com URLs diretas (o roteirista precisa ler o artigo completo).
FEEDS_BR = {
    "G1": "https://g1.globo.com/rss/g1/",
    "UOL": "https://rss.uol.com.br/feed/noticias.xml",
    "BBC Brasil": "https://www.bbc.com/portuguese/index.xml",
    "Agência Brasil": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
}

# Feeds internacionais com impacto mundial (guerra, doenças, IA, clima).
FEEDS_INT = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
}


def _dominio(url: str) -> str:
    try:
        host = urlparse(url).netloc
        return host.replace("www.", "")
    except Exception:
        return ""


def _titulo_limpo(titulo: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", titulo)).strip()


def _id_unico(url: str, titulo: str) -> str:
    origem = f"{url}|{titulo}".encode("utf-8")
    return hashlib.md5(origem).hexdigest()[:10]


def _resumo_da_pagina(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return ""
        texto = r.text
        for p in [
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        ]:
            m = re.search(p, texto, re.I | re.S)
            if m:
                return html.unescape(m.group(1)).strip()
    except Exception:
        pass
    return ""


def _gdelt(data_str: str, limite: int = 25) -> list:
    """Notícias de uma data específica via GDELT (sem chave, URLs diretas)."""
    params = {
        "query": "brasil OR brazil OR mundo OR economia OR politica",
        "mode": "artlist",
        "format": "json",
        "startdatetime": data_str + "000000",
        "enddatetime": data_str + "235959",
        "maxrecords": str(limite),
        "sort": "datedesc",
    }
    try:
        r = requests.get(GDELT_URL, params=params, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            dados = r.json()
            saida = []
            for a in dados.get("articles", []):
                url = a.get("url", "")
                titulo = _titulo_limpo(a.get("title", ""))
                if not url or not titulo:
                    continue
                resumo = _resumo_da_pagina(url)
                imagem = extrair_imagem(None, url, gdelt_social=a.get("socialimage"))
                saida.append(
                    {
                        "id": _id_unico(url, titulo),
                        "titulo": titulo,
                        "resumo": resumo_curto(resumo),
                        "fonte": _dominio(url),
                        "url": url,
                        "data": data_str,
                        "categoria": classificar(titulo, resumo),
                        "imagem": imagem,
                    }
                )
            return saida
    except Exception:
        pass
    return []


def _fetch_feed(url: str):
    """Busca feed com timeout para não travar a interface."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.content:
            return feedparser.parse(r.content)
    except Exception:
        pass
    try:
        return feedparser.parse(url)
    except Exception:
        return feedparser.parse("")


def _feed(feed_url: str, data_str: str, fonte: str, limite: int = 8) -> list:
    saida = []
    try:
        feed = _fetch_feed(feed_url)
        dia = f"{data_str[6:]}-{data_str[4:6]}-{data_str[:4]}"
        for e in feed.entries[: limite * 3]:
            link = e.get("link", "")
            titulo = _titulo_limpo(e.get("title", ""))
            if not link or not titulo:
                continue
            resumo = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary", "")))
            resumo = re.sub(r"\s+", " ", resumo).strip()
            publicada = e.get("published_parsed")
            if publicada:
                try:
                    data_entrada = f"{publicada.tm_mday:02d}-{publicada.tm_mon:02d}-{publicada.tm_year}"
                    if data_entrada != dia:
                        continue
                except Exception:
                    pass
            imagem = extrair_imagem(e, link)
            saida.append(
                {
                    "id": _id_unico(link, titulo),
                    "titulo": titulo,
                    "resumo": resumo_curto(resumo),
                    "fonte": fonte,
                    "url": link,
                    "data": dia,
                    "categoria": classificar(titulo, resumo),
                    "imagem": imagem,
                }
            )
            if len(saida) >= limite:
                break
    except Exception:
        pass
    return saida


def _google_rss(data_str: str, limite: int = 10) -> list:
    saida = []
    try:
        feed = _fetch_feed(GOOGLE_RSS_BR)
        dia = f"{data_str[6:]}-{data_str[4:6]}-{data_str[:4]}"
        for e in feed.entries:
            link = e.get("link", "")
            titulo = _titulo_limpo(e.get("title", ""))
            if not link or not titulo:
                continue
            resumo = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary", "")))
            imagem = extrair_imagem(e, link)
            saida.append(
                {
                    "id": _id_unico(link, titulo),
                    "titulo": titulo,
                    "resumo": resumo_curto(resumo),
                    "fonte": "Google News",
                    "url": link,
                    "data": dia,
                    "categoria": classificar(titulo, resumo),
                    "imagem": imagem,
                }
            )
            if len(saida) >= limite:
                break
    except Exception:
        pass
    return saida


def _feed_internacional(feed_url: str, fonte: str, data_str: str, limite: int = 3) -> list:
    """Feed em inglês: traduz prévia para pt-BR antes de classificar/exibir."""
    from .traducao import traduzir_noticia

    saida = []
    try:
        feed = _fetch_feed(feed_url)
        # coleta bruta
        brutos = []
        for e in feed.entries[:20]:
            link = e.get("link", "")
            titulo_en = _titulo_limpo(e.get("title", ""))
            if not link or not titulo_en:
                continue
            resumo_en = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary", "")))
            resumo_en = re.sub(r"\s+", " ", resumo_en).strip()
            imagem = extrair_imagem(e, link)
            brutos.append((link, titulo_en, resumo_en, imagem))
            if len(brutos) >= limite:
                break
        # traduz em paralelo (3 workers)
        def _traduz(item):
            link, titulo_en, resumo_en, imagem = item
            try:
                titulo_pt, resumo_pt = traduzir_noticia(titulo_en, resumo_en)
            except Exception:
                titulo_pt, resumo_pt = titulo_en, resumo_en
            titulo_pt = titulo_pt or titulo_en
            resumo_pt = resumo_pt or resumo_en
            return {
                "id": _id_unico(link, titulo_pt),
                "titulo": titulo_pt,
                "titulo_original": titulo_en,
                "resumo": resumo_curto(resumo_pt),
                "resumo_original": resumo_en,
                "fonte": fonte,
                "url": link,
                "data": f"{data_str[6:]}-{data_str[4:6]}-{data_str[:4]}",
                "categoria": classificar(titulo_pt, resumo_pt),
                "imagem": imagem,
                "internacional": True,
            }

        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(_traduz, b) for b in brutos]
            for f in as_completed(futs):
                try:
                    saida.append(f.result())
                except Exception:
                    pass
    except Exception:
        pass
    return saida


def _gdelt_internacional(data_str: str, limite: int = 3) -> list:
    """GDELT com foco em temas de impacto mundial (guerra, doenças, IA...)."""
    from .traducao import traduzir_noticia

    params = {
        "query": 'war OR conflict OR disease OR pandemic OR "artificial intelligence" OR climate',
        "mode": "artlist",
        "format": "json",
        "startdatetime": data_str + "000000",
        "enddatetime": data_str + "235959",
        "maxrecords": str(limite),
        "sort": "datedesc",
    }
    try:
        r = requests.get(GDELT_URL, params=params, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            dados = r.json()
            saida = []
            for a in dados.get("articles", []):
                url = a.get("url", "")
                titulo_en = _titulo_limpo(a.get("title", ""))
                if not url or not titulo_en:
                    continue
                # ignora se já for BR
                if a.get("sourcecountry") == "Brazil":
                    continue
                try:
                    titulo_pt, _ = traduzir_noticia(titulo_en, "")
                except Exception:
                    titulo_pt = titulo_en
                titulo_pt = titulo_pt or titulo_en
                resumo = _resumo_da_pagina(url)
                if resumo:
                    try:
                        _, resumo_pt = traduzir_noticia(titulo_en, resumo)
                        resumo = resumo_pt or resumo
                    except Exception:
                        pass
                imagem = extrair_imagem(None, url, gdelt_social=a.get("socialimage"))
                saida.append(
                    {
                        "id": _id_unico(url, titulo_pt),
                        "titulo": titulo_pt,
                        "titulo_original": titulo_en,
                        "resumo": resumo_curto(resumo),
                        "fonte": _dominio(url),
                        "url": url,
                        "data": data_str,
                        "categoria": classificar(titulo_pt, resumo),
                        "imagem": imagem,
                        "internacional": True,
                    }
                )
            return saida
    except Exception:
        pass
    return []


def buscar_noticias(data) -> list:
    """Busca notícias reais para uma data. GDELT + feeds BR + Google News + internacionais traduzidos."""
    data_str = data.strftime("%Y%m%d")
    noticias = _gdelt(data_str)
    for nome, url_feed in FEEDS_BR.items():
        noticias += _feed(url_feed, data_str, nome)
    noticias += _google_rss(data_str)
    # internacionais (prévia já traduzida de forma natural)
    for nome, url_feed in FEEDS_INT.items():
        noticias += _feed_internacional(url_feed, nome, data_str)
    noticias += _gdelt_internacional(data_str)

    vistos = {}
    for n in noticias:
        chave = normalizar(n["titulo"])
        if not chave:
            continue
        if chave in vistos:
            existente = vistos[chave]
            if len(n["resumo"]) > len(existente["resumo"]):
                vistos[chave] = n
        else:
            vistos[chave] = n

    ordenadas = sorted(vistos.values(), key=lambda n: n["categoria"])
    return ordenadas