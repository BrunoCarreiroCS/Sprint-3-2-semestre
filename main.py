"""Interface textual do NextFrame JOVI AI LensLab."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import database
from analysis_service import analisar_fotografia
from config import (
    DB_PATH,
    ROOT_DIR,
    SAMPLES_DIR,
    SUPPORTED_IMAGE_EXTENSIONS,
    ensure_directories,
    get_gemini_api_key,
    is_demo_mode,
)
from gemini_client import analisar_com_gemini, analisar_com_gemini_demo
from image_analyzer import calcular_hash, gerar_simulacao
from learning_engine import comparar_e_aprender
from recommendation_engine import recomendar_sem_foto
from reports import (
    exportar_resumo,
    formatar_analise,
    formatar_comparacao,
    formatar_evolucao,
    formatar_resumo_analise,
    formatar_resumo_comparacao,
)
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

ULTIMO_OBJETIVO: dict[int, str] = {}


def titulo(texto: str) -> None:
    print("\n" + "=" * 68)
    print(texto.center(68))
    print("=" * 68)


def escolher_rotulada(
    rotulo: str, opcoes: list[str], cancelar: bool = True, padrao: str | None = None
) -> str | None:
    print(f"\n{rotulo}:")
    for indice, opcao in enumerate(opcoes, 1):
        marca = "  <- Enter repete" if opcao == padrao else ""
        print(f"  {indice}. {opcao.replace('_', ' ').title()}{marca}")
    if cancelar:
        print("  0. Cancelar")
    minimo = 0 if cancelar else 1
    indice_padrao = opcoes.index(padrao) + 1 if padrao in opcoes else None
    numero = solicitar_validado(
        "Escolha: ", lambda valor: validar_inteiro(valor, minimo, len(opcoes), "opcao"), padrao=indice_padrao
    )
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


def listar_imagens_disponiveis() -> list[Path]:
    if not SAMPLES_DIR.exists():
        return []
    return sorted(p for p in SAMPLES_DIR.iterdir() if p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS)


def abrir_seletor_arquivo() -> Path | None:
    """Abre o explorador de arquivos do Windows para escolher uma foto (requer tkinter)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("Explorador de arquivos indisponivel: este Python foi instalado sem tkinter.")
        return None
    try:
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        caminho_selecionado = filedialog.askopenfilename(
            title="Selecione uma fotografia",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp"), ("Todos os arquivos", "*.*")],
        )
        raiz.destroy()
    except tk.TclError as exc:
        print(f"Nao foi possivel abrir o explorador de arquivos: {exc}")
        return None
    if not caminho_selecionado:
        print("Nenhum arquivo selecionado.")
        return None
    try:
        return validar_caminho_imagem(caminho_selecionado)
    except ValidationError as exc:
        print(f"Entrada invalida: {exc}")
        return None


def escolher_imagem(mensagem: str = "Caminho da imagem") -> Path | None:
    """Abre o explorador de arquivos por padrao; tambem lista exemplos e aceita caminho digitado."""
    imagens = listar_imagens_disponiveis()
    print(f"\n{mensagem}:")
    print("  1. Abrir explorador de arquivos  <- Enter")
    for indice, caminho in enumerate(imagens, 2):
        print(f"  {indice}. {caminho.relative_to(ROOT_DIR)}")
    opcao_manual = len(imagens) + 2
    print(f"  {opcao_manual}. Digitar outro caminho")
    print("  0. Cancelar")
    numero = solicitar_validado(
        "Escolha: ", lambda v: validar_inteiro(v, 0, opcao_manual, "opcao"), padrao=1
    )
    if numero == 0:
        return None
    if numero == 1:
        return abrir_seletor_arquivo()
    if numero == opcao_manual:
        return solicitar_validado(f"{mensagem} (0 cancela): ", validar_caminho_imagem, True)
    try:
        return validar_caminho_imagem(imagens[int(numero) - 2])
    except ValidationError as exc:
        print(f"Entrada invalida: {exc}")
        return None


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
    quer_tour = solicitar_validado(
        "Deseja ver um tour rapido com uma foto de exemplo agora? (sim/nao): ", normalizar_sim_nao
    )
    if quer_tour:
        executar_tour_guiado(usuario, caminho_banco)
    return usuario


