from core.roteiro import montar_roteiro, montar_roteiro_completo


def _noticia(titulo="Chuva forte causa alagamentos na capital", resumo=None, categoria="Meio ambiente", fonte="G1"):
    return {
        "titulo": titulo,
        "resumo": resumo,
        "categoria": categoria,
        "fonte": fonte,
    }


def test_roteiro_contem_titulo():
    texto = montar_roteiro(_noticia())
    assert "Chuva forte causa alagamentos na capital" in texto


def test_roteiro_usando_resumo_complementar():
    n = _noticia(resumo="Defesa civil orienta moradores a evitarem áreas de risco nesta noite.")
    texto = montar_roteiro(n)
    assert "Defesa civil orienta moradores" in texto


def test_roteiro_sem_resumo_fala_completo():
    n = _noticia(resumo="")
    texto = montar_roteiro(n)
    assert "reportagem original" in texto or "detalhes" in texto


def test_roteiro_variacao_entre_noticias():
    a = montar_roteiro(_noticia("Primeira manchete do dia."), indice=1, total=2)
    b = montar_roteiro(_noticia("Segunda manchete do dia."), indice=2, total=2)
    assert a != b


def test_roteiro_completo_abre_e_fecha():
    noticias = [
        _noticia("Notícia um sobre economia.", categoria="Economia"),
        _noticia("Notícia dois sobre saúde.", categoria="Saude"),
    ]
    texto = montar_roteiro_completo(noticias)
    assert texto.startswith("Olá") or "bem-vindo" in texto.lower()
    assert "Até a próxima edição" in texto


def test_roteiro_completo_vazio():
    assert montar_roteiro_completo([]) == ""