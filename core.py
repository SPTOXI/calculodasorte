"""
Sistema de Análise Estatística para Loterias - Modelo Canônico 3.0 + MCP-MD 1.0
AGENTE LLN ICT FR - Lei dos Grandes Números, Índice de Convergência Temporal, Fator de Recorrência
"""

import math
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class LoteriaType(Enum):
    MEGA_SENA = "mega_sena"
    QUINA = "quina"
    LOTOFACIL = "lotofacil"
    LOTOMANIA = "lotomania"
    MAIS_MILIONARIA = "mais_milionaria"
    DIA_DE_SORTE = "dia_de_sorte"
    SUPER_SETE = "super_sete"
    TIMEMANIA = "timemania"
    DUPLA_SENA = "dupla_sena"


@dataclass
class LoteriaConfig:
    """Configuração de cada loteria"""
    nome: str
    universo: int  # N - tamanho do universo
    sorteados: int  # k - quantidade sorteada por concurso
    minimo_aposta: int
    maximo_aposta: int
    custo_minimo: float
    dias_sorteio: List[str]
    faixas_premiacao: List[int]
    numero_inicial: int = 1  # Lotomania (00-99) e Super Sete (0-9) começam em 0
    sorteios_por_concurso: int = 1  # Dupla Sena tem 2 sorteios por concurso
    colunas: int = 0  # Super Sete: 7 colunas independentes, um dígito por coluna

    @property
    def numero_final(self) -> int:
        return self.numero_inicial + self.universo - 1

    @property
    def numeros(self) -> List[int]:
        return list(range(self.numero_inicial, self.numero_inicial + self.universo))


# Configurações das loterias brasileiras
LOTERIAS_CONFIG = {
    LoteriaType.MEGA_SENA: LoteriaConfig(
        nome="Mega-Sena",
        universo=60,
        sorteados=6,
        minimo_aposta=6,
        maximo_aposta=20,
        custo_minimo=6.0,
        dias_sorteio=["terça", "quinta", "domingo"],
        faixas_premiacao=[4, 5, 6]
    ),
    LoteriaType.QUINA: LoteriaConfig(
        nome="Quina",
        universo=80,
        sorteados=5,
        minimo_aposta=5,
        maximo_aposta=15,
        custo_minimo=3.0,
        dias_sorteio=["segunda", "terça", "quarta", "quinta", "sexta", "domingo"],
        faixas_premiacao=[2, 3, 4, 5]
    ),
    LoteriaType.LOTOFACIL: LoteriaConfig(
        nome="Lotofácil",
        universo=25,
        sorteados=15,
        minimo_aposta=15,
        maximo_aposta=20,
        custo_minimo=3.5,
        dias_sorteio=["segunda", "terça", "quarta", "quinta", "sexta", "domingo"],
        faixas_premiacao=[11, 12, 13, 14, 15]
    ),
    LoteriaType.LOTOMANIA: LoteriaConfig(
        nome="Lotomania",
        universo=100,
        sorteados=20,
        minimo_aposta=50,
        maximo_aposta=50,
        custo_minimo=3.0,
        dias_sorteio=["segunda", "quarta", "sexta"],
        faixas_premiacao=[0, 15, 16, 17, 18, 19, 20],
        numero_inicial=0
    ),
    LoteriaType.MAIS_MILIONARIA: LoteriaConfig(
        nome="+Milionária",
        universo=50,
        sorteados=6,
        minimo_aposta=6,
        maximo_aposta=6,
        custo_minimo=6.0,
        dias_sorteio=["quarta", "domingo"],
        faixas_premiacao=list(range(1, 11))
    ),
    LoteriaType.DIA_DE_SORTE: LoteriaConfig(
        nome="Dia de Sorte",
        universo=31,
        sorteados=7,
        minimo_aposta=7,
        maximo_aposta=15,
        custo_minimo=2.5,
        dias_sorteio=["terça", "quinta", "domingo"],
        faixas_premiacao=[4, 5, 6, 7]
    ),
    LoteriaType.SUPER_SETE: LoteriaConfig(
        nome="Super Sete",
        universo=10,  # Cada coluna tem 0-9
        sorteados=7,
        minimo_aposta=7,
        maximo_aposta=7,
        custo_minimo=3.0,
        dias_sorteio=["segunda", "quarta", "sexta"],
        faixas_premiacao=[3, 4, 5, 6, 7],
        numero_inicial=0,
        colunas=7
    ),
    LoteriaType.TIMEMANIA: LoteriaConfig(
        nome="Timemania",
        universo=80,
        sorteados=7,
        minimo_aposta=10,
        maximo_aposta=10,
        custo_minimo=3.5,
        dias_sorteio=["terça", "quinta", "domingo"],
        faixas_premiacao=[3, 4, 5, 6, 7]
    ),
    LoteriaType.DUPLA_SENA: LoteriaConfig(
        nome="Dupla Sena",
        universo=50,
        sorteados=6,
        minimo_aposta=6,
        maximo_aposta=15,
        custo_minimo=3.0,
        dias_sorteio=["segunda", "quarta", "sexta"],
        faixas_premiacao=[3, 4, 5, 6],
        sorteios_por_concurso=2
    )
}


