"""Validação fora da amostra do ranking MCP-MD.

Este módulo avalia uma regra de seleção previamente definida; não é um teste
geral de equiprobabilidade nem prova de vantagem futura. A especificação
consolidada fornece cinco critérios, mas não define a estatística, o prior ou
o protocolo dos blocos. As escolhas abaixo são operacionais e explícitas.

H0: concursos independentes, uniformes e sem reposição em cada sorteio.
H1: inclinação exponencial positiva da distribuição de acertos sob H0, com
um único theta, compartilhado pelos concursos, e prior discreto uniforme.

Referências das fórmulas:
https://stat.ethz.ch/R-manual/R-devel/library/stats/html/Hypergeometric.html
https://www.stat.berkeley.edu/~wfithian/courses/stat210a/exponentialTilt.nb.html
"""

import math
import random
import statistics
import sys
from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core import ModeloCanonico30


TREINO_MINIMO = 150
MAX_BLOCOS = 3
THETAS_ALTERNATIVA = (0.10, 0.25, 0.50, 1.00)
SEMENTE_MONTE_CARLO = 20260929


def _inteiro_positivo(valor: int, nome: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValueError(f"{nome} deve ser um inteiro positivo")


def _distribuicao_hipergeometrica(N: int, m: int, k: int) -> Dict[int, float]:
    """P(X=x)=C(m,x) C(N-m,k-x)/C(N,k), incluindo população finita."""
    if not (N > 0 and 0 <= m <= N and 0 <= k <= N):
        raise ValueError("Parâmetros hipergeométricos inválidos")
    denominador = math.comb(N, k)
    probabilidades = {
        x: math.comb(m, x) * math.comb(N - m, k - x) / denominador
        for x in range(max(0, k - (N - m)), min(k, m) + 1)
    }
    total = math.fsum(probabilidades.values())
    return {x: p / total for x, p in probabilidades.items()}


def _convoluir_distribuicoes(
    primeira: Dict[int, float], segunda: Dict[int, float]
) -> Dict[int, float]:
    resultado: Dict[int, float] = {}
    for x, px in primeira.items():
        for y, py in segunda.items():
            resultado[x + y] = resultado.get(x + y, 0.0) + px * py
    total = math.fsum(resultado.values())
    return {x: p / total for x, p in sorted(resultado.items())}


def _log_soma_exp(valores: List[float]) -> float:
    maior = max(valores)
    return maior + math.log(math.fsum(math.exp(v - maior) for v in valores))


class ValidaçãoCamada7:
    """Monte Carlo, BF10 e Z sobre os mesmos acertos de walk-forward.

    O ranking é treinado no prefixo histórico e congelado para o próximo
    bloco. Depois, o prefixo cresce, incorporando somente blocos já passados.
    Avaliam-se até os três últimos blocos completos, de 50 concursos por
    padrão. Nenhum hiperparâmetro é escolhido pelo resultado do teste.
    """

    def __init__(self, modelo: "ModeloCanonico30"):
        self.modelo = modelo
        self._backtests: Dict[int, Dict] = {}

    def _inconclusivo(self, mensagem: str, **campos) -> Dict:
        return {"status": "inconclusivo", "disponivel": False, "erro": mensagem, **campos}

    def _contexto_nulo(self) -> Dict:
        modelo = self.modelo
        config = modelo.config
        N = modelo.N
        if N <= 1:
            raise ValueError("Universo insuficiente para avaliar desempenho da seleção")

        if config.colunas:
            m, k, repeticoes = 1, 1, config.colunas
            tamanho_concurso = config.colunas
        else:
            m, k = min(10, N - 1), config.sorteados
            tamanho_concurso = len(modelo.historico[0]) if modelo.historico else k
            if config.sorteios_por_concurso > 1 and tamanho_concurso == k * config.sorteios_por_concurso:
                repeticoes = config.sorteios_por_concurso
            elif tamanho_concurso == k:
                repeticoes = 1
            else:
                raise ValueError("Histórico com quantidade de dezenas incompatível com a modalidade")

        universo = set(modelo.numeros)
        for concurso in modelo.historico:
            if len(concurso) != tamanho_concurso or any(n not in universo for n in concurso):
                raise ValueError("Histórico incompleto ou com números fora do universo")
            if not config.colunas:
                for inicio in range(0, tamanho_concurso, k):
                    sorteio = concurso[inicio:inicio + k]
                    if len(sorteio) != k or len(set(sorteio)) != k:
                        raise ValueError("Cada sorteio deve conter dezenas distintas")

        distribuicao_base = _distribuicao_hipergeometrica(N, m, k)
        distribuicao_concurso = {0: 1.0}
        for _ in range(repeticoes):
            distribuicao_concurso = _convoluir_distribuicoes(distribuicao_concurso, distribuicao_base)
        p = m / N
        media = repeticoes * k * p
        variancia = repeticoes * k * p * (1 - p) * (N - k) / (N - 1)
        if variancia <= 0:
            raise ValueError("Distribuição nula degenerada: o desempenho da seleção não pode ser testado")
        return {
            "universo": N,
            "selecionados_por_sorteio": m,
            "sorteados_por_sorteio": k,
            "sorteios_independentes_por_concurso": repeticoes,
            "media_por_concurso": media,
            "variancia_por_concurso": variancia,
            "suporte": list(distribuicao_concurso),
            "probabilidades": list(distribuicao_concurso.values()),
        }

    @staticmethod
    def _status_mcp_treino(modelo: "ModeloCanonico30") -> Dict:
        # O método do núcleo também distingue histórico curto e gamma indefinido.
        if hasattr(modelo, "obter_status_mcp"):
            return modelo.obter_status_mcp()
        # Compatibilidade com modelos anteriores; não trata 0/0 como evidência.
        frequencias = [modelo.calcular_frequencia(n) for n in modelo.numeros]
        disponivel = modelo.T >= TREINO_MINIMO and statistics.pvariance(frequencias) > 0
        return {
            "disponivel": disponivel,
            "motivo": None if disponivel else "MCP-MD requer 150 concursos e dispersão histórica não nula",
        }

    def _selecionar_no_treino(self, historico_treino: List[List[int]]) -> Tuple[List[int], Dict]:
        # Importação local evita ciclo quando core reexporta esta classe pública.
        from core import ModeloCanonico30, modelos_por_coluna

        treino = ModeloCanonico30(
            historico_treino, self.modelo.loteria_type, config_override=self.modelo.config
        )
        modelos = modelos_por_coluna(treino) if treino.config.colunas else [treino]
        selecionados: List[int] = []
        for modelo in modelos:
            status = self._status_mcp_treino(modelo)
            if not status["disponivel"]:
                return [], status
            analises = modelo.analisar_todos_elementos()
            if any(not math.isfinite(a.score_mcp) for a in analises):
                return [], {"disponivel": False, "motivo": "Score MCP-MD não finito no treino"}
            quantidade = 1 if treino.config.colunas else min(10, modelo.N - 1)
            ranking = sorted(analises, key=lambda a: (-a.score_mcp, a.numero))
            selecionados.extend(a.numero for a in ranking[:quantidade])
        return selecionados, {"disponivel": True}

    def backtest(self, janela_teste: int = 50) -> Dict:
        """Walk-forward expansivo, preservando a ordem cronológica recebida.

        Persistência operacional: os três blocos disjuntos têm Z>0.
        Robustez operacional: Z acumulado>2 após o segundo e o terceiro
        blocos. Esses limites de blocos não são fórmulas fornecidas pelo
        documento canônico; são requisitos conservadores desta implementação.
        """
        _inteiro_positivo(janela_teste, "janela_teste")
        if janela_teste in self._backtests:
            return self._backtests[janela_teste]
        quantidade_blocos = min(MAX_BLOCOS, max(0, (self.modelo.T - TREINO_MINIMO) // janela_teste))
        if quantidade_blocos == 0:
            resultado = self._inconclusivo(
                f"Histórico insuficiente: requer ao menos {TREINO_MINIMO + janela_teste} concursos",
                janela_teste=janela_teste, concursos_teste=0, blocos=[], z_acumulado=None,
                persistencia_blocos=False, walk_forward_robusto=False,
            )
            self._backtests[janela_teste] = resultado
            return resultado
        try:
            nula = self._contexto_nulo()
        except ValueError as exc:
            return self._inconclusivo(str(exc), blocos=[], z_acumulado=None,
                                     persistencia_blocos=False, walk_forward_robusto=False)

        inicio_avaliacao = self.modelo.T - quantidade_blocos * janela_teste
        blocos = []
        acertos_acumulados = 0
        for indice in range(quantidade_blocos):
            inicio = inicio_avaliacao + indice * janela_teste
            fim = inicio + janela_teste
            selecionados, status = self._selecionar_no_treino(self.modelo.historico[:inicio])
            if not status["disponivel"]:
                resultado = self._inconclusivo(
                    status.get("motivo") or "MCP-MD indisponível no treino",
                    janela_teste=janela_teste, concursos_teste=0, blocos=blocos,
                    bloco_indisponivel=indice + 1, z_acumulado=None,
                    persistencia_blocos=False, walk_forward_robusto=False,
                )
                self._backtests[janela_teste] = resultado
                return resultado
            teste = self.modelo.historico[inicio:fim]
            if self.modelo.config.colunas:
                acertos = sum(sum(n == escolhido for n, escolhido in zip(c, selecionados)) for c in teste)
            else:
                conjunto = set(selecionados)
                acertos = sum(sum(n in conjunto for n in c) for c in teste)

            esperado = janela_teste * nula["media_por_concurso"]
            variancia = janela_teste * nula["variancia_por_concurso"]
            acertos_acumulados += acertos
            z_acumulado = (acertos_acumulados - (indice + 1) * esperado) / math.sqrt((indice + 1) * variancia)
            blocos.append({
                "bloco": indice + 1,
                "treino_concursos": inicio,
                "inicio_teste": inicio + 1,
                "fim_teste": fim,
                "concursos_teste": janela_teste,
                "selecionados": selecionados,
                "selecao_por_coluna": bool(self.modelo.config.colunas),
                "acertos": acertos,
                "acertos_esperados": esperado,
                "variancia_nula": variancia,
                "z": (acertos - esperado) / math.sqrt(variancia),
                "z_acumulado": z_acumulado,
            })

        concursos_teste = quantidade_blocos * janela_teste
        total_sorteados = concursos_teste * nula["sorteados_por_sorteio"] * nula["sorteios_independentes_por_concurso"]
        esperado_total = concursos_teste * nula["media_por_concurso"]
        variancia_total = concursos_teste * nula["variancia_por_concurso"]
        taxa_esperada = esperado_total / total_sorteados
        taxa_acerto = acertos_acumulados / total_sorteados
        tres_blocos = quantidade_blocos == MAX_BLOCOS
        resultado = {
            "status": "calculado",
            "disponivel": True,
            "metodo": "walk_forward_blocos_expansivos",
            "janela_teste": janela_teste,
            "treino_minimo": TREINO_MINIMO,
            "maximo_blocos": MAX_BLOCOS,
            "concursos_teste": concursos_teste,
            "acertos": acertos_acumulados,
            "total_sorteados": total_sorteados,
            "taxa_acerto": taxa_acerto,
            "taxa_esperada": taxa_esperada,
            "performance_relativa": taxa_acerto / taxa_esperada,
            "acertos_esperados": esperado_total,
            "variancia_nula": variancia_total,
            "z_acumulado": (acertos_acumulados - esperado_total) / math.sqrt(variancia_total),
            "persistencia_blocos": tres_blocos and all(b["z"] > 0 for b in blocos),
            "walk_forward_robusto": tres_blocos and all(b["z_acumulado"] > 2 for b in blocos[1:]),
            "blocos": blocos,
            "distribuicao_nula": nula,
            "criterios_operacionais": {
                "persistencia": "Ganho (Z>0) nos três blocos disjuntos",
                "robustez": "Z acumulado>2 em cada avaliação a partir do segundo bloco",
                "selecao": "Top min(10,N-1) por score MCP; um dígito por coluna no Super Sete",
            },
        }
        self._backtests[janela_teste] = resultado
        return resultado

    def teste_monte_carlo(
        self, simulacoes: int = 10000, semente: int = SEMENTE_MONTE_CARLO, janela_teste: int = 50
    ) -> Dict:
        """Simula a mesma soma de acertos do backtest sob H0, com RNG local."""
        _inteiro_positivo(simulacoes, "simulacoes")
        teste = self.backtest(janela_teste)
        if not teste["disponivel"]:
            return self._inconclusivo(teste["erro"], simulacoes=simulacoes, percentil=None,
                                     significativo=False, semente=semente)
        nula = teste["distribuicao_nula"]
        rng = random.Random(semente)
        acumuladas, soma = [], 0.0
        for p in nula["probabilidades"]:
            soma += p
            acumuladas.append(soma)
        observados = teste["acertos"]
        excedencias = 0
        soma_simulada = 0
        for _ in range(simulacoes):
            simulado = sum(rng.choices(nula["suporte"], cum_weights=acumuladas,
                                      k=teste["concursos_teste"]))
            soma_simulada += simulado
            excedencias += simulado >= observados
        p_cauda = (excedencias + 1) / (simulacoes + 1)
        return {
            "status": "calculado",
            "disponivel": True,
            "simulacoes": simulacoes,
            "semente": semente,
            "estatistica": "acertos_acumulados",
            "acertos_observados": observados,
            "media_simulada": soma_simulada / simulacoes,
            "excedencias": excedencias,
            "percentil": p_cauda,
            "p_cauda_superior": p_cauda,
            "resolucao": 1 / (simulacoes + 1),
            "significativo": p_cauda < 0.01,
            "metodo": "Soma de acertos hipergeométricos; p=(b+1)/(M+1), empates incluídos",
        }

    def analise_bayesiana(self, janela_teste: int = 50) -> Dict:
        """BF10 exato para o prior discreto declarado, calculado em log.

        p_theta(x)=p0(x) exp(theta*x)/M0(theta). Para n concursos e
        S acertos, L_theta/L0=exp(theta*S-n*log(M0(theta))). O BF10
        é a média desses quocientes sob o prior fixado antes do teste.
        """
        teste = self.backtest(janela_teste)
        if not teste["disponivel"]:
            return self._inconclusivo(teste["erro"], bayes_factor=None,
                                     log_bayes_factor=None, evidencia_forte=False)
        nula = teste["distribuicao_nula"]
        quocientes_log = []
        for theta in THETAS_ALTERNATIVA:
            log_normalizador = _log_soma_exp([
                math.log(p) + theta * x
                for x, p in zip(nula["suporte"], nula["probabilidades"]) if p > 0
            ])
            quocientes_log.append(theta * teste["acertos"] - teste["concursos_teste"] * log_normalizador)
        log_bf = _log_soma_exp(quocientes_log) - math.log(len(THETAS_ALTERNATIVA))
        limitado = log_bf > math.log(sys.float_info.max)
        bf = sys.float_info.max if limitado else math.exp(log_bf)
        return {
            "status": "calculado",
            "disponivel": True,
            "bayes_factor": bf,
            "log_bayes_factor": log_bf,
            "bayes_factor_limitado": limitado,
            "evidencia_forte": log_bf > math.log(10),
            "orientacao": "BF10 = P(acertos | H1) / P(acertos | H0)",
            "hipotese_nula": "Concursos independentes e uniformes; acertos hipergeométricos por sorteio",
            "hipotese_alternativa": "Inclinação exponencial positiva da distribuição nula de acertos; theta comum",
            "prior_theta": {"valores": list(THETAS_ALTERNATIVA), "pesos": [1 / len(THETAS_ALTERNATIVA)] * len(THETAS_ALTERNATIVA)},
            "escolha_operacional": "Prior fixo de implementação, não definido pelo documento canônico; resultado depende desse prior",
        }

    def validacao_completa(
        self, simulacoes: int = 10000, semente: int = SEMENTE_MONTE_CARLO
    ) -> Dict:
        """Exige os cinco critérios simultaneamente, sem converter ausência em prova."""
        backtest = self.backtest()
        monte_carlo = self.teste_monte_carlo(simulacoes=simulacoes, semente=semente)
        bayesiana = self.analise_bayesiana()
        criterios = {
            "z_acumulado": backtest.get("z_acumulado") is not None and backtest["z_acumulado"] > 2,
            "bayes_factor": bayesiana["evidencia_forte"],
            "monte_carlo": monte_carlo["significativo"],
            "persistencia_blocos": backtest["persistencia_blocos"],
            "walk_forward": backtest["walk_forward_robusto"],
        }
        completo = backtest["disponivel"] and len(backtest["blocos"]) == MAX_BLOCOS
        valido = completo and all(criterios.values())
        if not completo:
            status = "inconclusivo"
            conclusao = "MCP-MD inconclusivo: requer treino disponível e três blocos completos de validação."
        elif valido:
            status = "criterios_atendidos"
            conclusao = "Critérios operacionais do MCP-MD atendidos neste recorte; requer replicação independente."
        else:
            status = "nao_validado"
            conclusao = "Critérios do MCP-MD não atendidos neste recorte; isso não demonstra ausência de estrutura."
        return {
            "status": status,
            "monte_carlo": monte_carlo,
            "bayesiana": bayesiana,
            "backtest": backtest,
            "criterios": criterios,
            "validacao_mcp_md": valido,
            "conclusao": conclusao,
            "limites": [
                "Avalia somente o ranking MCP-MD e o recorte declarado; não testa toda forma de desvio da equiprobabilidade.",
                "Os blocos de teste não se sobrepõem; independência dos acertos pressupõe H0 de concursos independentes.",
                "Janelas, regra de seleção, prior e critérios operacionais dos blocos são escolhas locais explícitas.",
                "Repetir análises, escolher modalidades ou ajustar parâmetros após ver resultados exige controle de testes múltiplos.",
                "Os critérios usam os mesmos dados e não constituem cinco evidências estatísticas independentes.",
                "Resultado histórico não garante vantagem futura nem substitui replicação em dados novos.",
            ],
        }
