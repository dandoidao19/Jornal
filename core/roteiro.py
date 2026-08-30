import re


def _palavras(texto: str):
    return set(re.findall(r"[a-zà-ú0-9]{3,}", texto.lower()))


def _sobreposicao(a: str, b: str) -> float:
    pa, pb = _palavras(a), _palavras(b)
    if not pb:
        return 0.0
    return len(pa & pb) / len(pb)


def _resumo_complementar(titulo: str, resumo: str) -> str | None:
    """Retorna o resumo apenas se ele acrescentar fatos novos ao título."""
    limpo = _limpar_resumo(resumo)
    if not limpo:
        return None
    sobre = _sobreposicao(titulo, limpo)
    if sobre >= 0.45:
        return None
    return limpo

ABERTURAS = [
    "Olá e seja bem-vindo ao nosso noticiário diário.",
    "Boas notícias de um resumo dos fatos que marcaram o dia.",
    "Começamos mais uma edição do nosso resumo diário.",
    "Seja bem-vindo ao resumo de hoje. Aqui estão os destaques.",
]

ROTACOES = [
    "Seguindo com os destaques do dia,",
    "Outro assunto que merece atenção,",
    "Continuando com o que acontece pelo Brasil e pelo mundo,",
    "Avança agora outro tema acompanhado hoje,",
    "Também entre os destaques,",
]

ABERTURAS_CATEGORIA = {
    "Economia": [
        "Na economia,",
        "No cenário econômico,",
        "Falando em economia,",
    ],
    "Politica": [
        "Na política,",
        "No cenário político,",
        "Falando em política,",
    ],
    "Social": [
        "No campo social,",
        "Nas questões sociais,",
        "Falando de temas sociais,",
    ],
    "Saude": [
        "Na área da saúde,",
        "Falando de saúde,",
    ],
    "Meio ambiente": [
        "Sobre o clima e o meio ambiente,",
        "Falando do meio ambiente,",
    ],
    "Internet": [
        "No mundo digital,",
        "No universo da internet e da tecnologia,",
        "Falando de tecnologia,",
    ],
    "Mundo": [
        "No cenário internacional,",
        "Pelo mundo,",
        "Lá fora,",
    ],
    "Esportes": [
        "Nos esportes,",
        "Pelo mundo do esporte,",
    ],
    "Familia": [
        "Em pautas de família,",
        "Falando de família,",
    ],
    "Geral": [
        "Um assunto que repercutiu hoje,",
        "Outra pauta importante,",
    ],
}

FALA_SEM_RESUMO = [
    "Os detalhes completos estão na reportagem original.",
    "Acompanhe o desdobramento nas próximas edições.",
    "Fique com as informações da reportagem completa.",
    "Saiba todos os detalhes na matéria original.",
]

FECHAMENTOS = [
    "Essa é a informação, com os detalhes na fonte original.",
    "O acompanhamento segue nas próximas edições.",
    "A cobertura completa está no texto original da reportagem.",
    "Esse foi o destaque. Seguimos na sequência.",
]

ENCERRAMENTO = (
    "E por hoje é só. Obrigado por acompanhar. Até a próxima edição, "
    "com os fatos que vão marcar os próximos dias."
)


def _limpar_resumo(resumo: str) -> str:
    texto = re.sub(r"\s+", " ", resumo or "").strip()
    texto = texto.replace("…", "")
    texto = re.sub(r"^[-–—\s]+", "", texto)
    texto = re.sub(r"[-–—]\s*[A-Za-z]+$", "", texto).strip()
    if not texto:
        return ""
    if texto and texto[-1] not in ".!?…":
        texto += "."
    return texto


def _frase_titulo(titulo: str) -> str:
    t = titulo.strip()
    if not t:
        return ""
    if t[-1] not in ".!?…":
        t += "."
    return t


def montar_roteiro(noticia: dict, indice: int = 1, total: int = 1) -> str:
    """Gera a narração de UMA notícia, com variação e sem repetir o resumo cru."""
    categoria = noticia.get("categoria", "Geral") or "Geral"
    titulo = noticia.get("titulo", "").strip()

    abert_cat = ABERTURAS_CATEGORIA.get(categoria, ABERTURAS_CATEGORIA["Geral"])
    abertura = abert_cat[(indice - 1) % len(abert_cat)]

    partes = [abertura, f"{_frase_titulo(titulo)}"]

    complementar = _resumo_complementar(titulo, noticia.get("resumo", ""))
    if complementar:
        partes.append(f"{complementar}")
    else:
        partes.append(FALA_SEM_RESUMO[(indice - 1) % len(FALA_SEM_RESUMO)])

    fechamento = FECHAMENTOS[(indice - 1) % len(FECHAMENTOS)]
    partes.append(fechamento)

    return " ".join(p.strip() for p in partes if p.strip())


def montar_roteiro_completo(noticias: list) -> str:
    """Roteiro completo (abertura + notícias + fechamento) em um único texto."""
    partes = []
    if not noticias:
        return ""
    partes.append(ABERTURAS[0])
    for i, n in enumerate(noticias, start=1):
        partes.append(montar_roteiro(n, i, len(noticias)))
        if i < len(noticias):
            partes.append(ROTACOES[i % len(ROTACOES)])
    partes.append(ENCERRAMENTO)
    return " ".join(partes)