import json
import os

import requests

DIR_CONFIG = os.path.join(os.path.dirname(__file__), "..", "data")


def _carregar_chaves() -> dict:
    chaves = {
        "groq": os.environ.get("GROQ_API_KEY", ""),
        "gemini": os.environ.get("GEMINI_API_KEY", ""),
    }
    try:
        cfg_path = os.path.join(DIR_CONFIG, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            chaves["groq"] = chaves["groq"] or cfg.get("groq_api_key", "")
            chaves["gemini"] = chaves["gemini"] or cfg.get("gemini_api_key", "")
    except Exception:
        pass
    return chaves


def traduzir_para_pt(texto: str) -> str | None:
    """Tradução natural para pt-BR via Groq/Gemini. Retorna None se falhar."""
    if not texto or not texto.strip():
        return texto
    chaves = _carregar_chaves()
    prompt = (
        "Traduza o texto abaixo para português do Brasil de forma natural, fluida e jornalística. "
        "Mantenha nomes próprios, números e fatos. Não adicione explicações, só a tradução:\n\n"
        + texto.strip()
    )
    # Groq primeiro (rapido e estável)
    if chaves["groq"]:
        for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {chaves['groq']}"},
                    json={
                        "model": modelo,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                    timeout=12,
                )
                r.raise_for_status()
                out = r.json()["choices"][0]["message"]["content"].strip()
                # limpar vazamento de pensamento
                import re

                out = re.sub(r"(?is)thinking[\s\S]*?/thinking", "", out).strip()
                out = re.sub(r"\s+", " ", out).strip()
                if out:
                    return out
            except Exception:
                continue
    if chaves["gemini"]:
        for modelo in ["gemini-2.0-flash", "gemini-2.0-flash-lite"]:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                    params={"key": chaves["gemini"]},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=12,
                )
                r.raise_for_status()
                out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                import re

                out = re.sub(r"(?is)thinking[\s\S]*?/thinking", "", out).strip()
                out = re.sub(r"\s+", " ", out).strip()
                if out:
                    return out
            except Exception:
                continue
    return None


def traduzir_noticia(titulo: str, resumo: str) -> tuple[str, str]:
    """Traduz título e resumo em uma única chamada quando possível."""
    combinado = f"TÍTULO: {titulo}\nRESUMO: {resumo}" if resumo else f"TÍTULO: {titulo}"
    prompt = (
        "Você é tradutor jornalístico. Traduza TÍTULO e RESUMO abaixo para português do Brasil "
        "de forma natural e fluida. Responda EXATAMENTE neste formato, sem comentários:\n"
        "TÍTULO: <tradução do título>\n"
        "RESUMO: <tradução do resumo>\n\n"
        + combinado
    )
    chaves = _carregar_chaves()
    if chaves["groq"]:
        for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {chaves['groq']}"},
                    json={
                        "model": modelo,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                    timeout=15,
                )
                r.raise_for_status()
                out = r.json()["choices"][0]["message"]["content"].strip()
                import re

                out = re.sub(r"(?is)thinking[\s\S]*?/thinking", "", out).strip()
                # parse
                t_match = re.search(r"T[IÍ]TULO\s*:\s*(.+)", out, re.I)
                r_match = re.search(r"RESUMO\s*:\s*(.+)", out, re.I | re.S)
                t_trad = t_match.group(1).strip() if t_match else None
                r_trad = r_match.group(1).strip() if r_match else None
                if t_trad:
                    # limpar possível "RESUMO:" que vazou para dentro do título
                    t_trad = re.split(r"\bRESUMO\s*:", t_trad, flags=re.I)[0].strip()
                    r_trad = r_trad or resumo
                    return t_trad, r_trad
            except Exception:
                continue
    # fallback: traduzir separadamente
    t2 = traduzir_para_pt(titulo)
    r2 = traduzir_para_pt(resumo) if resumo else resumo
    return t2 or titulo, r2 or resumo
