# JornalDiário — Jornal eletrônico diário (grátis)

Protótipo em **Streamlit** que transforma notícias do dia em um vídeo narrado:
1. Busca notícias reais (GDELT + feeds BR + Google News + internacionais com tradução);
2. Seleciona as pautas e categoria;
3. Gera roteiro (IA ou template) + narração TTS;
4. Monta vídeo 16:9 com imagem de fundo + trilha sonora.

## Rodar local

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Acesse `http://localhost:8501` (ou `http://SEU_IP:8501` no celular na mesma rede).

## Chaves de IA (opcionais)

Sem chaves o app funciona com o roteirista por _template_ e **sem tradução de notícias internacionais**.
Para roteiro por IA e tradução, configure **uma** das chaves (todas têm plano grátis):

| Provedor | Chave | Onde pegar |
|---|---|---|
| Groq | `GROQ_API_KEY` | console.groq.com (grátis) |
| Google Gemini | `GEMINI_API_KEY` | aistudio.google.com (grátis) |

**Nunca coloque chaves no repositório.** Prefira variável de ambiente ou, no deploy em nuvem, os *Secrets* da plataforma. O arquivo `data/config.example.json` é o modelo a copiar para `data/config.json` (ignorado pelo git).

## Testes e CI

```powershell
.venv\Scripts\python -m pytest -q
```

CI roda pytest no GitHub Actions a cada push (`.github/workflows/ci.yml`).

## Deploy (link fixo e grátis)

O repo já está pronto para subir. Opções gratuitas:

- **Streamlit Community Cloud** (recomendado): link fixo `https://app.streamlit.app` a partir do repo privado
  `dandoidao19/Jornal`. Na plataforma: *New app* → seleciona o repo → em **Secrets** preencha
  `GROQ_API_KEY` / `GEMINI_API_KEY`. O `requirements.txt` e o `packages.txt` (ffmpeg) são instalados
  automaticamente.
- **Túnel local (dev)**: `npx localtunnel --port 8501 --subdomain jornal-dandoidao19` → URL fixa enquanto o PC estiver ligado.

## Estrutura

```
app.py                 interface Streamlit (4 etapas)
core/busca.py          fontes e deduplicação
core/categorias.py     classificação por palavras-chave
core/roteiro.py        roteiro por template (fallback)
core/roteiro_ia.py     roteiro por IA (Groq/Gemini) lê artigo completo
core/traducao.py       tradução pt-BR
core/narracao.py       TTS grátis via edge-tts
core/imagens.py        extração de imagem da notícia
core/cards.py          cards/fundos com fontes empacotadas + cache
core/video.py          montagem final (moviepy + ffmpeg)
tests/                 testes pytest
assets/fonts/          fontes livres (DejaVu) para funcionar em qualquer SO
```

## Licenças e custos

- Todas as APIs usadas têm plano gratuito: GDELT, feeds públicos, edge-tts (Microsoft),
  Groq e Gemini (free tier).
- Fontes DejaVu: licença livre (Domínio Público / DejaVu License).