@dataclass
class ElementoAnalise:
    """Dados de análise para um elemento (número)"""
    numero: int
    contagem_total: int
    frequencia_observed: float  # f_i(T)
    fr: float  # Fator de Recorrência
    hi: float  # Desvio de Harmonia |FR_i - 1|
    ict: float  # Índice de Convergence Temporal
    iseg: float  # Índice de Saturação Estatística Global
    illa: float  # Índice de Leitura Linear Ajustado
    imc: float  # Índice de Microcompressão (MCP-MD)
    score_mcp: float  # Score MCP-MD
    classe: str  # Classe A, B, C, D baseada em ICT
    maturidade: str  # Classificação de maturidade


class ModeloCanonico30:
    """
    Implementação do Modelo Canônico 3.0 - MCSCE
    Modelo de Convergência, Saturação e Complexidade Estatística
    """
    
    def __init__(self, historico: List, loteria_type: LoteriaType, config_override: Optional[LoteriaConfig] = None):
        self.loteria_type = loteria_type
        self.config = config_override or LOTERIAS_CONFIG[loteria_type]

        # Normalizar histórico: aceita tanto lista de listas quanto lista de dicts
        self.historico = []
        for item in historico:
            if isinstance(item, dict):
                # Formato: {'concurso': 1, 'numeros': [1, 2, 3, ...]}
                numeros = item.get('numeros', item.get('dezenas', []))
                # Converter para inteiros
                numeros = [int(n) for n in numeros]
                self.historico.append(numeros)
            else:
                # Formato: lista de inteiros
                self.historico.append([int(n) for n in item])
        
        self.T = len(self.historico)  # Total de concursos observados
        self.N = self.config.universo  # Tamanho do universo
        self.numeros = self.config.numeros
        self.k = self.config.sorteados  # Números sorteados por concurso
        # Dupla Sena: quando cada concurso traz os 2 sorteios juntos (12 dezenas), k dobra
        por_sorteio = self.config.sorteados
        if (self.config.sorteios_por_concurso > 1 and self.historico
                and all(len(c) > por_sorteio for c in self.historico)):
            self.k = por_sorteio * self.config.sorteios_por_concurso
        
        # Frequência teórica por elemento
        self.mu = self.k / self.N
        
        # Janelas MCP-MD
        self.W1 = min(100, self.T)  # Janela curta
        self.W2 = min(150, self.T)  # Janela média
        
        # Pré-calcular contagens
        self._calcular_contagens()
    
    def _calcular_contagens(self):
        """Calcular contagens históricas para cada número"""
        self.contagens_total = {i: 0 for i in self.numeros}
        self.contagens_W1 = {i: 0 for i in self.numeros}
        self.contagens_W2 = {i: 0 for i in self.numeros}
        
        # Contagem total
        for concurso in self.historico:
            for numero in concurso:
                if numero in self.contagens_total:
                    self.contagens_total[numero] += 1
        
        # Contagem W1 (últimos 100)
        for concurso in self.historico[-self.W1:]:
            for numero in concurso:
                if numero in self.contagens_total:
                    self.contagens_W1[numero] += 1
        
        # Contagem W2 (últimos 150)
        for concurso in self.historico[-self.W2:]:
            for numero in concurso:
                if numero in self.contagens_total:
                    self.contagens_W2[numero] += 1
    
    def calcular_frequencia(self, numero: int) -> float:
        """Calcular frequência observada f_i(T) = c_i / T"""
        return self.contagens_total[numero] / self.T if self.T > 0 else 0
    
    def calcular_fr(self, numero: int) -> float:
        """Calcular Fator de Recorrência FR_i = f_i(T) / μ"""
        fi = self.calcular_frequencia(numero)
        return fi / self.mu if self.mu > 0 else 0
    
    def calcular_hi(self, numero: int) -> float:
        """Calcular Desvio de Harmonia H_i = |FR_i - 1|"""
        fr = self.calcular_fr(numero)
        return abs(fr - 1)
    
    def calcular_ict(self, numero: int) -> float:
        """
        Calcular Índice de Convergência Temporal (ICT)
        Mede a estabilidade/convergência temporal do comportamento observado
        ICT mais baixo = mais estável/convergente
        """
        if self.T < 10:
            return 1.0  # Poucos dados para análise
        
        # Calcular desvio padrão da frequência ao longo do tempo
        frequencias_janela = []
        janela = 10
        
        for i in range(0, self.T, janela):
            fim = min(i + janela, self.T)
            contagem_janela = sum(
                1 for concurso in self.historico[i:fim] 
                if numero in concurso
            )
            freq = contagem_janela / (fim - i) if (fim - i) > 0 else 0
            frequencias_janela.append(freq)
        
        if len(frequencias_janela) < 2:
            return 1.0
        
        # ICT baseado na variabilidade da frequência
        desvio_padrao = statistics.stdev(frequencias_janela) if len(frequencias_janela) > 1 else 0
        media = statistics.mean(frequencias_janela)
        
        # Normalizar ICT entre 0 e 1
        if media > 0:
            cv = desvio_padrao / media  # Coeficiente de variação
            ict = min(cv * 2, 1.0)  # Normalizar
        else:
            ict = 1.0
        
        return ict
    
    def calcular_iseg(self, numero: int) -> float:
        """
        Calcular Índice de Saturação Estatística Global (ISEG)
        Avalia maturidade e compressão da dispersão estrutural
        """
        fr = self.calcular_fr(numero)
        hi = self.calcular_hi(numero)
        
        # ISEG baseado na proximidade de FR com 1 e baixa variabilidade
        saturacao = 1.0 / (1.0 + hi)
        return saturacao
    
    def calcular_illa(self, numero: int) -> float:
        """
        Calcular Índice de Leitura Linear Ajustado (ILLA)
        ILLA_i = w1(1-H_i) + w2(1-ICT_i) + w3(C_i) + w4(P_i) + w5(ISEG)
        """
        hi = self.calcular_hi(numero)
        ict = self.calcular_ict(numero)
        iseg = self.calcular_iseg(numero)
        
        # Pesos (weights)
        w1, w2, w3, w4, w5 = 0.25, 0.25, 0.2, 0.15, 0.15
        
        # Convergência incremental (C_i)
        fi_t = self.calcular_frequencia(numero)
        fi_w1 = self.contagens_W1[numero] / self.W1 if self.W1 > 0 else 0
        c_i = 1.0 / (1.0 + abs(fi_t - fi_w1))  # Quanto menor diferença, maior convergência
        
        # Persistência estrutural (P_i)
        p_i = min(self.contagens_total[numero] / max(self.T * self.mu, 1), 1.0)
        
        illa = (w1 * (1 - hi) + 
                w2 * (1 - ict) + 
                w3 * c_i + 
                w4 * p_i + 
                w5 * iseg)
        
        return illa
    
    def calcular_imc(self, numero: int) -> float:
        """
        Calcular Índice de Microcompressão (MCP-MD)
        IMC_i = Δ1 + Δ2
        Δ1 = f_i(W1) - f_i(W2)
        Δ2 = f_i(W1) - f_i(T)
        """
        fi_w1 = self.contagens_W1[numero] / self.W1 if self.W1 > 0 else 0
        fi_w2 = self.contagens_W2[numero] / self.W2 if self.W2 > 0 else 0
        fi_t = self.calcular_frequencia(numero)
        
        delta1 = fi_w1 - fi_w2
        delta2 = fi_w1 - fi_t
        
        imc = delta1 + delta2
        return imc
    
    def calcular_gamma(self) -> float:
        """
        Calcular fator adaptativo γ = (σ_W1 / σ_hist)^2
        """
        if self.T < 10 or self.W1 < 10:
            return 1.0
        
        # Variância histórica
        variancias = []
        for numero in self.numeros:
            fi = self.calcular_frequencia(numero)
            variancias.append(fi)
        
        sigma_hist = statistics.variance(variancias) if len(variancias) > 1 else 1
        
        # Variância W1
        variancias_w1 = []
        for numero in self.numeros:
            fi_w1 = self.contagens_W1[numero] / self.W1 if self.W1 > 0 else 0
            variancias_w1.append(fi_w1)
        
        sigma_w1 = statistics.variance(variancias_w1) if len(variancias_w1) > 1 else 1
        
        gamma = (sigma_w1 / sigma_hist) ** 2 if sigma_hist > 0 else 1.0
        return gamma
    
    def calcular_score_mcp(self, numero: int) -> float:
        """
        Calcular Score MCP-MD
        Score_i(MCP) = ILLA_i + γ · IMC_i(norm)
        """
        illa = self.calcular_illa(numero)
        imc = self.calcular_imc(numero)
        gamma = self.calcular_gamma()
        
        # Normalizar IMC
        imcs = [self.calcular_imc(n) for n in self.numeros]
        media_imc = statistics.mean(imcs) if imcs else 0
        std_imc = statistics.stdev(imcs) if len(imcs) > 1 else 1
        
        imc_norm = (imc - media_imc) / std_imc if std_imc > 0 else 0
        
        score_mcp = illa + gamma * imc_norm
        return score_mcp
    
    def classificar_elemento(self, ict: float) -> str:
        """Classificar elemento por quartis de ICT"""
        if ict <= 0.25:
            return "A"  # Menor ICT - mais estável
        elif ict <= 0.50:
            return "B"  # Intermediária inferior
        elif ict <= 0.75:
            return "C"  # Intermediária superior
        else:
            return "D"  # Maior ICT - menos estável
    
    def classificar_maturidade(self, fr: float, hi: float, ict: float) -> str:
        """Classificar maturidade estatística do elemento"""
        if hi < 0.1 and ict < 0.3:
            return "Quase Assintótico"
        elif hi < 0.3 and ict < 0.5:
            return "Em Saturação"
        elif hi < 0.5:
            return "Convergente"
        elif ict < 0.7:
            return "Imaturo"
        else:
            return "Ruído Estatístico Puro"
    
    def analisar_elemento(self, numero: int) -> ElementoAnalise:
        """Realizar análise completa de um elemento"""
        fr = self.calcular_fr(numero)
        hi = self.calcular_hi(numero)
        ict = self.calcular_ict(numero)
        iseg = self.calcular_iseg(numero)
        illa = self.calcular_illa(numero)
        imc = self.calcular_imc(numero)
        score_mcp = self.calcular_score_mcp(numero)
        
        return ElementoAnalise(
            numero=numero,
            contagem_total=self.contagens_total[numero],
            frequencia_observed=self.calcular_frequencia(numero),
            fr=fr,
            hi=hi,
            ict=ict,
            iseg=iseg,
            illa=illa,
            imc=imc,
            score_mcp=score_mcp,
            classe=self.classificar_elemento(ict),
            maturidade=self.classificar_maturidade(fr, hi, ict)
        )
    
    def analisar_todos_elementos(self) -> List[ElementoAnalise]:
        """Analisar todos os elementos do universo"""
        return [self.analisar_elemento(i) for i in self.numeros]
    
    def calcular_entropia(self) -> float:
        """
        Camada 5 - Informacional
        Calcular entropia do sistema
        """
        entropia = 0
        for numero in self.numeros:
            p = self.calcular_frequencia(numero)
            if p > 0:
                entropia -= p * math.log2(p)
        return entropia
    
    def calcular_complexidade(self) -> float:
        """
        Camada 5 - Informacional
        Medida simplificada de complexidade baseada na distribuição
        """
        frequencias = [self.calcular_frequencia(i) for i in self.numeros]
        return statistics.stdev(frequencias) if len(frequencias) > 1 else 0
    
    def calcular_compressibilidade(self) -> float:
        """
        Camada 5 - Informacional
        Compressibilidade baseada na regularidade da distribuição
        """
        entropia_max = math.log2(self.N)
        entropia_atual = self.calcular_entropia()
        return 1 - (entropia_atual / entropia_max) if entropia_max > 0 else 0
    
    def obter_resumo_analise(self) -> Dict:
        """Obter resumo completo da análise"""
        analises = self.analisar_todos_elementos()
        
        # Estatísticas gerais
        icts = [a.ict for a in analises]
        frs = [a.fr for a in analises]
        his = [a.hi for a in analises]
        scores_mcp = [a.score_mcp for a in analises]
        
        # Contar classes
        classes = {"A": 0, "B": 0, "C": 0, "D": 0}
        for a in analises:
            classes[a.classe] += 1
        
        # Contar maturidades
        maturidades = {}
        for a in analises:
            maturidades[a.maturidade] = maturidades.get(a.maturidade, 0) + 1
        
        return {
            "loteria": self.config.nome,
            "total_concursos": self.T,
            "universo": self.N,
            "sorteados_por_concurso": self.k,
            "frequencia_teorica": self.mu,
            "estatisticas_gerais": {
                "ict_medio": statistics.mean(icts),
                "ict_desvio": statistics.stdev(icts) if len(icts) > 1 else 0,
                "fr_medio": statistics.mean(frs),
                "hi_medio": statistics.mean(his),
                "score_mcp_medio": statistics.mean(scores_mcp)
            },
            "distribuicao_classes": classes,
            "distribuicao_maturidade": maturidades,
            "camada_informacional": {
                "entropia": self.calcular_entropia(),
                "complexidade": self.calcular_complexidade(),
                "compressibilidade": self.calcular_compressibilidade()
            },
            "analises_individuais": [
                {
                    "numero": a.numero,
                    "contagem": a.contagem_total,
                    "frequencia": round(a.frequencia_observed, 6),
                    "fr": round(a.fr, 4),
                    "hi": round(a.hi, 4),
                    "ict": round(a.ict, 4),
                    "classe": a.classe,
                    "maturidade": a.maturidade,
                    "iseg": round(a.iseg, 4),
                    "illa": round(a.illa, 4),
                    "imc": round(a.imc, 6),
                    "score_mcp": round(a.score_mcp, 4)
                }
                for a in sorted(analises, key=lambda x: x.ict)
            ]
        }


