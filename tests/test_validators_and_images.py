from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from image_analyzer import analisar_imagem, gerar_simulacao, preparar_imagem_api
from validators import ValidationError, normalizar_sim_nao, validar_caminho_imagem, validar_inteiro


class ValidatorsAndImagesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.image = self.dir / "foto.png"
        Image.new("RGB", (640, 480), (28, 36, 48)).save(self.image)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_validadores_rejeitam_entradas_invalidas(self) -> None:
        self.assertEqual(validar_inteiro("3", 1, 5), 3)
        self.assertTrue(normalizar_sim_nao("sim"))
        self.assertFalse(normalizar_sim_nao("não"))
        with self.assertRaises(ValidationError):
            validar_inteiro("x", 1, 5)
        with self.assertRaises(ValidationError):
            validar_caminho_imagem(self.dir / "ausente.jpg")

    def test_analise_local_retorna_metricas_e_hash(self) -> None:
        resultado = analisar_imagem(self.image)
        self.assertEqual(resultado["largura"], 640)
        self.assertEqual(resultado["altura"], 480)
        self.assertEqual(len(resultado["imagem_hash"]), 64)
        self.assertLess(resultado["brilho"], 35)

    def test_copia_para_api_e_temporaria_sem_metadados(self) -> None:
        with preparar_imagem_api(self.image) as copia:
            self.assertTrue(copia.exists())
            with Image.open(copia) as imagem:
                self.assertEqual(imagem.format, "JPEG")
                self.assertLessEqual(max(imagem.size), 1600)
                self.assertEqual(len(imagem.getexif()), 0)
        self.assertFalse(copia.exists())

    def test_simulacao_nao_sobrescreve_original(self) -> None:
        conteudo_antes = self.image.read_bytes()
        destino = gerar_simulacao(self.image, "adicionar_iluminacao", 999)
        self.assertTrue(destino.exists())
        self.assertEqual(self.image.read_bytes(), conteudo_antes)

    def test_exif_do_sub_ifd_e_lido(self) -> None:
        from PIL import Image as PILImage
        from PIL.ExifTags import Base as ExifBase

        caminho = self.dir / "com_exif.jpg"
        imagem = PILImage.new("RGB", (640, 480), (60, 70, 80))
        exif = imagem.getexif()
        sub_ifd = exif.get_ifd(0x8769)
        sub_ifd[ExifBase.ISOSpeedRatings.value] = 400
        sub_ifd[ExifBase.ExposureTime.value] = 0.02
        imagem.save(caminho, exif=exif)

        resultado = analisar_imagem(caminho)
        self.assertEqual(resultado["exif"].get("iso"), 400.0)
        self.assertAlmostEqual(resultado["exif"].get("tempo_exposicao"), 0.02)

    def test_sem_exif_nao_gera_erro(self) -> None:
        resultado = analisar_imagem(self.image)
        self.assertEqual(resultado["exif"], {})

    def test_seletor_de_arquivo_devolve_caminho_validado(self) -> None:
        import main

        with patch("tkinter.filedialog.askopenfilename", return_value=str(self.image)):
            resultado = main.abrir_seletor_arquivo()
        self.assertEqual(resultado, self.image.resolve())

    def test_seletor_de_arquivo_cancelado_devolve_none(self) -> None:
        import main

        with patch("tkinter.filedialog.askopenfilename", return_value=""):
            resultado = main.abrir_seletor_arquivo()
        self.assertIsNone(resultado)


if __name__ == "__main__":
    unittest.main()
