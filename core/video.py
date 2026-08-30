import os

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    afx,
    concatenate_videoclips,
)

from .cards import preparar_fundo_imagem


def _altura_duracao(audio_path: str) -> float:
    try:
        with AudioFileClip(audio_path) as a:
            return max(a.duration, 3.0)
    except Exception:
        return 4.0


def montar_video(
    noticias: list,
    audio_dir: str,
    saida: str,
    largura=1920,
    altura=1080,
    modo_imagem: str = "imagem",
    musica_path: str | None = None,
    volume_musica: float = 0.12,
) -> str:
    """
    Monta o vídeo final.
    - modo_imagem="imagem": fundo é a imagem real da notícia (sem texto), com fallback para card.
    - modo_imagem="card": força card textual (compatibilidade).
    - musica_path: MP3/WAV de trilha; tocada em loop baixinho por baixo da narração.
    """
    clips = []
    audio_clipes = []
    try:
        for n in noticias:
            audio = os.path.join(audio_dir, f"{n['id']}.mp3")
            af = AudioFileClip(audio)
            audio_clipes.append(af)
            dur = max(af.duration, 3.0)

            fundo_base = os.path.join(audio_dir, f"{n['id']}.png")
            if modo_imagem == "imagem":
                fundo = preparar_fundo_imagem(
                    n.get("imagem"), fundo_base, largura=largura, altura=altura, noticia=n
                )
            else:
                from .cards import criar_card

                fundo = criar_card(n, fundo_base, largura=largura, altura=altura)
                # criar_card salva PNG, mas preparar já tratou; garante jpg se necessário
                if fundo.lower().endswith(".png"):
                    # converte para compatibilidade já tratada dentro de preparar, mas aqui mantém
                    pass

            clip = ImageClip(fundo).with_duration(dur).with_audio(af)
            # fundo já está em 1920x1080, evita novo resize que borra
            if clip.w != largura or clip.h != altura:
                clip = clip.resized((largura, altura))
            clips.append(clip)
    except Exception as e:
        for c in audio_clipes:
            try:
                c.close()
            except Exception:
                pass
        if not clips:
            raise RuntimeError(f"Falha ao montar vídeo: {e}")

    if not clips:
        raise RuntimeError("Nenhum clipe gerado.")

    video = concatenate_videoclips(clips, method="compose")

    # trilha sonora em segundo plano (mixada baixinho, em loop sem explodir memória)
    if musica_path and os.path.exists(musica_path):
        try:
            mus = AudioFileClip(musica_path)
            mus = mus.with_effects([afx.AudioLoop(duration=video.duration)])
            mus = mus.with_volume_scaled(volume_musica)
            video = video.with_audio(CompositeAudioClip([video.audio, mus]))
        except Exception:
            pass

    os.makedirs(os.path.dirname(saida), exist_ok=True)
    video.write_videofile(
        saida,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=4,
        bitrate="6000k",
        logger=None,
    )
    video.close()
    for c in clips + audio_clipes:
        try:
            c.close()
        except Exception:
            pass
    return saida