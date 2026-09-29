"""Regressões matemáticas do núcleo, sem Flask, banco ou serviços externos."""

import math
import statistics

import pytest

from core import LoteriaConfig, LoteriaType, ModeloCanonico30


def modelo_pequeno(historico, *, universo=4, sorteados=2, sorteios=1):
    config = LoteriaConfig(
        nome="Universo de teste",
        universo=universo,
        sorteados=sorteados,
        minimo_aposta=sorteados,
        maximo_aposta=universo,
        custo_minimo=0,
        dias_sorteio=[],
        faixas_premiacao=[],
        sorteios_por_concurso=sorteios,
    )
    return ModeloCanonico30(historico, LoteriaType.MEGA_SENA, config_override=config)


def test_frequencia_fr_e_harmonia_com_contagens_conhecidas():
    modelo = modelo_pequeno([[1, 2], [1, 2], [1, 2], [1, 3]])

    assert modelo.mu == 0.5
    assert modelo.contagens_total == {1: 4, 2: 3, 3: 1, 4: 0}
    assert [modelo.calcular_frequencia(n) for n in modelo.numeros] == [1, 0.75, 0.25, 0]
    assert [modelo.calcular_fr(n) for n in modelo.numeros] == [2, 1.5, 0.5, 0]
    assert [modelo.calcular_hi(n) for n in modelo.numeros] == [1, 0.5, 0.5, 1]
    assert sum(modelo.calcular_fr(n) for n in modelo.numeros) == pytest.approx(modelo.N)


def test_iseg_e_global_mesmo_quando_as_harmonias_sao_diferentes():
    modelo = modelo_pequeno([[1, 2], [1, 2], [1, 2], [1, 3]])
    # H = [1, 1/2, 1/2, 1]; 1 / (1 + H_medio) = 4/7.
    assert [modelo.calcular_iseg(n) for n in modelo.numeros] == pytest.approx([4 / 7] * 4)
    assert [a.iseg for a in modelo.analisar_todos_elementos()] == pytest.approx([4 / 7] * 4)


def test_entropia_usa_probabilidades_normalizadas_pela_quantidade_sorteada():
    modelo = modelo_pequeno([[1, 2], [1, 2], [1, 2], [1, 3]])
    esperado = -sum(p * math.log2(p) for p in (0.5, 0.375, 0.125))

    assert modelo.calcular_entropia() == pytest.approx(esperado)
    assert modelo.calcular_compressibilidade() == pytest.approx(1 - esperado / 2)


def test_distribuicao_uniforme_tem_entropia_maxima_e_compressibilidade_zero():
    modelo = modelo_pequeno([[1, 2], [3, 4]] * 10)

    assert modelo.calcular_entropia() == pytest.approx(math.log2(4))
    assert modelo.calcular_compressibilidade() == pytest.approx(0, abs=1e-12)
    assert all(modelo.calcular_iseg(n) == 1 for n in modelo.numeros)


def test_distribuicao_concentrada_tem_entropia_zero_e_compressibilidade_um():
    modelo = modelo_pequeno([[1]] * 20, sorteados=1)

    assert modelo.calcular_entropia() == 0
    assert modelo.calcular_compressibilidade() == 1


def test_universo_unitario_e_rejeitado_como_configuracao_degenerada():
    with pytest.raises(ValueError, match="Configuração inválida"):
        modelo_pequeno([[1]] * 20, universo=1, sorteados=1)


def test_entropia_lotofacil_nao_trata_frequencias_de_inclusao_como_probabilidades():
    modelo = ModeloCanonico30([list(range(1, 16))], LoteriaType.LOTOFACIL)

    assert modelo.calcular_entropia() == pytest.approx(math.log2(15))
    assert 0 <= modelo.calcular_entropia() <= math.log2(25)
    assert 0 <= modelo.calcular_compressibilidade() <= 1


@pytest.mark.parametrize("total", [1, 10, 19])
def test_ict_com_menos_de_vinte_concursos_sinaliza_amostra_insuficiente(total):
    modelo = modelo_pequeno([[1, 2]] * total)

    assert all(modelo.calcular_ict(n) == 1 for n in modelo.numeros)


