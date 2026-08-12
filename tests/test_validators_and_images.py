from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
