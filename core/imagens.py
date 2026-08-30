import html
import re

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
}


def _extrair_meta_og_imagem(html_text: str) -> str | None:
    for p in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]:
        m = re.search(p, html_text, re.I | re.S)
        if m:
            url = html.unescape(m.group(1)).strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http"):
                return url
    return None


def _imagem_do_feed(entry: dict, preferencia: str = "content") -> str | None:
    if preferencia == "content":
        for chave in ("media_content",):
            val = entry.get(chave)
            if isinstance(val, list) and val:
                for v in reversed(val):
                    u = v.get("url") or v.get("href")
                    if u and u.startswith("http"):
                        return u
        return None
    else:
        for chave in ("media_thumbnail",):
            val = entry.get(chave)
            if isinstance(val, list) and val:
                # pega a maior
                best = None
                best_w = 0
                for v in val:
                    u = v.get("url") or v.get("href")
                    if not u or not u.startswith("http"):
                        continue
                    try:
                        w = int(v.get("width") or 0)
                    except Exception:
                        w = 0
                    if w > best_w:
                        best_w = w
                        best = u
                if best:
                    return best
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and link.get("type", "").startswith("image/"):
                u = link.get("href")
                if u:
                    return u
        enc = entry.get("enclosures")
        if isinstance(enc, list) and enc:
            u = enc[0].get("href") or enc[0].get("url")
            if u and u.startswith("http"):
                return u
        return None


def extrair_imagem(entry: dict | None, url: str, gdelt_social: str | None = None) -> str | None:
    """Alta qualidade sem travar: media_content alta > og:image (se thumb) > GDELT > thumb."""
    # 1) Tenta media_content (normalmente já é alta, ex: 800x450)
    if entry is not None:
        mc = _imagem_do_feed(entry, preferencia="content")
        if mc:
            return mc

    # 2) Se não tem media_content (caso BBC: só thumbnail 240px), busca og:image de alta
    if "news.google.com" not in url:
        try:
            r = requests.get(url, headers=HEADERS, timeout=6)
            if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                og = _extrair_meta_og_imagem(r.text)
                if og:
                    return og
        except Exception:
            pass

    # 3) GDELT socialimage
    if gdelt_social and gdelt_social.startswith("http"):
        return gdelt_social

    # 4) thumbnail como último recurso
    if entry is not None:
        thumb = _imagem_do_feed(entry, preferencia="thumb")
        if thumb:
            return thumb

    return None
