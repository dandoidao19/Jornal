import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import streamlit as st

from core import __version__
from core.busca import buscar_noticias
from core.categorias import categorias_disponiveis
from core.narracao import gerar_narracao
from core.roteiro import montar_roteiro, montar_roteiro_completo
from core.roteiro_ia import disponivel, montar_roteiro_ia
from core.video import montar_video

st.set_page_config(page_title="JornalDiário — Protótipo", layout="wide")

# CSS responsivo: apenas em telas <=768px (smartphone). No PC (>768px) a interface não muda.
st.markdown(
    """
<style>
@media (max-width: 768px) {
  /* Empilha colunas (4 colunas → 1 por linha) */
  [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.6rem !important; }
  /* Botões com área de toque maior (48px mínimo) */
  .stButton > button { width: 100% !important; padding: 0.95rem 1rem !important; font-size: 1.06rem !important; min-height: 48px !important; border-radius: 12px !important; }
  .stDownloadButton > button { width: 100% !important; min-height: 48px !important; }
  /* Imagens ocupam largura total */
  [data-testid="stImage"] img { width: 100% !important; max-width: 100% !important; height: auto !important; }
  [data-testid="stImage"] { width: 100% !important; }
  /* Checkboxes e radios com área maior */
  [data-testid="stCheckbox"] label, [data-testid="stRadio"] label { font-size: 1.06rem !important; padding: 0.45rem 0 !important; }
  [data-testid="stCheckbox"] input { transform: scale(1.25); }
  /* Text areas legíveis */
  .stTextArea textarea { font-size: 1.02rem !important; line-height: 1.55 !important; }
  /* Título e cabeçalhos compactos */
  h1 { font-size: 1.55rem !important; line-height: 1.2 !important; }
  h2, h3 { font-size: 1.25rem !important; }
  /* Date input e select ocupam largura total */
  [data-testid="stDateInput"], [data-testid="stSelectbox"] { width: 100% !important; }
  /* Áudio player com toque */
  [data-testid="stAudio"] { width: 100% !important; }
  /* Versão sempre visível mesmo com sidebar fechada */
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { font-size: 0.88rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

VOZ_PADRAO = "pt-BR-FranciscaNeural"
VOZES_DISPONIVEIS = [
    "pt-BR-FranciscaNeural",
    "pt-BR-AntonioNeural",
    "pt-BR-BrendaNeural",
]
DIR_DADOS = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DIR_DADOS, exist_ok=True)


def sessao(chave, valor):
    if chave not in st.session_state:
        st.session_state[chave] = valor
    return st.session_state[chave]


@st.cache_data(ttl=3600, show_spinner=False)
def _buscar_cacheadas(data) -> list:
    """Busca notícias com cache de 1h por data (evita refazer toda a rede)."""
    return buscar_noticias(data)


sessao("etapa", 1)
sessao("data", date.today())
sessao("noticias", [])
sessao("voz", VOZ_PADRAO)

st.title("📰 JornalDiário — Jornal eletrônico diário")
st.caption(f"v{__version__} • Vídeo com imagem de fundo + trilha sonora · roteirista lê o artigo completo e resume em linguagem simples")
if disponivel():
    st.sidebar.success("🤖 Roteirista por IA ativo")
else:
    st.sidebar.warning("Roteirista por IA inativo. Adicione chaves em data/config.json.")

st.sidebar.divider()
st.sidebar.subheader("🎙️ Narração")
voz_nome = st.sidebar.selectbox(
    "Voz (TTS grátis)",
    VOZES_DISPONIVEIS,
    index=VOZES_DISPONIVEIS.index(st.session_state.voz)
    if st.session_state.voz in VOZES_DISPONIVEIS
    else 0,
)
st.session_state.voz = voz_nome
st.sidebar.caption("francisca: feminina · antonio: masculina · brenda: feminina")

st.sidebar.divider()
st.sidebar.subheader("🎵 Trilha sonora")
modo_imagem = st.sidebar.radio(
    "Fundo do vídeo",
    ["Imagem real da notícia (sem texto)", "Card com título (fallback)"],
    index=0,
)
st.session_state["modo_imagem"] = "imagem" if modo_imagem.startswith("Imagem") else "card"
musica_file = st.sidebar.file_uploader("Trilha de fundo (MP3/WAV)", type=["mp3", "wav", "m4a"])
if musica_file is not None:
    musica_path = os.path.join(DIR_DADOS, "_trilha_upload" + os.path.splitext(musica_file.name)[1])
    with open(musica_path, "wb") as f:
        f.write(musica_file.getbuffer())
    st.session_state["musica_path"] = musica_path
    st.sidebar.audio(musica_file)
    st.sidebar.caption(f"Trilha carregada: {musica_file.name}")
else:
    st.session_state.setdefault("musica_path", None)
volume_musica = st.sidebar.slider("Volume da trilha", 0.0, 0.3, 0.12, 0.02)
st.session_state["volume_musica"] = volume_musica

aba = st.sidebar.radio(
    "Etapas",
    ["1 · Buscar notícias", "2 · Selecionar", "3 · Revisar roteiro e narração", "4 · Vídeo final"],
    index=st.session_state.etapa - 1,
)

st.session_state.etapa = {"1": 1, "2": 2, "3": 3, "4": 4}.get(aba[0], 1)

st.sidebar.divider()
st.sidebar.caption(f"JornalDiário v{__version__} • grátis • código em github.com/dandoidao19/Jornal")
st.sidebar.caption("Atualizações versionadas a cada alteração.")


# ---------------------------------------------------------------- ETAPA 1
if st.session_state.etapa == 1:
    st.header("📅 Etapa 1 — Escolha a data e busque as notícias")
    st.caption("As notícias são buscadas de forma real, sem custo, a partir da data escolhida.")

    col1, col2 = st.columns([2, 1])
    with col1:
        data_escolhida = st.date_input(
            "Data das notícias",
            value=st.session_state.data,
            min_value=date(2023, 1, 1),
            max_value=date.today(),
        )
    with col2:
        st.write("")
        st.write("")
        buscar = st.button("🔎 Buscar notícias", type="primary", use_container_width=True)

    if buscar:
        st.session_state.data = data_escolhida
        with st.spinner("Buscando nas fontes (GDELT + feeds BR + internacionais com tradução)..."):
            noticias = _buscar_cacheadas(data_escolhida)
            st.session_state["_cache_invalida"] = None  # marca que a busca usou cache
        if not noticias:
            st.warning("Nenhuma notícia encontrada para essa data. Tente uma data recente.")
        else:
            st.session_state.noticias = noticias
            st.session_state.etapa = 2
            st.rerun()

    if st.session_state.noticias:
        st.info(f"Já há {len(st.session_state.noticias)} notícias carregadas de {st.session_state.data}.")
        if st.button("Ir para seleção →"):
            st.session_state.etapa = 2
            st.rerun()


# ---------------------------------------------------------------- ETAPA 2
elif st.session_state.etapa == 2:
    st.header("✅ Etapa 2 — Selecione as notícias para o vídeo")
    st.caption("Marque as notícias que entrarão no vídeo. Cada uma mostra título e um resumo breve.")

    noticias = st.session_state.noticias
    if not noticias:
        st.warning("Nenhuma notícia carregada. Volte à etapa 1.")
        if st.button("← Voltar"):
            st.session_state.etapa = 1
            st.rerun()
        st.stop()

    cat_opcoes = categorias_disponiveis()
    for i, n in enumerate(noticias):
        chave = f"sel_{n['id']}"
        selecionada = st.checkbox(f"**{n['titulo']}**", key=chave,
                                  value=sessao(f"sel_valor_{n['id']}", False))
        st.session_state[f"sel_valor_{n['id']}"] = selecionada
        # selo internacional / imagem
        selos = []
        if n.get("internacional"):
            selos.append("🌍 Internacional")
        if n.get("imagem"):
            selos.append("🖼️ Imagem")
        if selos:
            st.caption(" ".join(selos))
        # prévia da imagem real (sem texto)
        if n.get("imagem"):
            try:
                st.image(n["imagem"], width=420, caption="Imagem da matéria (fundo do vídeo)")
            except Exception:
                pass
        cols = st.columns(4)
        cat_atual = n.get("categoria", "Geral")
        cat_idx = cat_opcoes.index(cat_atual) if cat_atual in cat_opcoes else cat_opcoes.index("Geral")
        n["categoria"] = cols[0].selectbox(
            "Categoria",
            cat_opcoes,
            index=cat_idx,
            key=f"cat_{n['id']}",
            label_visibility="collapsed",
        )
        cols[1].markdown(f"📰 **Fonte:** {n['fonte']}")
        cols[2].markdown(f"📅 **Data:** {n['data']}")
        cols[3].markdown(f"🔗 [Abrir matéria]({n['url']})")
        resumo = n.get("resumo") or "Resumo indisponível."
        st.caption(f"📄 {resumo}")
        st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Voltar"):
            st.session_state.etapa = 1
            st.rerun()
    with col2:
        selecionadas = [
            n for n in noticias
            if st.session_state.get(f"sel_valor_{n['id']}", False)
        ]
        total = len(selecionadas)
        label = f"▶ Gerar roteiro e narração ({total})" if total else "▶ Gerar roteiro e narração"
        gerar = st.button(label, type="primary", use_container_width=True,
                          disabled=total == 0)
        if gerar:
            sessao_id = uuid.uuid4().hex[:8]
            audio_dir = os.path.join(DIR_DADOS, f"audio_{sessao_id}")
            os.makedirs(audio_dir, exist_ok=True)
            st.session_state["audio_dir"] = audio_dir
            st.session_state["selecionadas"] = selecionadas
            voz = st.session_state.voz
            total_n = len(selecionadas)
            progresso = st.progress(0.0, text="Gerando roteiro e narração...")
            concluidos = 0

            def _processar(item):
                j, n = item
                texto_ia = montar_roteiro_ia(n, j, total_n)
                texto = texto_ia if texto_ia else montar_roteiro(n, j, total_n)
                n["roteiro"] = texto
                n["roteiro_fonte"] = "IA" if texto_ia else "Template"
                caminho = os.path.join(audio_dir, f"{n['id']}.mp3")
                try:
                    gerar_narracao(texto, caminho, voz)
                    n["audio_ok"] = caminho
                    n["audio_erro"] = None
                except Exception as e:
                    n["audio_ok"] = None
                    n["audio_erro"] = str(e)
                return n

            with ThreadPoolExecutor(max_workers=min(3, total_n)) as ex:
                futs = [ex.submit(_processar, (j, n))
                        for j, n in enumerate(selecionadas, start=1)]
                for _ in as_completed(futs):
                    concluidos += 1
                    progresso.progress(concluidos / total_n,
                                       text=f"Notícia {concluidos}/{total_n}")
            progresso.empty()
            st.session_state.etapa = 3
            st.rerun()


# ---------------------------------------------------------------- ETAPA 3
elif st.session_state.etapa == 3:
    st.header("🎙️ Etapa 3 — Revisão individual do roteiro e da narração")
    st.caption("Cada notícia aparece separada. Edite o texto se quiser, ouça a narração e aprove.")

    selecionadas = st.session_state.get("selecionadas", [])
    if not selecionadas:
        st.warning("Nenhuma notícia selecionada.")
        st.stop()

    if st.button("👁 Ver roteiro completo (abertura + todas as notícias)"):
        completo = montar_roteiro_completo(selecionadas)
        st.text_area(
            "Roteiro completo da edição",
            value=completo,
            height=260,
            key="roteiro_completo_v3",
        )
        st.caption("Use o texto acima como base para revisão ou para exportar antes de gerar as narrações.")
    st.markdown("---")

    aprovadas = 0
    for i, n in enumerate(selecionadas, start=1):
        chave_aprov = f"aprov_{n['id']}"
        sessao(chave_aprov, True)
        texto_editado = st.text_area(
            f"📝 Texto da narração — notícia {i}/{len(selecionadas)}",
            value=n.get("roteiro", ""),
            height=120,
            key=f"roteiro_{n['id']}_{n.get('audio_ok', '')}",
        )
        n["roteiro"] = texto_editado

        origem = "🤖 IA" if n.get("roteiro_fonte") == "IA" else "📝 Template"
        st.caption(f"Origem do roteiro: {origem}")

        cols = st.columns(3)
        caminho = n.get("audio_ok")
        if caminho and os.path.exists(caminho):
            with open(caminho, "rb") as f:
                audio_bytes = f.read()
            cols[0].audio(audio_bytes, format="audio/mp3")
        else:
            cols[0].warning("Narração ainda não gerada para esta notícia.")
        aprovar = cols[1].checkbox(
            "✅ Aprovar para o vídeo", key=chave_aprov,
            value=sessao(chave_aprov, True),
        )
        if aprovar:
            aprovadas += 1
        regravar = cols[2].button("🔊 Regravar narração", key=f"rec_{n['id']}")
        if regravar:
            caminho2 = os.path.join(st.session_state.audio_dir, f"{n['id']}.mp3")
            try:
                gerar_narracao(texto_editado, caminho2, st.session_state.voz)
                n["audio_ok"] = caminho2
                n["audio_erro"] = None
            except Exception as e:
                n["audio_erro"] = str(e)
            st.rerun()
        st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Voltar"):
            st.session_state.etapa = 2
            st.rerun()
    with col2:
        precisa_audio = [
            n for n in selecionadas
            if not (n.get("audio_ok") and os.path.exists(n["audio_ok"]))
        ]
        if precisa_audio:
            st.info(f"⚠️ {len(precisa_audio)} narração(ões) pendente(s). Clique em 'Gerar áudio' abaixo.")
            if st.button("🔊 Gerar áudios pendentes"):
                for n in precisa_audio:
                    caminho = os.path.join(st.session_state.audio_dir, f"{n['id']}.mp3")
                    try:
                        gerar_narracao(n.get("roteiro", ""), caminho, st.session_state.voz)
                        n["audio_ok"] = caminho
                    except Exception as e:
                        n["audio_erro"] = str(e)
                st.rerun()
        else:
            st.session_state["aprovadas_lista"] = [
                n for n in selecionadas
                if st.session_state.get(f"aprov_{n['id']}", True)
            ]
            avancar = st.button("🎬 Gerar vídeo final", type="primary",
                                use_container_width=True,
                                disabled=aprovadas == 0)
            if avancar:
                st.session_state.etapa = 4
                st.rerun()


# ---------------------------------------------------------------- ETAPA 4
elif st.session_state.etapa == 4:
    st.header("🎬 Etapa 4 — Vídeo final: revisão e aprovação")
    st.caption("O vídeo é montado localmente. Confira o resultado antes de aprovar.")

    aprovadas = st.session_state.get("aprovadas_lista", [])
    if not aprovadas:
        st.warning("Nenhuma notícia aprovada. Volte à etapa 3.")
        if st.button("← Voltar"):
            st.session_state.etapa = 3
            st.rerun()
        st.stop()

    video_dir = os.path.join(DIR_DADOS, f"video_{uuid.uuid4().hex[:8]}")
    os.makedirs(video_dir, exist_ok=True)
    saida = os.path.join(video_dir, "jornal_final.mp4")

    gerar = st.button("🎬 Montar vídeo (YouTube 16:9)", type="primary")
    if gerar:
        with st.spinner("Montando vídeo com imagem de fundo + trilha sonora..."):
            try:
                montar_video(
                    aprovadas,
                    st.session_state.audio_dir,
                    saida,
                    largura=1920,
                    altura=1080,
                    modo_imagem=st.session_state.get("modo_imagem", "imagem"),
                    musica_path=st.session_state.get("musica_path"),
                    volume_musica=st.session_state.get("volume_musica", 0.12),
                )
                st.session_state["video_pronto"] = saida
            except Exception as e:
                st.error(f"Erro ao montar vídeo: {e}")

    video_pronto = st.session_state.get("video_pronto")
    if video_pronto and os.path.exists(video_pronto):
        st.success("✅ Vídeo gerado!")
        st.video(video_pronto)
        with open(video_pronto, "rb") as f:
            st.download_button(
                "💾 Baixar vídeo (MP4)",
                f.read(),
                file_name="jornal_diario.mp4",
                mime="video/mp4",
            )

    st.subheader("Resumo do que entrará no vídeo")
    for n in aprovadas:
        st.markdown(f"- **[{n['categoria']}]** {n['titulo']} — *{n['fonte']}*")

    if st.button("🏁 Aprovar e finalizar edição"):
        st.balloons()
        st.success("Edição aprovada! Aqui termina o protótipo do fluxo completo.")
        st.info("Próximos passos reais: upload no YouTube (API) e geração da versão TikTok 9:16.")


# Rodapé com versão — visível em PC e celular (fora da sidebar, sempre no fim)
st.divider()
st.caption(f"JornalDiário v{__version__} • grátis • alterações versionadas — github.com/dandoidao19/Jornal")