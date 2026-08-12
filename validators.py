"""Validacoes puras e auxiliares de entrada para a interface textual."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from config import MAX_IMAGE_BYTES, SUPPORTED_IMAGE_EXTENSIONS


class ValidationError(ValueError):
    """Erro de entrada que pode ser mostrado ao usuario."""


def validar_texto(valor: str, nome: str = "valor", minimo: int = 1, maximo: int = 160) -> str:
    texto = str(valor).strip()
    if len(texto) < minimo:
        raise ValidationError(f"{nome.capitalize()} nao pode ficar vazio.")
    if len(texto) > maximo:
        raise ValidationError(f"{nome.capitalize()} deve ter no maximo {maximo} caracteres.")
    return texto


def validar_escolha(valor: str, opcoes: Iterable[str], nome: str = "opcao") -> str:
    texto = str(valor).strip().lower()
    validas = [str(opcao).lower() for opcao in opcoes]
    if texto not in validas:
        raise ValidationError(f"{nome.capitalize()} invalida. Escolha: {', '.join(validas)}.")
    return texto


def validar_inteiro(valor: str | int, minimo: int, maximo: int, nome: str = "valor") -> int:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{nome.capitalize()} deve ser um numero inteiro.") from exc
    if not minimo <= numero <= maximo:
        raise ValidationError(f"{nome.capitalize()} deve estar entre {minimo} e {maximo}.")
    return numero


def normalizar_sim_nao(valor: str) -> bool:
    texto = str(valor).strip().lower()
    if texto in {"sim", "s"}:
        return True
    if texto in {"nao", "não", "n"}:
        return False
    raise ValidationError("Responda com sim ou nao.")


def validar_caminho_imagem(valor: str | Path, limite_bytes: int = MAX_IMAGE_BYTES) -> Path:
    caminho = Path(str(valor).strip().strip('"')).expanduser()
    if not caminho.exists():
        raise ValidationError("Arquivo de imagem nao encontrado.")
    if not caminho.is_file():
        raise ValidationError("O caminho informado nao e um arquivo.")
    if caminho.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        formatos = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise ValidationError(f"Formato nao suportado. Use: {formatos}.")
    try:
        tamanho = caminho.stat().st_size
    except OSError as exc:
        raise ValidationError("Nao foi possivel ler o arquivo.") from exc
    if tamanho > limite_bytes:
        raise ValidationError("A imagem ultrapassa o limite de 20 MB.")
    return caminho.resolve()


def solicitar_validado(
    mensagem: str,
    validador: Callable[[str], object],
    permitir_cancelar: bool = False,
) -> object | None:
    """Repete uma entrada invalida sem recursao; `0` cancela quando permitido."""
    while True:
        valor = input(mensagem).strip()
        if permitir_cancelar and valor == "0":
            return None
        try:
            return validador(valor)
        except ValidationError as exc:
            print(f"Entrada invalida: {exc}")

