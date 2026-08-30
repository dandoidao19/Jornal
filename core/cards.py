import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
}

FONT_DIR = r"C:\Windows\Fonts"
FONT_TITULO = os.path.join(FONT_DIR, "arialbd.ttf")
FONT_TEXTO = os.path.join(FONT_DIR, "arial.ttf")
FONT_FONTE = os.path.join(FONT_DIR, "arial.ttf")

CORES = {
    "Economia": "#1e6f5c",
    "Politica": "#2b3a67",
    "Social": "#7b2d8b",
    "Saude": "#0e7490",
    "Meio ambiente": "#065f46",
    "Internet": "#0e7490",
    "Mundo": "#b45309",
    "Esportes": "#9d174d",
    "Familia": "#92400e",
    "Geral": "#374151",
}


def _fonte(caminho, tamanho):
    try:
        return ImageFont.truetype(caminho, tamanho)
    except Exception:
        return ImageFont.load_default()


def quebrar_linhas(texto: str, fonte, max_largura: int, draw: ImageDraw) -> list:
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=fonte) <= max_largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def criar_card(noticia: dict, caminho: str, largura=1920, altura=1080) -> str:
    cor = CORES.get(noticia.get("categoria", "Geral"), "#374151")
    img = Image.new("RGB", (largura, altura), cor)
    draw = ImageDraw.Draw(img)

    faixa = 90 if largura >= 1920 else 54
    draw.rectangle(
        [(0, altura - faixa), (largura, altura)], fill="#111827"
    )

    categoria = noticia.get("categoria") or "Geral"
    f_cat = _fonte(FONT_TEXTO, int(largura * 0.055))
    f_tit = _fonte(FONT_TITULO, int(largura * 0.062))
    f_fon = _fonte(FONT_FONTE, int(largura * 0.04))

    draw.text((largura * 0.06, altura * 0.07), categoria.upper(), font=f_cat, fill="#ffffff")

    margem = int(largura * 0.06)
    linhas = quebrar_linhas(noticia.get("titulo", ""), f_tit, largura - margem * 2, draw)
    y = int(altura * 0.22)
    for ln in linhas[:5]:
        draw.text((margem, y), ln, font=f_tit, fill="#ffffff")
        y += int(largura * 0.085)

    fonte_txt = noticia.get("fonte") or "Fonte desconhecida"
    draw.text(
        (margem, altura - faixa + 18),
        f"Fonte: {fonte_txt}",
        font=f_fon,
        fill="#d1d5db",
    )

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    # PNG sem perda, alta resolução
    img.save(caminho, format="PNG", optimize=False)
    return caminho


def _baixar_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        pass
    return None


def preparar_fundo_imagem(imagem_url: str | None, destino: str, largura=1920, altura=1080, noticia: dict | None = None) -> str:
    """Baixa a imagem da notícia em ALTA, corta para preencher. Sem recompressão visível."""
    if imagem_url:
        raw = _baixar_bytes(imagem_url)
        if raw:
            try:
                img = Image.open(BytesIO(raw)).convert("RGB")
                # se a imagem já for grande, mantém nitidez; se for pequena, upscale com LANCZOS + leve nitidez
                # evita interpolar thumbnail borrado: se a imagem for < 800px de largura, log para debug
                img = ImageOps.fit(img, (largura, altura), method=Image.LANCZOS, centering=(0.5, 0.5))
                # leve aumento de nitidez para compensar upscale
                try:
                    from PIL import ImageFilter

                    if img.width >= largura and img.height >= altura:
                        pass
                    else:
                        img = img.filter(ImageFilter.SHARPEN)
                except Exception:
                    pass
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                # JPG alta qualidade 95 (nítido e leve) — evita PNG gigante que trava o ffmpeg
                if destino.lower().endswith(".png"):
                    destino = os.path.splitext(destino)[0] + ".jpg"
                img.save(destino, format="JPEG", quality=95, subsampling=0, optimize=True)
                return destino
            except Exception:
                pass
    # fallback: card com título/fonte
    if noticia is not None:
        if destino.lower().endswith(".png"):
            destino = os.path.splitext(destino)[0] + ".jpg"
            # criar_card salva como PNG, converte
            tmp = destino.replace(".jpg", ".png")
            criar_card(noticia, tmp, largura=largura, altura=altura)
            try:
                from PIL import Image as _Im

                im = _Im.open(tmp).convert("RGB")
                im.save(destino, format="JPEG", quality=95, subsampling=0, optimize=True)
                os.remove(tmp)
            except Exception:
                destino = tmp
            return destino
        return criar_card(noticia, destino, largura=largura, altura=altura)
    img = Image.new("RGB", (largura, altura), CORES.get("Geral"))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if destino.lower().endswith(".png"):
        destino = os.path.splitext(destino)[0] + ".jpg"
    img.save(destino, format="JPEG", quality=95, subsampling=0, optimize=True)
    return destino