class ValidaçãoCamada7:
    """
    Camada 7 - Falsificação e Validação
    Implementa testes de Monte Carlo, análise Bayesiana e backtest
    """
    
    def __init__(self, modelo: ModeloCanonico30):
        self.modelo = modelo
    
    def teste_monte_carlo(self, simulacoes: int = 10000) -> Dict:
        """
        Executar simulação de Monte Carlo para validar resultados
        """
        import random
        
        # Pré-calcular scores de cada elemento para evitar recálculos desnecessários
        analises_atuais = self.modelo.analisar_todos_elementos()
        scores_map = {a.numero: a.score_mcp for a in analises_atuais}
        score_atual = statistics.mean([a.score_mcp for a in analises_atuais])
        
        resultados_simulados = []
        universo = list(self.modelo.numeros)
        k = self.modelo.k
        
        for _ in range(simulacoes):
            # Simular sorteio aleatório
            sorteio = random.sample(universo, k)
            resultados_simulados.append(sum(scores_map[numero] for numero in sorteio) / k)
        
        percentil = sum(1 for s in resultados_simulados if s >= score_atual) / simulacoes
        
        return {
            "simulacoes": simulacoes,
            "score_medio_simulado": statistics.mean(resultados_simulados),
            "score_atual": score_atual,
            "percentil": percentil,
            "significativo": percentil < 0.01  # Percentil < 1%
        }
    
    def analise_bayesiana(self) -> Dict:
        """
        Análise Bayesiana simplificada para avaliar evidência de padrões
        """
        # Hipótese nula: distribuição uniforme (equiprovável)
        # Hipótese alternativa: existe padrão detectável
        
        # Calcular chi-quadrado observado
        chi_quadrado = 0
        esperado = self.modelo.T * self.modelo.mu
        
        for numero in self.modelo.numeros:
            observado = self.modelo.contagens_total[numero]
            chi_quadrado += ((observado - esperado) ** 2) / esperado if esperado > 0 else 0
        
        # Fator de Bayes aproximado (simplificado)
        gl = self.modelo.N - 1  # Graus de liberdade
        bayes_factor = math.exp(-chi_quadrado / 2) / math.sqrt(2 * math.pi * gl)
        
        return {
            "chi_quadrado": chi_quadrado,
            "graus_liberdade": gl,
            "bayes_factor": bayes_factor,
            "evidencia_forte": bayes_factor > 10
        }
    
    def backtest(self, janela_teste: int = 50) -> Dict:
        """
        Realizar backtest usando janela de teste
        """
        if self.modelo.T < janela_teste + 50:
            return {"erro": "Histórico insuficiente para backtest"}
        
        # Dividir histórico em treino e teste
        historico_treino = self.modelo.historico[:-janela_teste]
        historico_teste = self.modelo.historico[-janela_teste:]
        
        # Criar modelo apenas com dados de treino
        modelo_treino = ModeloCanonico30(historico_treino, self.modelo.loteria_type, config_override=self.modelo.config)
        
        # Selecionar top 10 números por score MCP
        analises = modelo_treino.analisar_todos_elementos()
        top_numeros = sorted(analises, key=lambda x: x.score_mcp, reverse=True)[:10]
        top_numeros_set = {a.numero for a in top_numeros}
        
        # Testar no período de teste
        acertos = 0
        total_sorteados = 0
        
        for concurso in historico_teste:
            for numero in concurso:
                total_sorteados += 1
                if numero in top_numeros_set:
                    acertos += 1
        
        taxa_acerto = acertos / total_sorteados if total_sorteados > 0 else 0
        taxa_esperada = len(top_numeros_set) / self.modelo.N
        
        return {
            "janela_teste": janela_teste,
            "concursos_teste": len(historico_teste),
            "acertos": acertos,
            "total_sorteados": total_sorteados,
            "taxa_acerto": taxa_acerto,
            "taxa_esperada": taxa_esperada,
            "performance_relativa": taxa_acerto / taxa_esperada if taxa_esperada > 0 else 0
        }
    
    def validacao_completa(self) -> Dict:
        """Executar todas as validaçōes da Camada 7"""
        monte_carlo = self.teste_monte_carlo()
        bayesiana = self.analise_bayesiana()
        backtest = self.backtest()
        
        # Critérios de validação MCP-MD
        validacao_mcp_md = (
            monte_carlo["percentil"] < 0.01 and
            bayesiana["bayes_factor"] > 10 and
            backtest.get("performance_relativa", 0) > 1.2
        )
        
        return {
            "monte_carlo": monte_carlo,
            "bayesiana": bayesiana,
            "backtest": backtest,
            "validacao_mcp_md": validacao_mcp_md,
            "conclusao": "MCP-MD válido" if validacao_mcp_md else "MCP-MD não válido - ruído estatístico"
        }


