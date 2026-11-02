"""Analise tecnica local e simulacoes seguras de fotografias."""

from __future__ import annotations

import hashlib
import math
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, UnidentifiedImageError

from config import API_IMAGE_MAX_SIDE, MIN_IMAGE_HEIGHT, MIN_IMAGE_WIDTH, OUTPUT_DIR
from validators import ValidationError, validar_caminho_imagem


def calcular_hash(caminho: str | Path) -> str:
    digest = hashlib.sha256()
    with open(caminho, "rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _numero_exif(valor: object) -> float | None:
    try:
        return round(float(valor), 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _extrair_exif_seguro(imagem: Image.Image) -> dict:
    """Le ISO, tempo de exposicao e distancia focal, que ficam no Exif Sub-IFD
    (tag 0x8769) e nao no IFD0 devolvido diretamente por ``Image.getexif()``."""
    exif = imagem.getexif()
    combinado = dict(exif)
    try:
        combinado.update(exif.get_ifd(0x8769))
    except (KeyError, AttributeError, ValueError, TypeError):
        pass
    dados: dict[str, float | int] = {}
    mapa = {34855: "iso", 33434: "tempo_exposicao", 37386: "distancia_focal"}
    for codigo, nome in mapa.items():
        if codigo in combinado:
            valor = _numero_exif(combinado.get(codigo))
            if valor is not None:
                dados[nome] = valor
    return dados


def analisar_imagem(caminho: str | Path) -> dict:
    arquivo = validar_caminho_imagem(caminho)
    try:
        with Image.open(arquivo) as original:
            original.verify()
        with Image.open(arquivo) as original:
            imagem = ImageOps.exif_transpose(original).convert("RGB")
            largura, altura = imagem.size
            if largura < MIN_IMAGE_WIDTH or altura < MIN_IMAGE_HEIGHT:
                raise ValidationError(
                    f"Resolução mínima: {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels."
                )
            exif = _extrair_exif_seguro(original)
            rgb = np.asarray(imagem)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("A imagem está corrompida ou não pode ser decodificada.") from exc

    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    brilho = float(np.mean(cinza) / 255 * 100)
    contraste = float(min(100, np.std(cinza) / 127.5 * 100))
    nitidez_bruta = float(cv2.Laplacian(cinza, cv2.CV_64F).var())
    saturacao = float(np.mean(hsv[:, :, 1]) / 255 * 100)
    sombras = float(np.mean(cinza <= 10) * 100)
    realces = float(np.mean(cinza >= 245) * 100)

    return {
        "brilho": round(brilho, 2),
        "contraste": round(contraste, 2),
        "nitidez_bruta": round(nitidez_bruta, 2),
        "saturacao": round(saturacao, 2),
        "sombras_recortadas": round(sombras, 2),
        "realces_estourados": round(realces, 2),
        "largura": int(largura),
        "altura": int(altura),
        "proporcao": round(largura / altura, 4),
        "megapixels": round(largura * altura / 1_000_000, 3),
        "exif": exif,
        "imagem_hash": calcular_hash(arquivo),
        "nome_arquivo": arquivo.name,
    }


@contextmanager
def preparar_imagem_api(caminho: str | Path) -> Iterator[Path]:
    """Gera JPEG reduzido e sem metadados, removendo-o sempre ao final."""
    arquivo = validar_caminho_imagem(caminho)
    temporario: Path | None = None
    try:
        with Image.open(arquivo) as original:
            imagem = ImageOps.exif_transpose(original).convert("RGB")
            imagem.thumbnail((API_IMAGE_MAX_SIDE, API_IMAGE_MAX_SIDE), Image.Resampling.LANCZOS)
            handle = tempfile.NamedTemporaryFile(prefix="jovi_api_", suffix=".jpg", delete=False)
            temporario = Path(handle.name)
            handle.close()
            imagem.save(temporario, "JPEG", quality=85, optimize=True)
        yield temporario
    finally:
        if temporario and temporario.exists():
            temporario.unlink()


def _fonte_aviso(tamanho: int) -> tuple[ImageFont.ImageFont | ImageFont.FreeTypeFont, str]:
    """Usa uma fonte do sistema com acentos; sem ela, a fonte embutida do Pillow recebe o aviso sem acentos."""
    for nome in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho), "SIMULAÇÃO EDUCATIVA - NÃO É RECAPTURA"
        except OSError:
            continue
    return ImageFont.load_default(), "SIMULACAO EDUCATIVA - NAO E RECAPTURA"


def gerar_simulacao(caminho: str | Path, codigo_acao: str, usuario_id: int) -> Path:
    """Cria uma previa educativa sem sobrescrever a fotografia original."""
    arquivo = validar_caminho_imagem(caminho)
    destino_dir = OUTPUT_DIR / "simulacoes" / str(usuario_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"SIMULACAO_{codigo_acao}_{arquivo.stem}.jpg"

    with Image.open(arquivo) as original:
        imagem = ImageOps.exif_transpose(original).convert("RGB")
        if codigo_acao == "adicionar_iluminacao":
            imagem = ImageEnhance.Brightness(imagem).enhance(1.25)
        elif codigo_acao == "ajustar_contraste":
            imagem = ImageEnhance.Contrast(imagem).enhance(1.2)
        elif codigo_acao == "reduzir_saturacao":
            imagem = ImageEnhance.Color(imagem).enhance(0.75)
        elif codigo_acao == "aumentar_nitidez":
            imagem = ImageEnhance.Sharpness(imagem).enhance(1.8)
        elif codigo_acao == "reposicionar_enquadramento":
            desenho = ImageDraw.Draw(imagem)
            w, h = imagem.size
            desenho.rectangle((w // 6, h // 6, 5 * w // 6, 5 * h // 6), outline="#00D4FF", width=max(3, w // 250))

        desenho = ImageDraw.Draw(imagem)
        margem = max(8, imagem.width // 100)
        altura_faixa = max(34, imagem.height // 14)
        fonte, texto = _fonte_aviso(max(12, altura_faixa // 2))
        desenho.rectangle((0, 0, imagem.width, altura_faixa), fill=(5, 20, 40))
        desenho.text((margem, margem), texto, fill=(255, 255, 255), font=fonte)
        imagem.save(destino, "JPEG", quality=90)
    return destino


def normalizar_nitidez(valor_bruto: float) -> float:
    """Normalizacao suave para evitar dominancia de valores extremos."""
    return round(min(100.0, math.sqrt(max(0.0, valor_bruto)) * 4.0), 2)

