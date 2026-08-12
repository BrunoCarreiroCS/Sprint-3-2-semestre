"""Configuracoes centrais do JOVI AI LensLab."""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
SAMPLES_DIR = ROOT_DIR / "samples"
DB_PATH = DATA_DIR / "jovi.db"

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MIN_IMAGE_WIDTH = 320
MIN_IMAGE_HEIGHT = 240
API_IMAGE_MAX_SIDE = 1600
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def ensure_directories() -> None:
    """Cria somente os diretorios de dados previstos pelo projeto."""
    for directory in (DATA_DIR, OUTPUT_DIR, SAMPLES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _ler_env_local(nome: str) -> str | None:
    """Le uma variavel simples de ``.env`` sem expor ou modificar o ambiente."""
    arquivo = ROOT_DIR / ".env"
    if not arquivo.exists():
        return None
    try:
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            limpa = linha.strip()
            if not limpa or limpa.startswith("#") or "=" not in limpa:
                continue
            chave, valor = limpa.split("=", 1)
            if chave.strip() == nome:
                return valor.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def get_gemini_api_key() -> str | None:
    """Le a chave do ambiente sem imprimir ou persistir seu valor."""
    value = os.getenv("GEMINI_API_KEY", "").strip() or (_ler_env_local("GEMINI_API_KEY") or "")
    return value or None


def get_gemini_model() -> str:
    """Retorna o modelo configurado ou o padrao estavel do projeto."""
    value = os.getenv("GEMINI_MODEL", "").strip() or (_ler_env_local("GEMINI_MODEL") or "")
    return value or DEFAULT_GEMINI_MODEL
