from core.categorias import classificar, normalizar, resumo_curto, categorias_disponiveis


def test_classificar_economia_pela_titulo():
    assert classificar("Dólar fecha em alta e bolsa sobe com juros") == "Economia"


def test_classificar_esportes_pelo_resumo():
    assert classificar("Final emocionante hoje", "furacão faz gol de falta e vence o campeonato") == "Esportes"


def test_classificar_sem_keywords_vira_geral():
    assert classificar("Bela tarde de domingo no parque") == "Geral"


def test_classificar_acentos_ignorados():
    assert classificar("Vacinação avança no SUS") == "Saude"


def test_classificar_internet():
    assert classificar("WhatsApp lança novo recurso de inteligência artificial") == "Internet"


def test_resumo_curto_trunca():
    texto = "palavra " * 100
    curto = resumo_curto(texto, limite=80)
    assert len(curto) <= 81
    assert curto.endswith("…")


def test_resumo_curto_vazio():
    assert resumo_curto("") == ""
    assert resumo_curto(None) == ""


def test_normalizar_titulo():
    assert normalizar("  Dólar cai!!  Hoje ") == "dólar cai hoje"


def test_categorias_contem_geral():
    cats = categorias_disponiveis()
    assert "Geral" in cats
    assert "Economia" in cats