def gerar_jogo_sugerido(modelo: ModeloCanonico30, quantidade_numeros: int) -> List[int]:
    """
    Gerar sugestão de jogo baseada na análise estatística
    Considera múltiplas camadas do modelo canônico
    """
    if modelo.config.colunas:
        return gerar_jogo_por_coluna(modelo.historico, modelo.config)

    analises = modelo.analisar_todos_elementos()
    
    # Estratégia balanceada:
    # - 40% números com melhor score MCP (Classe A/B)
    # - 30% números com menor ICT (mais estáveis)
    # - 20% números com FR próximo de 1 (equilibrados)
    # - 10% números aleatórios para diversificação
    
    n_mcp = int(quantidade_numeros * 0.4)
    n_ict = int(quantidade_numeros * 0.3)
    n_fr = int(quantidade_numeros * 0.2)
    n_aleatorio = quantidade_numeros - n_mcp - n_ict - n_fr
    
    sugeridos = set()
    
    # Top por score MCP
    por_mcp = sorted(analises, key=lambda x: x.score_mcp, reverse=True)
    for a in por_mcp[:n_mcp]:
        sugeridos.add(a.numero)
    
    # Top por ICT (menor é melhor)
    por_ict = sorted(analises, key=lambda x: x.ict)
    for a in por_ict[:n_ict]:
        if len(sugeridos) < n_mcp + n_ict:
            sugeridos.add(a.numero)
    
    # Top por FR próximo de 1
    por_fr = sorted(analises, key=lambda x: abs(x.fr - 1))
    for a in por_fr[:n_fr]:
        if len(sugeridos) < n_mcp + n_ict + n_fr:
            sugeridos.add(a.numero)
    
    # Aleatórios para completar
    import random
    while len(sugeridos) < quantidade_numeros:
        num = random.choice(modelo.numeros)
        sugeridos.add(num)
    
    return sorted(list(sugeridos))[:quantidade_numeros]