def executar_tour_guiado(usuario: dict, caminho_banco: str | Path = DB_PATH) -> None:
    """Roda uma analise completa com uma foto de exemplo, sem pedir nenhuma entrada extra."""
    titulo("TOUR GUIADO")
    exemplo = SAMPLES_DIR / "exemplo_escuro.jpg"
    if not exemplo.exists():
        print("Nenhuma imagem de exemplo encontrada; use a opcao 2 do menu quando quiser.")
        return
    print("Vamos analisar uma foto de exemplo escura para voce ver o diagnostico completo.")
    cliente_ia = analisar_com_gemini_demo if is_demo_mode() else analisar_com_gemini
    try:
        resultado = analisar_fotografia(
            usuario, exemplo, "retrato", "Conhecer o JOVI AI LensLab", usuario["estilo_preferido"],
            bool(usuario["consentimento_api"]), caminho_banco, cliente_ia,
        )
    except ValidationError as exc:
        print(f"Nao foi possivel rodar o tour: {exc}")
        return
    print(formatar_analise(resultado))
    print("\nEsse foi um exemplo completo do ciclo medir -> interpretar -> simular.")
    print("Use a opcao 2 do menu quando quiser analisar suas proprias fotos.")


def descricao_perfil(usuario: dict) -> str:
    return f"{usuario['apelido']} ({usuario['nivel']}, {usuario['estilo_preferido']})"


def selecionar_perfil(caminho_banco: str | Path = DB_PATH) -> dict | None:
    titulo("SELECIONAR PERFIL")
    usuarios = database.listar_usuarios(caminho_banco)
    if not usuarios:
        print("Ainda nao ha perfis. Vamos criar o primeiro.")
        return criar_perfil(caminho_banco)
    print("  1. Selecionar perfil existente")
    print("  2. Criar novo perfil")
    print("  3. Excluir perfil")
    print("  0. Cancelar")
    escolha = solicitar_validado("Escolha: ", lambda v: validar_inteiro(v, 0, 3, "opcao"))
    if escolha == 0:
        return None
    if escolha == 2:
        return criar_perfil(caminho_banco)
    if escolha == 3:
        excluir_perfil(usuarios, caminho_banco)
        return selecionar_perfil(caminho_banco)
    return escolher_registro(usuarios, descricao_perfil, "perfil")


def excluir_perfil(usuarios: list[dict], caminho_banco: str | Path = DB_PATH) -> None:
    titulo("EXCLUIR PERFIL")
    usuario = escolher_registro(usuarios, descricao_perfil, "perfil")
    if not usuario:
        return
    confirmacao = input(
        f"Digite EXCLUIR {usuario['apelido']} para confirmar (apaga todo o historico deste perfil): "
    ).strip()
    if confirmacao != f"EXCLUIR {usuario['apelido']}":
        print("Exclusao cancelada.")
        return
    database.excluir_usuario(usuario["id"], caminho_banco)
    print(f"Perfil {usuario['apelido']} e todo o historico foram excluidos.")


