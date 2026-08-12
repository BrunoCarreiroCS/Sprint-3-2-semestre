"""Gera fotos artificiais para demonstrar o modo offline sem dados pessoais."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    escura = Image.new("RGB", (960, 640), (12, 18, 30))
    desenho = ImageDraw.Draw(escura)
    desenho.ellipse((340, 170, 620, 540), fill=(75, 65, 58))
    escura.save(SAMPLES / "exemplo_escuro.jpg", quality=92)

    nítida = Image.new("RGB", (960, 640), (190, 205, 220))
    desenho = ImageDraw.Draw(nítida)
    for x in range(80, 880, 40):
        desenho.line((x, 80, x, 560), fill=(20, 60, 110), width=5)
    nítida.save(SAMPLES / "exemplo_nitido.jpg", quality=92)

    borrada = nítida.filter(ImageFilter.GaussianBlur(radius=8))
    borrada.save(SAMPLES / "exemplo_borrado.jpg", quality=92)
    print(f"Amostras geradas em {SAMPLES}")


if __name__ == "__main__":
    main()