def gerar_multiplos_jogos(
    modelo: ModeloCanonico30, 
    quantidade_jogos: int, 
    quantidade_numeros: int,
    numeros_base: Optional[List[int]] = None
) -> List[List[int]]:
    """
    Gera N combinações distintas e balanceadas baseadas no Modelo Canônico 3.0.
    Garante que não haja jogos duplicados e respeita os limites da loteria.
    Se numeros_base for fornecido, restringe a geração ao subconjunto de números escolhido pelo usuário.
    """
    import random

    if modelo.config.colunas:
        return _gerar_multiplos_por_coluna(modelo, quantidade_jogos, numeros_base)

    analises = modelo.analisar_todos_elementos()
    
    # Se o usuário definiu um pool de números base, valida e filtra
    if numeros_base and len(numeros_base) >= quantidade_numeros:
        universo_disponivel = sorted(list({n for n in numeros_base if n in modelo.contagens_total}))
        if len(universo_disponivel) < quantidade_numeros:
            universo_disponivel = list(modelo.numeros)
    else:
        universo_disponivel = list(modelo.numeros)
    
    # Calcular pesos estatísticos para cada número
    pesos = {a.numero: _peso_canonico(a) for a in analises}

    jogos_gerados = []
    jogos_set = set()
    tentativas = 0
    max_tentativas = quantidade_jogos * 150

    # Candidatos disponíveis dentro do universo selecionado
    candidatos_analises = [a for a in analises if a.numero in universo_disponivel]

    while len(jogos_gerados) < quantidade_jogos and tentativas < max_tentativas:
        tentativas += 1
        jogo = set()
        
        # 1. 40% dos números vindos dos melhores scores do grupo disponível
        if len(candidatos_analises) > quantidade_numeros:
            top_candidatos = sorted(candidatos_analises, key=lambda x: pesos[x.numero], reverse=True)[:max(quantidade_numeros * 2, 10)]
            qtd_top = min(len(top_candidatos), max(1, int(quantidade_numeros * 0.4)))
            amostra_top = random.sample([c.numero for c in top_candidatos], qtd_top)
            jogo.update(amostra_top)
        
        # 2. Completar com amostragem ponderada pelos pesos canônicos no universo disponível
        while len(jogo) < quantidade_numeros:
            candidatos_restantes = [n for n in universo_disponivel if n not in jogo]
            if not candidatos_restantes:
                break
            pesos_restantes = [pesos.get(n, 1.0) for n in candidatos_restantes]
            escolhido = random.choices(candidatos_restantes, weights=pesos_restantes, k=1)[0]
            jogo.add(escolhido)

        if len(jogo) == quantidade_numeros:
            jogo_ordenado = tuple(sorted(list(jogo)))
            if jogo_ordenado not in jogos_set:
                jogos_set.add(jogo_ordenado)
                jogos_gerados.append(list(jogo_ordenado))

    return jogos_gerados


