"""Interface textual do NextFrame JOVI AI LensLab."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import database
from analysis_service import analisar_fotografia
from config import DB_PATH, ensure_directories, get_gemini_api_key
from image_analyzer import calcular_hash, gerar_simulacao
from learning_engine import comparar_e_aprender
from recommendation_engine import recomendar_sem_foto
from reports import exportar_resumo, formatar_analise, formatar_comparacao, formatar_evolucao
from validators import (
    ValidationError,
    normalizar_sim_nao,
    solicitar_validado,
    validar_caminho_imagem,
    validar_inteiro,
    validar_texto,
)


OBJETIVOS = ["documento", "pessoa", "retrato", "paisagem", "produto", "redes_sociais", "outro"]
NIVEIS = ["iniciante", "intermediario", "avancado"]
ESTILOS = ["natural", "equilibrado", "vibrante"]


def titulo(texto: str) -> None:
    print("\n" + "=" * 68)
    print(texto.center(68))
    print("=" * 68)


def escolher_rotulada(rotulo: str, opcoes: list[str], cancelar: bool = True) -> str | None:
    print(f"\n{rotulo}:")
    for indice, opcao in enumerate(opcoes, 1):
        print(f"  {indice}. {opcao.replace('_', ' ').title()}")
    if cancelar:
        print("  0. Cancelar")
    minimo = 0 if cancelar else 1
    numero = solicitar_validado("Escolha: ", lambda valor: validar_inteiro(valor, minimo, len(opcoes), "opcao"))
    if numero == 0:
        return None
    return opcoes[int(numero) - 1]


def escolher_registro(registros: list[dict], descricao, rotulo: str = "registro") -> dict | None:
    if not registros:
        print(f"Nenhum {rotulo} disponivel.")
        return None
    for indice, registro in enumerate(registros, 1):
        print(f"  {indice}. {descricao(registro)}")
    print("  0. Cancelar")
    numero = solicitar_validado("Escolha: ", lambda valor: validar_inteiro(valor, 0, len(registros), rotulo))
    return None if numero == 0 else registros[int(numero) - 1]


def criar_perfil(caminho_banco: str | Path = DB_PATH) -> dict | None:
    titulo("CRIAR PERFIL")
    apelido = solicitar_validado("Apelido (0 cancela): ", lambda v: validar_texto(v, "apelido", 2, 40), True)
    if apelido is None:
        return None
    nivel = escolher_rotulada("Nivel de experiencia", NIVEIS)
    if nivel is None:
        return None
    estilo = escolher_rotulada("Estilo preferido", ESTILOS)
    if estilo is None:
        return None
    consentimento = solicitar_validado(
        "Autoriza enviar copia reduzida e sem metadados ao Gemini? (sim/nao): ", normalizar_sim_nao
    )
    try:
        usuario = database.criar_usuario(str(apelido), nivel, estilo, bool(consentimento), caminho_banco)
    except sqlite3.IntegrityError:
        print("Esse apelido ja existe. Selecione o perfil existente.")
        return None
    print(f"Perfil {usuario['apelido']} criado. O aprendizado sera isolado neste perfil.")
    return usuario


def selecionar_perfil(caminho_banco: str | Path = DB_PATH) -> dict | None:
    titulo("SELECIONAR PERFIL")
    usuarios = database.listar_usuarios(caminho_banco)
    if not usuarios:
        print("Ainda nao ha perfis. Vamos criar o primeiro.")
        return criar_perfil(caminho_banco)
    print("  1. Selecionar perfil existente")
    print("  2. Criar novo perfil")
    print("  0. Cancelar")
    escolha = solicitar_validado("Escolha: ", lambda v: validar_inteiro(v, 0, 2, "opcao"))
    if escolha == 0:
        return None
    if escolha == 2:
        return criar_perfil(caminho_banco)
    return escolher_registro(usuarios, lambda u: f"{u['apelido']} ({u['nivel']}, {u['estilo_preferido']})", "perfil")


def executar_analise(usuario: dict, caminho_banco: str | Path = DB_PATH, contexto: dict | None = None) -> dict | None:
    titulo("ANALISAR FOTOGRAFIA")
    caminho = solicitar_validado("Caminho da imagem (0 cancela): ", validar_caminho_imagem, True)
    if caminho is None:
        return None
    objetivo = contexto["objetivo"] if contexto else escolher_rotulada("Objetivo", OBJETIVOS)
    if objetivo is None:
        return None
    intencao = contexto["intencao"] if contexto else solicitar_validado(
        "Qual era sua intencao com a foto? ", lambda v: validar_texto(v, "intencao", 3, 160)
    )
    estilo = contexto["estilo"] if contexto else usuario["estilo_preferido"]
    permitir_api = bool(usuario["consentimento_api"])
    if permitir_api and not get_gemini_api_key():
        print("Aviso: GEMINI_API_KEY nao configurada; o modo offline sera usado.")
    print("Analisando sem alterar a fotografia original...")
    try:
        resultado = analisar_fotografia(
            usuario, caminho, str(objetivo), str(intencao), str(estilo), permitir_api, caminho_banco
        )
    except ValidationError as exc:
        print(f"Nao foi possivel analisar: {exc}")
        return None
    print(formatar_analise(resultado))
    resultado["caminho_original"] = str(caminho)
    return resultado


def selecionar_analise(usuario: dict, caminho_banco: str | Path = DB_PATH) -> dict | None:
    analises = database.listar_analises(usuario["id"], caminho_banco)
    resumo = escolher_registro(
        analises,
        lambda a: f"#{a['id']} {a['nome_arquivo']} - {a['pontuacao_geral']:.1f}/100 ({a['objetivo']})",
        "analise",
    )
    return database.buscar_analise(resumo["id"], caminho_banco) if resumo else None


def selecionar_recomendacao(analise_id: int, caminho_banco: str | Path = DB_PATH) -> dict | None:
    recomendacoes = database.listar_recomendacoes(analise_id, caminho_banco)
    return escolher_registro(
        recomendacoes,
        lambda r: f"{r['codigo_acao'].replace('_', ' ').title()} (ganho previsto +{r['ganho_previsto']:.1f})",
        "recomendacao",
    )


def explorar_simulacao(usuario: dict, caminho_banco: str | Path = DB_PATH) -> None:
    titulo("EXPLORAR CENARIOS E SE?")
    analise = selecionar_analise(usuario, caminho_banco)
    if not analise:
        return
    recomendacao = selecionar_recomendacao(analise["id"], caminho_banco)
    if not recomendacao:
        return
    simulaveis = {
        "adicionar_iluminacao", "ajustar_contraste", "reduzir_saturacao",
        "aumentar_nitidez", "reposicionar_enquadramento",
    }
    if recomendacao["codigo_acao"] not in simulaveis:
        print("Essa orientacao exige recaptura fisica e nao possui previa digital honesta.")
        return
    caminho = solicitar_validado("Informe novamente a foto original (0 cancela): ", validar_caminho_imagem, True)
    if caminho is None:
        return
    if calcular_hash(caminho) != analise["imagem_hash"]:
        print("A imagem informada nao corresponde a analise selecionada.")
        return
    destino = gerar_simulacao(caminho, recomendacao["codigo_acao"], usuario["id"])
    print(f"Previa educativa criada em: {destino}")
    print("Ela e uma simulacao visual, nao uma prova de melhoria. A prova ocorre na recaptura.")


def comparar_recaptura(usuario: dict, caminho_banco: str | Path = DB_PATH) -> None:
    titulo("COMPARAR ANTES E DEPOIS")
    print("Escolha a analise original:")
    antes = selecionar_analise(usuario, caminho_banco)
    if not antes:
        return
    print("Escolha a recomendacao que voce aplicou:")
    recomendacao = selecionar_recomendacao(antes["id"], caminho_banco)
    if not recomendacao:
        return
    database.marcar_recomendacao(recomendacao["id"], antes["id"], caminho_banco)
    print("Agora informe a nova foto. Ela sera avaliada no mesmo contexto da original.")
    resultado_depois = executar_analise(
        usuario,
        caminho_banco,
        {"objetivo": antes["objetivo"], "intencao": antes["intencao"], "estilo": antes["estilo"]},
    )
    if not resultado_depois:
        return
    avaliacao = solicitar_validado(
        "Quanto a recomendacao ajudou? (1 a 5): ", lambda v: validar_inteiro(v, 1, 5, "avaliacao")
    )
    comentario = input("Comentario opcional: ").strip()[:500]
    try:
        comparacao = comparar_e_aprender(
            usuario["id"], antes["id"], resultado_depois["analise_id"],
            recomendacao["id"], int(avaliacao), comentario, caminho_banco,
        )
    except ValueError as exc:
        print(f"Comparacao recusada: {exc}")
        return
    print(formatar_comparacao(comparacao))
    print("O peso foi atualizado somente para este usuario e este tipo de contexto.")


def marcar_conselho(usuario: dict, caminho_banco: str | Path = DB_PATH) -> None:
    titulo("ESCOLHER RECOMENDACAO")
    analise = selecionar_analise(usuario, caminho_banco)
    if not analise:
        return
    recomendacao = selecionar_recomendacao(analise["id"], caminho_banco)
    if recomendacao:
        database.marcar_recomendacao(recomendacao["id"], analise["id"], caminho_banco)
        print("Recomendacao registrada. Depois use 'Comparar antes e depois'.")


def mostrar_historico(usuario: dict, caminho_banco: str | Path = DB_PATH) -> None:
    titulo("HISTORICO")
    analises = database.listar_analises(usuario["id"], caminho_banco)
    if not analises:
        print("Nenhuma analise registrada.")
        return
    for item in analises:
        print(
            f"#{item['id']:03d} | {item['criado_em'][:19]} | {item['pontuacao_geral']:5.1f}/100 | "
            f"{item['modo_execucao'].upper():7s} | {item['nome_arquivo']}"
        )


def recomendacao_sem_foto(usuario: dict) -> None:
    titulo("ORIENTACAO SEM FOTO")
    objetivo = escolher_rotulada("Objetivo", OBJETIVOS)
    if objetivo is None:
        return
    ambiente = escolher_rotulada("Luz do ambiente", ["escuro", "equilibrado", "muito_claro"])
    if ambiente is None:
        return
    movimento = solicitar_validado("O assunto esta em movimento? (sim/nao): ", normalizar_sim_nao)
    recomendacoes = recomendar_sem_foto(usuario, objetivo, ambiente, bool(movimento))
    for indice, item in enumerate(recomendacoes, 1):
        print(f"\n{indice}. {item['codigo_acao'].replace('_', ' ').title()}")
        print(f"   {item['explicacao']}")
        print(f"   Ganho apenas previsto: +{item['ganho_previsto']:.1f}; risco: {item['risco']}")


def gerenciar_dados(usuario: dict, caminho_banco: str | Path = DB_PATH) -> tuple[dict | None, bool]:
    titulo("PRIVACIDADE E DADOS")
    print(f"Consentimento Gemini: {'ATIVO' if usuario['consentimento_api'] else 'DESATIVADO'}")
    print("  1. Alterar consentimento")
    print("  2. Exportar resumo")
    print("  3. Excluir perfil e todo o historico")
    print("  0. Voltar")
    escolha = solicitar_validado("Escolha: ", lambda v: validar_inteiro(v, 0, 3, "opcao"))
    if escolha == 1:
        novo = solicitar_validado("Autorizar Gemini? (sim/nao): ", normalizar_sim_nao)
        database.atualizar_consentimento(usuario["id"], bool(novo), caminho_banco)
        usuario = database.buscar_usuario(usuario["id"], caminho_banco)
        print("Preferencia atualizada.")
    elif escolha == 2:
        destino = exportar_resumo(usuario["id"], caminho_banco)
        print(f"Resumo exportado em: {destino}")
    elif escolha == 3:
        confirmacao = input(f"Digite EXCLUIR {usuario['apelido']} para confirmar: ").strip()
        if confirmacao == f"EXCLUIR {usuario['apelido']}":
            database.excluir_usuario(usuario["id"], caminho_banco)
            print("Perfil e historico excluidos permanentemente do banco local.")
            return None, True
        print("Exclusao cancelada.")
    return usuario, False


def exibir_menu(usuario: dict) -> None:
    chave = "configurada" if get_gemini_api_key() else "ausente"
    titulo("NEXTFRAME JOVI AI LENSLAB")
    print(f"Perfil: {usuario['apelido']} | Nivel: {usuario['nivel']} | Gemini: chave {chave}")
    print("  1. Trocar ou criar perfil")
    print("  2. Analisar fotografia")
    print("  3. Explorar simulacao 'E se?'")
    print("  4. Comparar antes e depois e aprender")
    print("  5. Marcar recomendacao para testar")
    print("  6. Ver historico")
    print("  7. Ver evolucao")
    print("  8. Receber orientacao sem foto")
    print("  9. Privacidade e dados")
    print("  0. Encerrar")


def main(caminho_banco: str | Path = DB_PATH) -> None:
    ensure_directories()
    database.inicializar_banco(caminho_banco)
    print("JOVI AI LensLab: um laboratorio para testar, medir e aprender fotografia.")
    usuario = selecionar_perfil(caminho_banco)
    if not usuario:
        print("Nenhum perfil selecionado. Ate logo!")
        return
    while True:
        exibir_menu(usuario)
        opcao = solicitar_validado("Escolha: ", lambda v: validar_inteiro(v, 0, 9, "opcao"))
        try:
            if opcao == 0:
                print("Sessao encerrada. Suas fotos nao foram armazenadas no banco.")
                return
            if opcao == 1:
                novo = selecionar_perfil(caminho_banco)
                if novo:
                    usuario = novo
            elif opcao == 2:
                executar_analise(usuario, caminho_banco)
            elif opcao == 3:
                explorar_simulacao(usuario, caminho_banco)
            elif opcao == 4:
                comparar_recaptura(usuario, caminho_banco)
            elif opcao == 5:
                marcar_conselho(usuario, caminho_banco)
            elif opcao == 6:
                mostrar_historico(usuario, caminho_banco)
            elif opcao == 7:
                print(formatar_evolucao(usuario["id"], caminho_banco))
            elif opcao == 8:
                recomendacao_sem_foto(usuario)
            elif opcao == 9:
                usuario, excluido = gerenciar_dados(usuario, caminho_banco)
                if excluido or usuario is None:
                    usuario = selecionar_perfil(caminho_banco)
                    if not usuario:
                        print("Nenhum perfil ativo. Ate logo!")
                        return
        except (ValueError, sqlite3.Error, OSError) as exc:
            print(f"Operacao nao concluida: {exc}")


if __name__ == "__main__":
    main()