@pytest.mark.parametrize("total,primeira_metade", [(20, 10), (21, 11)])
def test_ict_usa_frequencias_acumuladas_na_segunda_metade(total, primeira_metade):
    modelo = modelo_pequeno([[1, 2]] * primeira_metade + [[2, 3]] * (total - primeira_metade))
    # O número 1 deixa de ocorrer após a primeira metade; o acumulado permanece constante.
    frequencias = [primeira_metade / t for t in range(primeira_metade, total + 1)]
    esperado = statistics.pstdev(frequencias) / 0.5

    assert modelo.calcular_ict(1) == pytest.approx(esperado)
    assert modelo.calcular_ict(2) == 0
    assert modelo.calcular_ict(4) == 0


def test_ict_e_limitado_a_um():
    modelo = modelo_pequeno([[1]] * 10 + [[2]] * 10, universo=100, sorteados=1)

    assert modelo.calcular_ict(1) == 1


def test_ict_contabiliza_repeticoes_em_sorteios_independentes():
    modelo = modelo_pequeno([[1, 1]] * 10 + [[2, 2]] * 10, sorteados=1, sorteios=2)
    esperado = statistics.pstdev([20 / t for t in range(10, 21)]) / 0.5

    assert modelo.k == 2
    assert modelo.calcular_ict(1) == pytest.approx(esperado)


def test_ict_super_sete_contabiliza_ocorrencias_em_colunas_distintas():
    historico = [[0, 0, 1, 2, 3, 4, 5]] * 10 + [[1, 2, 3, 4, 5, 6, 7]] * 10
    modelo = ModeloCanonico30(historico, LoteriaType.SUPER_SETE)
    esperado = statistics.pstdev([20 / t for t in range(10, 21)]) / 0.7

    assert modelo.calcular_ict(0) == pytest.approx(esperado)


def test_gamma_e_razao_de_variancias_sem_elevar_a_razao_ao_quadrado():
    modelo = modelo_pequeno([[1, 2]] * 100 + [[1, 3]] * 100)
    # f(T) = [1, 1/2, 1/2, 0], f(W1) = [1, 0, 1, 0]: razão = 2.
    assert modelo.calcular_gamma() == pytest.approx(2)
    assert modelo.calcular_gamma() == pytest.approx(2)  # Resultado permanece igual com cache.
    status = modelo.obter_status_mcp()
    assert status["disponivel"] is True
    assert status["gamma"] == pytest.approx(2)


def test_imc_usa_janelas_de_cem_e_cento_e_cinquenta_concursos():
    modelo = modelo_pequeno([[1, 2]] * 100 + [[1, 3]] * 100)

    assert (modelo.W1, modelo.W2) == (100, 150)
    assert modelo.calcular_imc(1) == 0
    assert modelo.calcular_imc(2) == pytest.approx(-5 / 6)
    assert modelo.calcular_imc(3) == pytest.approx(5 / 6)
    assert modelo.calcular_imc(4) == 0


@pytest.mark.parametrize("total", [1, 19, 100, 149])
def test_mcp_indisponivel_antes_de_completar_janela_media(total):
    modelo = modelo_pequeno([[1, 2]] * total)
    status = modelo.obter_status_mcp()

    assert {"disponivel", "status", "motivo", "gamma"} <= status.keys()
    assert status["disponivel"] is False
    assert status["status"]
    assert status["motivo"]
    assert status["gamma"] is None
    assert modelo.calcular_gamma() == 0
    for numero in modelo.numeros:
        assert modelo.calcular_score_mcp(numero) == modelo.calcular_illa(numero)


def test_mcp_disponivel_exatamente_no_limite_da_janela_media():
    modelo = modelo_pequeno([[1, 2]] * 150)

    assert modelo.obter_status_mcp()["disponivel"] is True
    assert modelo.calcular_gamma() == pytest.approx(1)