def _peso_canonico(a: ElementoAnalise) -> float:
    estabilidade = max(0.0, 1.0 - a.ict)
    harmonia = max(0.0, 1.0 - abs(a.fr - 1.0))
    return max(0.05, (a.score_mcp * 1.5) + (estabilidade * 1.0) + (harmonia * 0.8))


def _config_coluna(config: LoteriaConfig, indice: int) -> LoteriaConfig:
    return LoteriaConfig(
        nome=f"{config.nome} - Coluna {indice + 1}",
        universo=config.universo,
        sorteados=1,
        minimo_aposta=1,
        maximo_aposta=1,
        custo_minimo=0.0,
        dias_sorteio=[],
        faixas_premiacao=[],
        numero_inicial=config.numero_inicial,
    )


def modelos_por_coluna(historico: List, config: LoteriaConfig, loteria_type: LoteriaType = LoteriaType.SUPER_SETE) -> List[ModeloCanonico30]:
    """Um Modelo Canônico por coluna (Super Sete): cada coluna é um sorteio independente de 1 dígito."""
    historico_normalizado = ModeloCanonico30(historico, loteria_type, config_override=config).historico
    validos = [c for c in historico_normalizado if len(c) == config.colunas]
    return [
        ModeloCanonico30([[c[i]] for c in validos], loteria_type, config_override=_config_coluna(config, i))
        for i in range(config.colunas)
    ]


