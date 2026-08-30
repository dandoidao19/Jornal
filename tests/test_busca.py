from core.busca import _deduplicar


def _n(titulo, resumo="", categoria="Geral"):
    return {
        "id": titulo[:10],
        "titulo": titulo,
        "resumo": resumo,
        "categoria": categoria,
        "fonte": "Fonte",
        "url": "https://exemplo.com/x",
    }


def test_dedupe_mantem_resumo_maior():
    n1 = _n("Dólar bate recorde hoje", "curto")
    n2 = _n("Dólar bate recorde hoje!!", "versão muito mais completa do resumo da mesma notícia")
    resultado = _deduplicar([n1, n2])
    assert len(resultado) == 1
    assert resultado[0]["resumo"] == n2["resumo"]


def test_dedupe_ignora_acentos_e_pontuacao():
    a = _n("Chuva na capital hoje", "resumo A")
    b = _n("Chuva na capital, hoje!", "resumo B")
    assert len(_deduplicar([a, b])) == 1


def test_dedupe_vazio():
    assert _deduplicar([]) == []


def test_dedupe_ordenado_por_categoria():
    n1 = _n("Notícia economia", "", "Economia")
    n2 = _n("Notícia esportes", "", "Esportes")
    n3 = _n("Notícia geral", "", "Geral")
    resultado = _deduplicar([n3, n1, n2])
    assert resultado[0]["categoria"] == "Economia"
    assert resultado[-1]["categoria"] == "Geral"