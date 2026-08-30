import re
import unicodedata

# Palavras-chave com pesos: 3 = fortíssima, 2 = forte, 1 = genérica.
# A busca casa palavras inteiras no título (peso x2) e no resumo (peso x1).
CATEGORIAS = {
    "Economia": {
        "economia": 2, "dolar": 3, "pib": 3, "inflacao": 3, "inflacionario": 3,
        "juros": 3, "selic": 3, "ibovespa": 3, "bolsa de valores": 3, "bolsa": 2,
        "cambio": 3, "emprego": 2, "desemprego": 3, "investidor": 2, "acoes": 2,
        "lucro": 2, "receita": 2, "orcamento": 2, "impostos": 2, "fiscal": 2,
        "tarifa": 2, "gasolina": 2, "financas": 2, "banco central": 3, "b3": 3,
        "varejo": 2, "exportacao": 2, "crise economica": 3, "precos": 2,
        "renda": 2, "salario": 2, "aposentadoria": 2, "taxa": 2,
    },
    "Politica": {
        "eleicao": 3, "eleitoral": 3, "votacao": 3, "urna": 3, "voto": 3,
        "candidato": 3, "candidatura": 3, "presidente": 2, "presidencial": 2,
        "governo": 1, "congresso": 3, "senado": 3, "camara": 3, "deputado": 3,
        "senador": 3, "vereador": 3, "stf": 3, "supremo": 2, "ministro": 2,
        "governador": 2, "prefeito": 2, "partido": 2, "bancada": 2, "politica": 1,
        "politico": 2, "projeto de lei": 3, "emenda": 2, "legislativo": 3,
        "impeachment": 3, "medida provisoria": 3, "plenario": 2, "reforma": 2,
        "tse": 3, "cpi": 3, "comissao": 2, "tribunal": 2, "mandato": 3,
        "parlamentar": 3, "golpe": 2, "bolsonaro": 3, "lula": 3, "agenor": 1,
    },
    "Social": {
        "saude": 1, "educacao": 2, "escola": 2, "professor": 2, "violencia": 3,
        "crime": 3, "criminoso": 3, "homicidio": 3, "assassinato": 3,
        "seguranca publica": 3, "policia": 2, "prisao": 2, "roubo": 3,
        "trafico": 3, "faccao": 3, "protesto": 2, "manifestacao": 2, "greve": 2,
        "moradia": 2, "direitos": 2, "pobreza": 3, "fome": 3, "assistencia": 2,
        "denuncia": 2, "acidente": 2, "desabamento": 3, "deslizamento": 3,
        "sequestro": 3, "estupro": 3, "menor": 2, "consumo de drogas": 3,
    },
    "Saude": {
        "hospital": 2, "hospitais": 2, "vacina": 3, "medico": 2, "medicamento": 3,
        "doenca": 3, "cancer": 3, "covid": 3, "dengue": 3, "epidemia": 3,
        "pandemia": 3, "cirurgia": 3, "sus": 3, "saude publica": 3,
        "farmacia": 2, "tratamento": 2, "clinica": 2, "emergencia": 2,
        "alerta": 1, "exame": 2, "obesidade": 3, "ansiedade": 3,
    },
    "Meio ambiente": {
        "clima": 3, "chuva": 3, "chuvas": 3, "tempestade": 3, "temporal": 3,
        "seca": 3, "enchente": 3, "alagamento": 3, "desmatamento": 3,
        "queimadas": 3, "meio ambiente": 3, "temperatura": 3, "meteorologia": 3,
        "frente fria": 3, "onda de calor": 3, "aquecimento": 3, "emissoes": 2,
        "frio": 2, "calor": 2, "previsao do tempo": 3, "floresta": 2,
    },
    "Internet": {
        "internet": 3, "rede social": 3, "whatsapp": 3, "instagram": 3,
        "tiktok": 3, "twitter": 3, "streaming": 3, "inteligencia artificial": 3,
        "ia generativa": 3, "5g": 3, "chip": 3, "hacker": 3, "cibercrime": 3,
        "phishing": 3, "metaverso": 3, "algoritmo": 3, "startup": 2,
        "youtube": 3, "celular": 2, "smartphone": 2, "aplicativo": 2,
        "app": 1, "tecnologia": 2, "digital": 2, "online": 2, "internet das coisas": 3,
    },
    "Mundo": {
        "guerra": 3, "conflito": 3, "internacional": 2, "nacoes unidas": 3,
        "onu": 3, "diplomacia": 3, "embaixador": 2, "global": 2, "eua": 3,
        "estados unidos": 3, "russia": 3, "ucrania": 3, "china": 3, "israel": 3,
        "europa": 2, "uniao europeia": 3, "otan": 3, "nato": 3, "tratado": 3,
        "acordo": 2, "refugiado": 3, "mundo": 1, "paises": 1, "palestina": 3,
        "faixa de gaza": 3, "sancoes": 3,
    },
    "Esportes": {
        "futebol": 3, "campeonato": 3, "copa": 3, "selecao": 2, "time": 2,
        "gol": 3, "partida": 3, "olimpiada": 3, "medalha": 3, "titulo": 2,
        "tenista": 3, "f1": 3, "formula 1": 3, "basquete": 3, "volei": 3,
        "nba": 3, "treinador": 2, "jogador": 2, "torcedor": 2,
    },
    "Familia": {
        "familia": 3, "familiares": 3, "filhos": 3, "parental": 3,
        "maternidade": 3, "paternidade": 3, "gravidez": 3, "bebe": 3,
        "casamento": 3, "casal": 2, "divorcio": 3, "guarda": 2, "crianca": 2,
        "nascer": 2, "opcao": 1, "loas": 3, "bpc": 3, "auxilio": 2,
    },
}