def analise_por_coluna(historico: List, config: LoteriaConfig) -> List[Dict]:
    resultado = []
    for i, modelo in enumerate(modelos_por_coluna(historico, config)):
        analises = sorted(modelo.analisar_todos_elementos(), key=lambda a: a.score_mcp, reverse=True)
        resultado.append({
            "coluna": i + 1,
            "digitos": [
                {
                    "numero": a.numero,
                    "contagem": a.contagem_total,
                    "frequencia": round(a.frequencia_observed, 6),
                    "fr": round(a.fr, 4),
                    "score_mcp": round(a.score_mcp, 4),
                    "classe": a.classe,
                }
                for a in analises
            ],
        })
    return resultado


def _escolher_digitos(modelos: List[ModeloCanonico30], permitidos: Optional[set] = None) -> List[int]:
    import random
    jogo = []
    for modelo in modelos:
        analises = [a for a in modelo.analisar_todos_elementos() if not permitidos or a.numero in permitidos]
        if not analises:
            analises = modelo.analisar_todos_elementos()
        escolhido = random.choices(analises, weights=[_peso_canonico(a) for a in analises], k=1)[0]
        jogo.append(escolhido.numero)
    return jogo


def gerar_jogo_por_coluna(historico: List, config: LoteriaConfig) -> List[int]:
    """Jogo do Super Sete: um dígito por coluna, na ordem das colunas (repetição permitida)."""
    return _escolher_digitos(modelos_por_coluna(historico, config))