def executar_analise(
    usuario: dict,
    caminho_banco: str | Path = DB_PATH,
    contexto: dict | None = None,
    oferecer_proximo_passo: bool = True,
) -> dict | None:
    titulo("ANALISAR FOTOGRAFIA")
    caminho = escolher_imagem("Caminho da imagem")
    if caminho is None:
        return None
    objetivo = contexto["objetivo"] if contexto else escolher_rotulada(
        "Objetivo", OBJETIVOS, padrao=ULTIMO_OBJETIVO.get(usuario["id"])
    )
    if objetivo is None:
        return None
    if not contexto:
        ULTIMO_OBJETIVO[usuario["id"]] = objetivo
    intencao = contexto["intencao"] if contexto else solicitar_validado(
        "Qual era sua intencao com a foto? (0 cancela): ", lambda v: validar_texto(v, "intencao", 3, 160), True
    )
    if intencao is None:
        return None
    estilo = contexto["estilo"] if contexto else usuario["estilo_preferido"]
    permitir_api = bool(usuario["consentimento_api"])
    if permitir_api and not get_gemini_api_key() and not is_demo_mode():
        print("Aviso: GEMINI_API_KEY nao configurada; o modo offline sera usado.")
    cliente_ia = analisar_com_gemini_demo if is_demo_mode() else analisar_com_gemini
    print("Analisando sem alterar a fotografia original...")
    try:
        resultado = analisar_fotografia(
            usuario, caminho, str(objetivo), str(intencao), str(estilo), permitir_api, caminho_banco, cliente_ia
        )
    except ValidationError as exc:
        print(f"Nao foi possivel analisar: {exc}")
        return None
    print(formatar_resumo_analise(resultado))
    quer_detalhes = solicitar_validado(
        "\nVer detalhes tecnicos completos (metricas, IA, todas as recomendacoes)? (sim/nao): ", normalizar_sim_nao
    )
    if quer_detalhes:
        print(formatar_analise(resultado))
    resultado["caminho_original"] = str(caminho)
    recomendacoes = resultado.get("recomendacoes") or []
    tem_recomendacao_real = bool(recomendacoes) and recomendacoes[0]["codigo_acao"] != "manter_configuracao"
    if oferecer_proximo_passo and tem_recomendacao_real:
        oferecer_marcar_recomendacao(usuario, resultado, caminho_banco)
    return resultado


def oferecer_marcar_recomendacao(usuario: dict, resultado: dict, caminho_banco: str | Path = DB_PATH) -> None:
    quer = solicitar_validado(
        "\nDeseja marcar uma destas recomendacoes para testar agora? (sim/nao): ", normalizar_sim_nao
    )
    if not quer:
        return
    recomendacao = selecionar_recomendacao(resultado["analise_id"], caminho_banco)
    if recomendacao:
        database.marcar_recomendacao(recomendacao["id"], resultado["analise_id"], caminho_banco)
        print("Recomendacao registrada. Depois use 'Comparar antes e depois' para verificar o resultado.")


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
    caminho = escolher_imagem("Informe novamente a foto original")
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
    antes = None
    recomendacao = None
    pendente = database.buscar_recomendacao_pendente(usuario["id"], caminho_banco)
    if pendente:
        print(
            f"Voce marcou '{pendente['codigo_acao'].replace('_', ' ').title()}' "
            f"na foto {pendente['nome_arquivo']} para testar."
        )
        usar_pendente = solicitar_validado(
            "Foi essa recomendacao que voce aplicou? (sim/nao): ", normalizar_sim_nao, padrao=True
        )
        if usar_pendente:
            antes = database.buscar_analise(pendente["analise_id"], caminho_banco)
            recomendacao = pendente
    if antes is None:
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
        oferecer_proximo_passo=False,
    )
    if not resultado_depois:
        return
    avaliacao = solicitar_validado(
        "Quanto a recomendacao ajudou? (1 a 5, 0 cancela): ",
        lambda v: validar_inteiro(v, 1, 5, "avaliacao"),
        True,
    )
    if avaliacao is None:
        print("Avaliacao cancelada. A recaptura ficou salva no historico, mas o aprendizado nao foi atualizado.")
        return
    comentario = input("Comentario opcional: ").strip()[:500]
    try:
        comparacao = comparar_e_aprender(
            usuario["id"], antes["id"], resultado_depois["analise_id"],
            recomendacao["id"], int(avaliacao), comentario, caminho_banco,
        )
    except ValueError as exc:
        print(f"Comparacao recusada: {exc}")
        return
    print(formatar_resumo_comparacao(comparacao))
    quer_detalhes = solicitar_validado(
        "\nVer detalhes tecnicos completos (mudanca por dimensao, peso aprendido)? (sim/nao): ", normalizar_sim_nao
    )
    if quer_detalhes:
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
    chave = "demo" if is_demo_mode() else ("configurada" if get_gemini_api_key() else "ausente")
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