def test_variancia_historica_zero_desativa_mcp_mesmo_com_janela_recente_desigual():
    modelo = modelo_pequeno([[1, 2]] * 100 + [[3, 4]] * 100)
    status = modelo.obter_status_mcp()

    assert status["disponivel"] is False
    assert status["gamma"] is None
    assert status["motivo"]
    assert modelo.calcular_gamma() == 0
    assert any(modelo.calcular_imc(n) != 0 for n in modelo.numeros)
    for numero in modelo.numeros:
        assert modelo.calcular_score_mcp(numero) == modelo.calcular_illa(numero)


def test_variancia_recente_zero_produz_gamma_zero_valido():
    modelo = modelo_pequeno([[1, 2]] * 50 + [[1, 2], [3, 4]] * 50)

    assert modelo.obter_status_mcp()["disponivel"] is True
    assert modelo.obter_status_mcp()["gamma"] == 0
    assert modelo.calcular_gamma() == 0
    for numero in modelo.numeros:
        assert modelo.calcular_score_mcp(numero) == modelo.calcular_illa(numero)


def test_classes_usam_quartis_inclusivos_da_distribuicao(monkeypatch):
    modelo = modelo_pequeno([[1, 2]] * 20)
    valores = {1: 0.01, 2: 0.02, 3: 0.03, 4: 0.04}
    monkeypatch.setattr(modelo, "calcular_ict", valores.__getitem__)

    assert [modelo.classificar_elemento(v) for v in valores.values()] == ["A", "B", "C", "D"]
    # Cortes inclusivos: 0.0175, 0.025, 0.0325; diferem de cortes fixos ou exclusivos.
    assert modelo.classificar_elemento(0.015) == "A"
    assert modelo.classificar_elemento(0.02) == "B"
    assert modelo.classificar_elemento(0.03) == "C"
    assert modelo.classificar_elemento(0.035) == "D"


@pytest.mark.parametrize("valores", [[0.1, 0.1, 0.2, 0.2], [0.3, 0.3, 0.3, 0.3]])
def test_empates_de_ict_nao_sao_separados_em_classes_distintas(monkeypatch, valores):
    modelo = modelo_pequeno([[1, 2]] * 20)
    por_numero = dict(zip(modelo.numeros, valores))
    monkeypatch.setattr(modelo, "calcular_ict", por_numero.__getitem__)
    analises = modelo.analisar_todos_elementos()

    for valor in set(valores):
        assert len({a.classe for a in analises if a.ict == valor}) == 1


@pytest.mark.parametrize(
    "historico",
    [
        [],
        [[1]],
        [[1, 2, 3]],
        [[0, 1]],
        [[1, 5]],
        [[1, 1]],
        [[1, 2.5]],
        [[1, True]],
        [[1, None]],
        [[1, "2.5"]],
    ],
)
def test_historicos_invalidos_sao_rejeitados(historico):
    with pytest.raises(ValueError):
        modelo_pequeno(historico)


def test_normaliza_strings_numericas_sem_truncar_numeros():
    modelo = modelo_pequeno([["01", "02"], [3, 4.0]])

    assert modelo.historico == [[1, 2], [3, 4]]
    assert all(type(n) is int for concurso in modelo.historico for n in concurso)


def test_dicionarios_sao_ordenados_pelo_numero_do_concurso_sem_mutar_entrada():
    historico = [
        {"concurso": "10", "numeros": ["3", "4"]},
        {"concurso": "2", "dezenas": ["1", "3"]},
        {"concurso": "1", "numeros": ["1", "2"]},
    ]
    modelo = modelo_pequeno(historico)

    assert modelo.historico == [[1, 2], [1, 3], [3, 4]]
    assert [c["concurso"] for c in historico] == ["10", "2", "1"]
    assert historico[0]["numeros"] == ["3", "4"]


def test_ordem_de_dicionarios_nao_altera_janelas_nem_indicadores():
    historico = [
        {"concurso": str(n), "numeros": [1, 2] if n <= 100 else [1, 3]}
        for n in range(1, 201)
    ]
    modelo = modelo_pequeno(historico)
    invertido = modelo_pequeno(list(reversed(historico)))

    assert invertido.historico == modelo.historico
    assert invertido.contagens_W1 == modelo.contagens_W1
    assert invertido.contagens_W2 == modelo.contagens_W2
    assert invertido.obter_resumo_analise() == modelo.obter_resumo_analise()