def _gerar_multiplos_por_coluna(modelo: ModeloCanonico30, quantidade_jogos: int,
                                numeros_base: Optional[List[int]] = None) -> List[List[int]]:
    modelos = modelos_por_coluna(modelo.historico, modelo.config)
    permitidos = {n for n in (numeros_base or []) if n in modelo.contagens_total} or None
    jogos, vistos = [], set()
    tentativas = 0
    while len(jogos) < quantidade_jogos and tentativas < quantidade_jogos * 150:
        tentativas += 1
        jogo = _escolher_digitos(modelos, permitidos)
        if tuple(jogo) not in vistos:
            vistos.add(tuple(jogo))
            jogos.append(jogo)
    return jogos


if __name__ == "__main__":
    # Exemplo de uso
    print("Modelo Canônico 3.0 + MCP-MD 1.0")
    print("AGENTE LLN ICT FR - Sistema de Análise Estatística")
    print("=" * 60)
    
    # Histórico fictício para teste
    historico_teste = [
        [1, 5, 10, 23, 35, 42],
        [3, 12, 18, 29, 41, 55],
        [7, 15, 22, 33, 44, 58],
        # ... adicionar mais concursos
    ]
    
    # Criar modelo para Mega-Sena
    modelo = ModeloCanonico30(historico_teste, LoteriaType.MEGA_SENA)
    resumo = modelo.obter_resumo_analise()
    
    print(f"\nLoteria: {resumo['loteria']}")
    print(f"Concursos analisados: {resumo['total_concursos']}")
    print(f"ICT Médio: {resumo['estatisticas_gerais']['ict_medio']:.4f}")
    print(f"Entropia: {resumo['camada_informacional']['entropia']:.4f}")