# Ordem usada para desempatar pontuações iguais.
PRIORIDADE = [
    "Economia", "Politica", "Mundo", "Social", "Saude",
    "Meio ambiente", "Internet", "Esportes", "Familia",
]

LIMITE_MINIMO = 2


def _sem_acento(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", t.lower())


def _marcas(texto: str) -> list:
    return [f" {m} " for m in _sem_acento(texto).split()]


def _pontuacao(titulo_norm: str, resumo_norm: str, palavras: dict) -> int:
    score = 0
    for palavra, peso in palavras.items():
        padrao = r"(?<![a-z0-9])" + re.escape(palavra) + r"(?![a-z0-9])"
        if re.search(padrao, titulo_norm):
            score += peso * 2
        if resumo_norm and re.search(padrao, resumo_norm):
            score += peso
    return score


def classificar(titulo: str, resumo: str = "") -> str:
    """Classifica pela soma de pesos; categoria só é atribuída acima do limite."""
    titulo_norm = _sem_acento(titulo)
    resumo_norm = _sem_acento(resumo)
    melhor_cat = "Geral"
    melhor_pont = 0
    for cat, palavras in CATEGORIAS.items():
        pont = _pontuacao(titulo_norm, resumo_norm, palavras)
        if pont > melhor_pont:
            melhor_pont = pont
            melhor_cat = cat
        elif pont == melhor_pont and pont > 0:
            if PRIORIDADE.index(cat) < PRIORIDADE.index(melhor_cat):
                melhor_cat = cat
    if melhor_pont < LIMITE_MINIMO:
        return "Geral"
    return melhor_cat


def categorias_disponiveis() -> list:
    return list(CATEGORIAS.keys()) + ["Geral"]


def resumo_curto(texto: str, limite: int = 200) -> str:
    if not texto:
        return ""
    limpo = re.sub(r"\s+", " ", texto).strip()
    if len(limpo) <= limite:
        return limpo
    corte = limpo[:limite]
    ultimo = corte.rfind(" ")
    return corte[:ultimo] + "…"


def normalizar(titulo: str) -> str:
    t = titulo.lower()
    t = re.sub(r"[^a-z0-9ãõáéíóúâêôçà ]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:80]