@pytest.mark.parametrize("segundo_concurso", [1, "01", "invalido", 1.5, True])
def test_identificadores_duplicados_ou_invalidos_sao_rejeitados(segundo_concurso):
    historico = [
        {"concurso": 1, "numeros": [1, 2]},
        {"concurso": segundo_concurso, "numeros": [3, 4]},
    ]
    with pytest.raises(ValueError):
        modelo_pequeno(historico)


def test_listas_sem_metadados_preservam_ordem_cronologica_fornecida():
    historico = [[3, 4], [1, 2], [1, 3]]

    assert modelo_pequeno(historico).historico == historico


@pytest.mark.parametrize("duplo", [False, True])
def test_dupla_sena_aceita_um_ou_dois_sorteios_por_concurso(duplo):
    numeros = list(range(1, 7)) * (2 if duplo else 1)
    modelo = ModeloCanonico30([numeros] * 20, LoteriaType.DUPLA_SENA)

    assert modelo.k == (12 if duplo else 6)
    assert modelo.contagens_total[1] == (40 if duplo else 20)
    assert modelo.calcular_frequencia(1) == (2 if duplo else 1)
    assert modelo.calcular_fr(1) == pytest.approx(50 / 6)
    assert sum(modelo.calcular_fr(n) for n in modelo.numeros) == pytest.approx(50)


def test_dupla_sena_rejeita_mistura_de_concursos_simples_e_duplos():
    with pytest.raises(ValueError):
        ModeloCanonico30([list(range(1, 7)), list(range(1, 7)) * 2], LoteriaType.DUPLA_SENA)


@pytest.mark.parametrize(
    "numeros",
    [
        list(range(1, 8)),
        list(range(1, 12)),
        list(range(1, 14)),
        [1, 1, 3, 4, 5, 6],
        [1, 1, 3, 4, 5, 6] + list(range(1, 7)),
        list(range(1, 7)) + [1, 1, 3, 4, 5, 6],
    ],
)
def test_dupla_sena_exige_quantidade_valida_e_unicidade_em_cada_sorteio(numeros):
    with pytest.raises(ValueError):
        ModeloCanonico30([numeros], LoteriaType.DUPLA_SENA)


def test_super_sete_aceita_zero_e_repeticao_entre_colunas():
    modelo = ModeloCanonico30([[0] * 7] * 20, LoteriaType.SUPER_SETE)

    assert modelo.contagens_total[0] == 140
    assert modelo.calcular_frequencia(0) == 7
    assert modelo.calcular_fr(0) == 10
    assert modelo.calcular_entropia() == 0
    assert modelo.calcular_compressibilidade() == 1
    assert {a.numero for a in modelo.analisar_todos_elementos()} == set(range(10))


@pytest.mark.parametrize("numeros", [[0] * 6, [0] * 8, [0, 1, 2, 3, 4, 5, 10]])
def test_super_sete_exige_sete_digitos_validos(numeros):
    with pytest.raises(ValueError):
        ModeloCanonico30([numeros], LoteriaType.SUPER_SETE)


def test_lotomania_preserva_numero_zero_no_universo_e_na_analise():
    modelo = ModeloCanonico30([list(range(20)), list(range(80, 100))], LoteriaType.LOTOMANIA)
    analises = {a.numero: a for a in modelo.analisar_todos_elementos()}

    assert modelo.numeros == list(range(100))
    assert analises[0].contagem_total == 1
    assert analises[99].contagem_total == 1
    assert analises[0].fr == pytest.approx(2.5)
    assert modelo.calcular_entropia() == pytest.approx(math.log2(40))


def test_lotomania_rejeita_cem_fora_do_universo():
    with pytest.raises(ValueError):
        ModeloCanonico30([list(range(1, 20)) + [100]], LoteriaType.LOTOMANIA)
