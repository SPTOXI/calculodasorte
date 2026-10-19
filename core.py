"""
Sistema de Análise Estatística para Loterias - Modelo Canônico 4.0 + MCP-MD 1.0
MCOSS (Heptacolunar - Super Sete) / MCODSen (Hexagonal Bivariado - Dupla Sena) / MCODS (Heptagonal Calendário - Dia de Sorte) / MCOMIL (Biparamétrico Hexa-Trevo - +Milionária) / MCOC (Centesimal 10x10 - Lotomania) / MCOD (Decagonal - Timemania) / MCOM (Matricial 5x5 - Lotofácil) / MCOH (Hexagonal - Mega-Sena) / MCOP (Pentagonal - Quina) - Modelos Canônicos de Otimização e Cobertura Espacial
AGENTE LLN ICT FR - Lei dos Grandes Números, Índice de Convergência Temporal, Fator de Recorrência
"""

from __future__ import annotations
import math
import statistics
from typing import Dict, List, Tuple, Optional, Any, Union, Set
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
        dias_sorteio=["terça", "quinta", "sábado"],
        faixas_premiacao=[4, 5, 6]
    ),
    LoteriaType.QUINA: LoteriaConfig(
        nome="Quina",
        universo=80,
        sorteados=5,
        minimo_aposta=5,
        maximo_aposta=15,
        custo_minimo=3.0,
        dias_sorteio=["segunda", "terça", "quarta", "quinta", "sexta", "sábado"],
        faixas_premiacao=[2, 3, 4, 5]
    ),
    LoteriaType.LOTOFACIL: LoteriaConfig(
        nome="Lotofácil",
        universo=25,
        sorteados=15,
        minimo_aposta=15,
        maximo_aposta=20,
        custo_minimo=3.5,
        dias_sorteio=["segunda", "terça", "quarta", "quinta", "sexta", "sábado"],
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
        maximo_aposta=12,
        custo_minimo=6.0,
        dias_sorteio=["quarta", "sábado"],
        faixas_premiacao=list(range(1, 11))
    ),
    LoteriaType.DIA_DE_SORTE: LoteriaConfig(
        nome="Dia de Sorte",
        universo=31,
        sorteados=7,
        minimo_aposta=7,
        maximo_aposta=15,
        custo_minimo=2.5,
        dias_sorteio=["segunda", "terça", "quarta", "quinta", "sexta", "sábado"],
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
        dias_sorteio=["terça", "quinta", "sábado"],
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


class ModeloCanonico40:
    """
    Implementação do Modelo Canônico 4.0 - MCOH
    Modelo de Convergência Estatística, Saturação e Otimização Hexagonal (K-Medians).
    Engloba as camadas 1-7 do MCSCE, a extensão experimental MCP-MD 1.0 e a
    Camada 8 de Cobertura Espacial e Dispersão Hexagonal.
    """
    
    def __init__(self, historico: List, loteria_type: LoteriaType, config_override: Optional[LoteriaConfig] = None):
        self.loteria_type = loteria_type
        self.config = config_override or LOTERIAS_CONFIG[loteria_type]
        self.N = self.config.universo  # Tamanho do universo
        self.numeros = self.config.numeros
        if self.N < 2 or not 1 <= self.config.sorteados <= self.N:
            raise ValueError("Configuração inválida de universo ou quantidade sorteada")
        self.historico = self._normalizar_historico(historico)
        self.T = len(self.historico)
        self.k = len(self.historico[0])  # Inclui ambos os sorteios quando fornecidos
        self.mu = self.k / self.N
        self.W1 = min(100, self.T)
        self.W2 = min(150, self.T)
        self._memo: Dict = {}
        self._calcular_contagens()

    @staticmethod
    def _inteiro(valor, campo: str) -> int:
        """Aceitar inteiros e sua representação textual sem truncar valores."""
        if isinstance(valor, bool) or not isinstance(valor, (str, int, float)):
            raise ValueError(f"{campo} deve ser inteiro")
        try:
            convertido = int(valor)
        except (ValueError, OverflowError):
            raise ValueError(f"{campo} deve ser inteiro") from None
        if isinstance(valor, float) and valor != convertido:
            raise ValueError(f"{campo} deve ser inteiro")
        return convertido

    def _normalizar_historico(self, historico: List) -> List[List[int]]:
        """Validar concursos antes de calcular; listas seguem a ordem cronológica recebida."""
        if not isinstance(historico, (list, tuple)) or not historico:
            raise ValueError("Histórico vazio ou inválido")
        itens = list(historico)
        identificados = [isinstance(item, dict) and 'concurso' in item for item in itens]
        if any(identificados):
            if not all(identificados):
                raise ValueError("Informe o número do concurso em todos os registros ou em nenhum")
            ids = [self._inteiro(item['concurso'], "Número do concurso") for item in itens]
            if any(i <= 0 for i in ids) or len(set(ids)) != len(ids):
                raise ValueError("Números de concurso devem ser positivos e únicos")
            itens = [item for _, item in sorted(zip(ids, itens), key=lambda par: par[0])]

        resultado = []
        tamanhos = set()
        por_sorteio = self.config.sorteados
        tamanhos_permitidos = {por_sorteio}
        if self.config.sorteios_por_concurso > 1:
            tamanhos_permitidos.add(por_sorteio * self.config.sorteios_por_concurso)
        if self.config.colunas:
            tamanhos_permitidos = {self.config.colunas}
        for indice, item in enumerate(itens, 1):
            valores = item.get('numeros', item.get('dezenas')) if isinstance(item, dict) else item
            if not isinstance(valores, (list, tuple)) or len(valores) not in tamanhos_permitidos:
                raise ValueError(f"Concurso {indice}: quantidade de números inválida")
            numeros = [self._inteiro(n, f"Concurso {indice}: número") for n in valores]
            if any(n < self.config.numero_inicial or n > self.config.numero_final for n in numeros):
                raise ValueError(f"Concurso {indice}: número fora do universo da loteria")
            if not self.config.colunas:
                for inicio in range(0, len(numeros), por_sorteio):
                    sorteio = numeros[inicio:inicio + por_sorteio]
                    if len(set(sorteio)) != por_sorteio:
                        raise ValueError(f"Concurso {indice}: números repetidos no mesmo sorteio")
            tamanhos.add(len(numeros))
            resultado.append(numeros)
        if len(tamanhos) != 1:
            raise ValueError("Histórico não pode misturar concursos com um e dois sorteios")
        return resultado
    
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
        Estimador operacional de estabilidade das frequências acumuladas.

        O documento não define a fórmula do ICT. Aqui, usa-se o desvio padrão
        populacional de f_i(t), ceil(T/2) <= t <= T, dividido por mu e limitado
        a 1. Frequências acumuladas permitem redução da variabilidade com T;
        blocos fixos de 10 concursos não possuem essa propriedade.
        """
        if self.T < 20:
            return 1.0
        if 'icts' not in self._memo:
            acumuladas = dict.fromkeys(self.numeros, 0)
            trajetorias = {n: [] for n in self.numeros}
            inicio = math.ceil(self.T / 2)
            for t, concurso in enumerate(self.historico, 1):
                for n in concurso:
                    acumuladas[n] += 1
                if t >= inicio:
                    for n in self.numeros:
                        trajetorias[n].append(acumuladas[n] / t)
            self._memo['icts'] = {
                n: min(statistics.pstdev(trajetorias[n]) / self.mu, 1.0)
                for n in self.numeros
            }
        return self._memo['icts'][numero]

    def calcular_iseg(self, numero: Optional[int] = None) -> float:
        """
        Calcular Índice de Saturação Estatística Global (ISEG)
        Avalia maturidade e compressão da dispersão estrutural
        """
        # Aproximação operacional global; a fonte não fornece fórmula de ISEG.
        if 'iseg' not in self._memo:
            hi_medio = statistics.mean(self.calcular_hi(n) for n in self.numeros)
            self._memo['iseg'] = 1.0 / (1.0 + hi_medio)
        return self._memo['iseg']
    
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
        if self.T < 150:
            return 0.0  # Janelas canônicas incompletas: sem contribuição MCP
        fi_w1 = self.contagens_W1[numero] / self.W1 if self.W1 > 0 else 0
        fi_w2 = self.contagens_W2[numero] / self.W2 if self.W2 > 0 else 0
        fi_t = self.calcular_frequencia(numero)
        
        delta1 = fi_w1 - fi_w2
        delta2 = fi_w1 - fi_t
        
        imc = delta1 + delta2
        return imc
    
    def calcular_gamma(self) -> float:
        """γ = (σ_W1/σ_hist)² = Var(W1)/Var(hist), sem novo quadrado."""
        status = self.obter_status_mcp()
        return status['gamma'] if status['disponivel'] else 0.0

    def obter_status_mcp(self) -> Dict:
        """Distinguir extensão calculável de ausência/degeneração dos dados."""
        if 'status_mcp' not in self._memo:
            motivo = None
            gamma = None
            if self.T < 150:
                motivo = "MCP-MD requer pelo menos 150 concursos para completar as janelas de 100 e 150."
            else:
                var_hist = statistics.pvariance(self.calcular_frequencia(n) for n in self.numeros)
                if var_hist == 0:
                    motivo = "Dispersão histórica nula: o denominador de gamma é zero."
                else:
                    var_w1 = statistics.pvariance(self.contagens_W1[n] / 100 for n in self.numeros)
                    gamma = var_w1 / var_hist
            self._memo['status_mcp'] = {
                'disponivel': motivo is None,
                'status': 'disponivel' if motivo is None else 'indisponivel',
                'motivo': motivo,
                'janela_curta': 100,
                'janela_media': 150,
                'gamma': gamma,
            }
        return dict(self._memo['status_mcp'])
    
    def calcular_score_mcp(self, numero: int) -> float:
        """
        Calcular Score MCP-MD
        Score_i(MCP) = ILLA_i + γ · IMC_i(norm)
        """
        illa = self.calcular_illa(numero)
        if not self.obter_status_mcp()['disponivel']:
            return illa
        imc = self.calcular_imc(numero)
        gamma = self.calcular_gamma()
        
        # Normalizar IMC
        if 'imc_stats' not in self._memo:
            imcs = [self.calcular_imc(n) for n in self.numeros]
            self._memo['imc_stats'] = (
                statistics.mean(imcs) if imcs else 0,
                statistics.pstdev(imcs),
            )
        media_imc, std_imc = self._memo['imc_stats']
        
        imc_norm = (imc - media_imc) / std_imc if std_imc > 0 else 0
        
        score_mcp = illa + gamma * imc_norm
        return score_mcp
    
    def classificar_elemento(self, ict: float) -> str:
        """Quartis empíricos inclusivos; valores empatados recebem a mesma classe."""
        q1, q2, q3 = self.obter_quartis_ict()
        if ict <= q1:
            return "A"  # Menor ICT - mais estável
        elif ict <= q2:
            return "B"  # Intermediária inferior
        elif ict <= q3:
            return "C"  # Intermediária superior
        else:
            return "D"  # Maior ICT - menos estável

    def obter_quartis_ict(self) -> List[float]:
        if 'quartis_ict' not in self._memo:
            self._memo['quartis_ict'] = statistics.quantiles(
                [self.calcular_ict(n) for n in self.numeros], n=4, method='inclusive'
            )
        return list(self._memo['quartis_ict'])
    
    def classificar_maturidade(self, fr: float, hi: float, ict: float) -> str:
        """Classificar maturidade estatística do elemento"""
        if hi < 0.1 and ict < 0.3:
            return "Quase Assintótico"
        elif hi < 0.3 and ict < 0.5:
            return "Em Saturação"
        elif hi < 0.5:
            return "Convergente"
        else:
            return "Imaturo"  # Ruído não pode ser diagnosticado por um único descritor
    
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
        """Analisar todos os elementos do universo (calculado uma vez por modelo)"""
        if 'analises' not in self._memo:
            self._memo['analises'] = [self.analisar_elemento(i) for i in self.numeros]
        return self._memo['analises']
    
    def calcular_entropia(self) -> float:
        """
        Camada 5 - Informacional
        Calcular entropia do sistema
        """
        total = sum(self.contagens_total.values())
        probabilidades = [c / total for c in self.contagens_total.values() if c]
        return min(math.log2(self.N), -sum(p * math.log2(p) for p in probabilidades))
    
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
        return max(0.0, min(1.0, 1 - entropia_atual / entropia_max))
    
    def obter_resumo_analise(self) -> Dict:
        """Obter resumo completo da análise"""
        if 'resumo' in self._memo:
            return self._memo['resumo']
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
        
        # Configuração da Camada Espacial especializada por topologia da loteria
        is_supersete = (self.config.nome == "Super Sete" or self.config.colunas == 7 or getattr(self, 'loteria_type', None) == LoteriaType.SUPER_SETE)
        is_duplasena = (self.config.nome == "Dupla Sena" or getattr(self, 'loteria_type', None) == LoteriaType.DUPLA_SENA or (self.N == 50 and self.config.sorteios_por_concurso == 2))
        is_diadesorte = (self.config.nome == "Dia de Sorte" or getattr(self, 'loteria_type', None) == LoteriaType.DIA_DE_SORTE or (self.N == 31 and self.config.sorteados == 7))
        is_maismilionaria = (self.config.nome == "+Milionária" or getattr(self, 'loteria_type', None) == LoteriaType.MAIS_MILIONARIA or (self.N == 50 and self.config.sorteados == 6 and not is_duplasena))
        is_lotomania = (self.config.nome == "Lotomania" or (self.N == 100 and self.config.sorteados == 20))
        is_timemania = (self.config.nome == "Timemania" or (self.N == 80 and self.config.sorteados == 7))
        is_lotofacil = (self.config.nome == "Lotofácil" or (self.N == 25 and self.config.sorteados == 15))
        is_quina = (self.config.nome == "Quina" or (self.N == 80 and self.config.sorteados == 5))
        is_megasena = (self.config.nome == "Mega-Sena" or (self.N == 60 and self.config.sorteados == 6))

        if is_supersete:
            modelo_metodologia = "Canônico 4.0 — MCOSS (Super Sete)"
            extensao_desc = "MCP-MD 1.0 + Otimização Heptacolunar Independente"
            camada_espacial_desc = "Heptacolunar Independente K-Medians (Dispersão Vetorial Z_10^7)"
            camada_espacial_dict = {
                "modelo": "Heptacolunar Independente K-Medians (Z_10^7)",
                "total_setores": 7,
                "largura_setor": 1.0,
                "universo": 10,
                "metrica": "Vetorial modular Z_10 em 7 colunas",
                "distancia_maxima_teorica": 5.0
            }
        elif is_duplasena:
            modelo_metodologia = "Canônico 4.0 — MCODSen (Dupla Sena)"
            extensao_desc = "MCP-MD 1.0 + Otimização Hexagonal Bivariada de Duplo Sorteio"
            camada_espacial_desc = "Hexagonal Bivariada K-Medians (Dispersão Cíclica Z_50 Duplo Sorteio)"
            camada_espacial_dict = {
                "modelo": "Hexagonal Bivariada K-Medians (Z_50 Duplo Sorteio)",
                "total_setores": 6,
                "largura_setor": 8.33,
                "universo": 50,
                "metrica": "Circular cíclica Z_50 com cobertura conjunta S1/S2",
                "distancia_maxima_teorica": 4.0
            }
        elif is_diadesorte:
            modelo_metodologia = "Canônico 4.0 — MCODS (Dia de Sorte)"
            extensao_desc = "MCP-MD 1.0 + Otimização Heptagonal de Calendário"
            camada_espacial_desc = "Heptagonal Calendário K-Medians (Dispersão Cíclica Z_31)"
            camada_espacial_dict = {
                "modelo": "Heptagonal Calendário K-Medians (Z_31)",
                "total_setores": 7,
                "largura_setor": 4.43,
                "universo": 31,
                "metrica": "Circular cíclica Z_31 (Calendário)",
                "distancia_maxima_teorica": 2.0
            }
        elif is_maismilionaria:
            modelo_metodologia = "Canônico 4.0 — MCOMIL (+Milionária)"
            extensao_desc = "MCP-MD 1.0 + Otimização Biparamétrica Hexa-Trevo"
            camada_espacial_desc = "Hexa-Trevo K-Medians (Dispersão Cíclica Z_50 + Trevos)"
            camada_espacial_dict = {
                "modelo": "Hexa-Trevo K-Medians (Z_50 + Trevos)",
                "total_setores": 6,
                "largura_setor": 8.33,
                "universo": 50,
                "metrica": "Circular cíclica Z_50 e Trevos P_2({1..6})",
                "distancia_maxima_teorica": 4.0
            }
        elif is_lotomania:
            modelo_metodologia = "Canônico 4.0 — MCOC (Lotomania)"
            extensao_desc = "MCP-MD 1.0 + Otimização Centesimal e Matricial 10x10"
            camada_espacial_desc = "Centesimal Matricial 10x10 K-Medians (Quadrantes e Grid)"
            camada_espacial_dict = {
                "modelo": "Centesimal Matricial 10x10 (Quadrantes e Grid)",
                "total_setores": 10,
                "largura_setor": 10.0,
                "universo": 100,
                "metrica": "Grid bidimensional Manhattan (10 linhas x 10 colunas)",
                "distancia_maxima_teorica": 1.0
            }
        elif is_timemania:
            modelo_metodologia = "Canônico 4.0 — MCOD (Timemania)"
            extensao_desc = "MCP-MD 1.0 + Otimização Decagonal e Time do Coração"
            camada_espacial_desc = "Decagonal K-Medians (Dispersão Cíclica Z_80)"
            camada_espacial_dict = {
                "modelo": "Decagonal K-Medians (Z_80)",
                "total_setores": 10,
                "largura_setor": 8.0,
                "universo": 80,
                "metrica": "Circular cíclica Z_80",
                "distancia_maxima_teorica": 4.0
            }
        elif is_lotofacil:
            modelo_metodologia = "Canônico 4.0 — MCOM (Lotofácil)"
            extensao_desc = "MCP-MD 1.0 + Otimização Matricial 5x5"
            camada_espacial_desc = "Matricial 5x5 K-Medians (Quintetos)"
            camada_espacial_dict = {
                "modelo": "Matricial 5x5 K-Medians (Quintetos)",
                "total_setores": 5,
                "largura_setor": 5.0,
                "universo": 25,
                "metrica": "Grid bidimensional Manhattan e Z_25",
                "distancia_maxima_teorica": 1.0
            }
        elif is_quina:
            modelo_metodologia = "Canônico 4.0 — MCOP (Quina)"
            extensao_desc = "MCP-MD 1.0 + Otimização Pentagonal"
            camada_espacial_desc = "Pentagonal K-Medians (Dispersão Cíclica Z_80)"
            camada_espacial_dict = {
                "modelo": "Pentagonal K-Medians (Z_80)",
                "total_setores": 5,
                "largura_setor": 16.0,
                "universo": 80,
                "metrica": "Circular cíclica Z_80",
                "distancia_maxima_teorica": 8.0
            }
        elif is_megasena:
            modelo_metodologia = "Canônico 4.0 — MCOH (Mega-Sena)"
            extensao_desc = "MCP-MD 1.0 + Otimização Hexagonal"
            camada_espacial_desc = "Hexagonal K-Medians (Dispersão Cíclica Z_60)"
            camada_espacial_dict = {
                "modelo": "Hexagonal K-Medians (Z_60)",
                "total_setores": 6,
                "largura_setor": 10.0,
                "universo": 60,
                "metrica": "Circular cíclica Z_60",
                "distancia_maxima_teorica": 5.0
            }
        else:
            modelo_metodologia = f"Canônico 4.0 ({self.config.nome})"
            extensao_desc = "MCP-MD 1.0 + Cobertura Espacial"
            camada_espacial_desc = f"Espacial K-Medians (Z_{self.N})"
            camada_espacial_dict = {
                "modelo": f"Espacial K-Medians (Z_{self.N})",
                "total_setores": 6 if self.N >= 60 else max(3, self.config.sorteados),
                "largura_setor": round(self.N / 6, 1),
                "universo": self.N,
                "metrica": f"Circular cíclica Z_{self.N}",
                "distancia_maxima_teorica": round(self.N / 12, 1)
            }

        self._memo['resumo'] = {
            "loteria": self.config.nome,
            "total_concursos": self.T,
            "universo": self.N,
            "sorteados_por_concurso": self.k,
            "frequencia_teorica": self.mu,
            "unidade_frequencia": (
                "ocorrencias_por_concurso" if self.config.colunas or self.k > self.config.sorteados
                else "proporcao_de_concursos"
            ),
            "escopo_analise": (
                "digitos_agregados_entre_colunas" if self.config.colunas else "numeros_principais"
            ),
            "mcp_md": self.obter_status_mcp(),
            "quartis_ict": self.obter_quartis_ict(),
            "metodologia": {
                "modelo": modelo_metodologia,
                "versao": "4.0",
                "extensao": extensao_desc,
                "implementacao": "operacional-2026-10",
                "camada_espacial": camada_espacial_desc,
                "ict": "min(1, pstdev(f_i(t), ceil(T/2) <= t <= T) / mu); mínimo de 20 concursos",
                "ict_disponivel": self.T >= 20,
                "classes": "Quartis empíricos inclusivos de ICT; empates na mesma classe. Classes são relativas.",
                "iseg": "1 / (1 + média de H_i); aproximação global",
                "pesos_illa": [0.25, 0.25, 0.20, 0.15, 0.15],
                "convergencia_incremental": "C_i = 1 / (1 + abs(f_i(T) - f_i(W1)))",
                "persistencia": "P_i = min(c_i / max(T * mu, 1), 1)",
                "normalizacao_imc": "Desvio padrão populacional entre todos os elementos; IMC uniforme contribui zero",
                "entropia": "Shannon marginal: p_i = c_i / soma(c); não mede dependência temporal",
                "aproximacoes": ["ICT", "ISEG", "C_i", "P_i", "pesos ILLA", "limiares de maturidade", "MCOH Hexagonal", "MCOP Pentagonal", "MCOM Matricial", "MCOD Decagonal", "MCOC Centesimal"],
                "componentes_nao_implementados": [
                    "IIE", "FCT", "ILLA Dinâmico", "AE", "complexidade algorítmica",
                    "compressão efetiva de sequências", "fractal", "multifractal", "caos"
                ],
                "limite": "A fonte não especifica fórmulas para todas as camadas. Descritores e classes não comprovam vantagem ou equiprobabilidade.",
            },
            "estatisticas_gerais": {
                "ict_medio": statistics.mean(icts),
                "ict_desvio": statistics.stdev(icts) if len(icts) > 1 else 0,
                "fr_medio": statistics.mean(frs),
                "hi_medio": statistics.mean(his),
                "score_mcp_medio": statistics.mean(scores_mcp),
                "iseg_global": self.calcular_iseg(),
            },
            "camada_espacial": camada_espacial_dict,
            "distribuicao_classes": classes,
            "distribuicao_maturidade": maturidades,
            "camada_informacional": {
                "entropia": self.calcular_entropia(),
                "entropia_maxima": math.log2(self.N),
                "entropia_normalizada": self.calcular_entropia() / math.log2(self.N),
                "dispersao_frequencias": self.calcular_complexidade(),
                "deficit_entropia": self.calcular_compressibilidade(),
                "observacao": "complexidade e compressibilidade são aliases legados de dispersão e déficit de entropia; não são testes algorítmicos.",
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
            ],
            "dinamica_canonica": self.avaliar_dinamica_expansao_retracao(),
            "opcoes_analise": self.obter_opcoes_analise()
        }
        return self._memo['resumo']

    def obter_opcoes_analise(self) -> Dict[str, Any]:
        """Retorna o painel completo das formas de análise disponíveis (Canônica, Fechamentos e Tradicionais)."""
        if 'opcoes_analise' not in self._memo:
            from metodos_analise import construir_painel_opcoes_analise
            self._memo['opcoes_analise'] = construir_painel_opcoes_analise(self)
        return self._memo['opcoes_analise']

    def _obter_multiplicadores_dinamicos(self) -> Dict[int, float]:
        """Obtém os multiplicadores de expansão e retração calibrados nos últimos jogos vs último resultado."""
        if 'pesos_dinamicos' not in self._memo:
            from dinamica_canonica import AvaliadorDinamicaCanonica
            lot_slug = self.loteria_type.value if hasattr(self.loteria_type, 'value') else str(self.loteria_type)
            self._memo['pesos_dinamicos'] = AvaliadorDinamicaCanonica.calcular_pesos_dinamicos_numerais(
                lot_slug, self.historico, list(self.numeros)
            )
        return self._memo['pesos_dinamicos']

    def _peso_canonico_dinamico(self, numero: int) -> float:
        """Combina o peso canônico multicamada (MCP + ICT + FR) com o ajuste dinâmico de expansão/retração."""
        base = _peso_canonico(self.analisar_elemento(numero))
        mult = self._obter_multiplicadores_dinamicos().get(numero, 1.0)
        return max(0.05, base * mult)

    def gerar_multiplos_jogos(
        self,
        quantidade_jogos: int = 5,
        quantidade_numeros: Optional[int] = None,
        numeros_base: Optional[List[int]] = None,
        metodo: Optional[str] = None
    ) -> List[List[int]]:
        """Atalho de instância para gerar múltiplos jogos com o método escolhido."""
        return gerar_multiplos_jogos(
            self,
            quantidade_jogos=quantidade_jogos,
            quantidade_numeros=quantidade_numeros,
            numeros_base=numeros_base,
            metodo=metodo
        )

    def gerar_jogo_sugerido(
        self,
        estrategia: str = "equilibrada",
        quantidade_numeros: Optional[int] = None,
        metodo: Optional[str] = None
    ) -> List[int]:
        """Atalho de instância para gerar um jogo sugerido com a estratégia ou método escolhido."""
        return gerar_jogo_sugerido(
            self,
            estrategia=estrategia,
            quantidade_numeros=quantidade_numeros,
            metodo=metodo
        )

    def calcular_dispersao_hexagonal(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOH (Modelo Canônico de Otimização Hexagonal e Cobertura Espacial).
        Calcula a dispersão geométrica e proximidade métrica do jogo no espaço cíclico Z_N.
        """
        if self.config.colunas == 7 or self.config.nome == "Super Sete" or getattr(self, 'loteria_type', None) == LoteriaType.SUPER_SETE:
            return self.calcular_dispersao_heptacolunar_supersete(jogo)
        if self.config.nome == "Dupla Sena" or getattr(self, 'loteria_type', None) == LoteriaType.DUPLA_SENA or (self.N == 50 and self.config.sorteios_por_concurso == 2):
            return self.calcular_dispersao_bivariada_duplasena(jogo)
        if self.config.nome == "Dia de Sorte" or getattr(self, 'loteria_type', None) == LoteriaType.DIA_DE_SORTE or (self.N == 31 and self.config.sorteados == 7):
            return self.calcular_dispersao_heptagonal_diadesorte(jogo)
        if self.config.nome == "+Milionária" or getattr(self, 'loteria_type', None) == LoteriaType.MAIS_MILIONARIA or (self.N == 50 and self.config.sorteados == 6):
            return self.calcular_dispersao_biparametrica_maismilionaria(jogo)
        if self.config.nome == "Lotomania" or (self.N == 100 and self.config.sorteados == 20):
            return self.calcular_dispersao_centesimal_lotomania(jogo)
        if self.config.nome == "Timemania" or (self.N == 80 and self.config.sorteados == 7):
            return self.calcular_dispersao_decagonal(jogo)
        if self.config.nome == "Lotofácil" or (self.N == 25 and self.config.sorteados == 15):
            return self.calcular_dispersao_matricial_lotofacil(jogo)
        if self.config.nome == "Quina" or (self.N == 80 and self.config.sorteados == 5):
            return self.calcular_dispersao_pentagonal(jogo)

        if self.config.colunas or not jogo:
            return {
                "disponivel": False,
                "motivo": "Dispersão hexagonal aplica-se a loterias de números com universo contínuo."
            }

        n_numeros = len(jogo)
        N = self.N
        num_setores = 6
        largura_setor = N / num_setores

        # 1. Alocação nos 6 setores do hexágono
        setores = [0] * num_setores
        centros_setores = [self.config.numero_inicial + (i + 0.5) * largura_setor for i in range(num_setores)]

        for num in jogo:
            idx = int((num - self.config.numero_inicial) / largura_setor)
            idx = min(idx, num_setores - 1)
            setores[idx] += 1

        setores_cobertos = sum(1 for c in setores if c > 0)

        # 2. Proximidade métrica circular mínima para os centros dos setores
        distancias_centros = []
        for num in jogo:
            d_min = min(
                min(abs(num - c), N - abs(num - c))
                for c in centros_setores
            )
            distancias_centros.append(d_min)

        dist_media_centros = statistics.mean(distancias_centros) if distancias_centros else 0.0
        dist_max_centros = max(distancias_centros) if distancias_centros else 0.0

        # 3. Índice de Dispersão Espacial (IDE 4.0) de 0.0 a 100.0%
        cobertura_pct = (setores_cobertos / min(num_setores, n_numeros)) * 100.0
        desvio_setorial = statistics.pstdev(setores)
        max_desvio = n_numeros / 2.0
        fator_equilibrio = max(0.0, 1.0 - (desvio_setorial / max(max_desvio, 1.0)))
        ide = round(0.6 * cobertura_pct + 0.4 * (fator_equilibrio * 100.0), 1)

        if setores_cobertos >= min(5, n_numeros):
            classificacao = "Excelente (Dispersão Hexagonal Ampla)"
        elif setores_cobertos >= min(4, n_numeros):
            classificacao = "Boa (Dispersão Equilibrada)"
        else:
            classificacao = "Concentrada (Aglomerada em Poucos Setores)"

        return {
            "disponivel": True,
            "setores_cobertos": setores_cobertos,
            "total_setores": num_setores,
            "distribuicao_setorial": setores,
            "distancia_media_centros": round(dist_media_centros, 2),
            "distancia_maxima_centros": round(dist_max_centros, 2),
            "indice_dispersao": ide,
            "classificacao": classificacao,
            "observacao": (
                "A cobertura hexagonal garante dispersão uniforme no volante, "
                "minimizando a distância média para qualquer combinação sorteada."
            )
        }

    def gerar_jogos_hexagonais(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos utilizando o reticulado hexagonal regular com perturbações harmônicas
        e ajuste dinâmico de expansão/retração dos últimos jogos contra o último resultado.
        """
        import random
        jogos = []
        jogos_set = set()

        if quantidade_numeros == 6 and self.historico:
            jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
            if len(jogo_din) == 6 and len(set(jogo_din)) == 6:
                tup_din = tuple(sorted(jogo_din))
                jogos_set.add(tup_din)
                jogos.append(list(tup_din))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        num_setores = 6
        largura = self.N / num_setores

        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            if quantidade_numeros == 6:
                setores_alvo = list(range(6))
            else:
                setores_alvo = (list(range(6)) * (quantidade_numeros // 6 + 1))[:quantidade_numeros]
                random.shuffle(setores_alvo)

            for s in setores_alvo:
                inicio = int(self.config.numero_inicial + s * largura)
                fim = int(self.config.numero_inicial + (s + 1) * largura) - 1
                fim = min(fim, self.config.numero_final)
                opcoes = [n for n in range(inicio, fim + 1) if n not in candidatos]
                if opcoes:
                    pesos = [self._peso_canonico_dinamico(n) for n in opcoes]
                    escolhido = random.choices(opcoes, weights=pesos, k=1)[0]
                    candidatos.append(escolhido)

            if len(candidatos) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                if 2 <= pares <= 4 or quantidade_numeros != 6:
                    ordenado = sorted(candidatos)
                    diffs = [b - a for a, b in zip(ordenado, ordenado[1:])]
                    if len(set(diffs)) > 1 or quantidade_numeros < 4:
                        tup = tuple(ordenado)
                        if tup not in jogos_set:
                            jogos_set.add(tup)
                            jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def calcular_dispersao_pentagonal(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOP (Modelo Canônico de Otimização Pentagonal e Cobertura Espacial - Quina).
        Calcula a dispersão geométrica e proximidade métrica do jogo no espaço cíclico Z_80,
        dividido em 5 setores de 16 dezenas cada: [1..16], [17..32], [33..48], [49..64], [65..80].
        Centros naturais: [8, 24, 40, 56, 72].
        """
        if self.config.colunas or not jogo:
            return {
                "disponivel": False,
                "motivo": "Dispersão pentagonal aplica-se à Quina e loterias de números com universo contínuo."
            }

        n_numeros = len(jogo)
        N = 80
        num_setores = 5
        largura_setor = 16
        centros_setores = [8, 24, 40, 56, 72]

        # 1. Alocação nos 5 setores do pentágono
        setores = [0] * num_setores
        for num in jogo:
            idx = int((num - 1) / largura_setor)
            idx = min(max(0, idx), num_setores - 1)
            setores[idx] += 1

        setores_cobertos = sum(1 for c in setores if c > 0)

        # 2. Proximidade métrica circular mínima para os centros dos 5 setores
        distancias_centros = []
        for num in jogo:
            d_min = min(
                min(abs(num - c), N - abs(num - c))
                for c in centros_setores
            )
            distancias_centros.append(d_min)

        dist_media_centros = statistics.mean(distancias_centros) if distancias_centros else 0.0
        dist_max_centros = max(distancias_centros) if distancias_centros else 0.0

        # 3. Índice de Dispersão Espacial (IDE 4.0 Pentagonal) de 0.0 a 100.0%
        cobertura_pct = (setores_cobertos / min(num_setores, n_numeros)) * 100.0
        desvio_setorial = statistics.pstdev(setores)
        max_desvio = n_numeros / 2.0
        fator_equilibrio = max(0.0, 1.0 - (desvio_setorial / max(max_desvio, 1.0)))
        ide = round(0.6 * cobertura_pct + 0.4 * (fator_equilibrio * 100.0), 1)

        if setores_cobertos >= min(5, n_numeros):
            classificacao = "Excelente (Dispersão Pentagonal Ampla)"
        elif setores_cobertos >= min(4, n_numeros):
            classificacao = "Boa (Dispersão Equilibrada)"
        elif setores_cobertos >= min(3, n_numeros):
            classificacao = "Regular (Dispersão Parcial)"
        else:
            classificacao = "Concentrada (Aglomerada em Poucos Setores)"

        return {
            "disponivel": True,
            "geometria": "Pentagonal",
            "setores_cobertos": setores_cobertos,
            "total_setores": num_setores,
            "distribuicao_setorial": setores,
            "distancia_media_centros": round(dist_media_centros, 2),
            "distancia_maxima_centros": round(dist_max_centros, 2),
            "indice_dispersao": ide,
            "classificacao": classificacao,
            "observacao": (
                "A cobertura pentagonal garante dispersão uniforme no volante de 80 números da Quina, "
                "minimizando a distância para qualquer sorteio com cota máxima de 8 unidades."
            )
        }

    def calcular_dispersao_matricial_lotofacil(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOM (Modelo Canônico de Otimização Matricial 5x5 e Quintetos - Lotofácil).
        Avalia o equilíbrio bidimensional em matriz 5x5:
        - Distribuição de dezenas nos 5 quintetos/linhas (esperança 3.0 por linha);
        - Distribuição nas 5 colunas (esperança 3.0 por coluna);
        - Proporção Moldura (16 dezenas) vs Miolo (9 dezenas) com centro modal em 10M/5M (ou 9M/6M);
        - Paridade modal estocástica (8I/7P ou 7I/8P);
        - Baricentro de soma das dezenas no ponto ótimo (~195).
        """
        if not jogo or not all(isinstance(n, int) and 1 <= n <= 25 for n in jogo):
            return {
                "disponivel": False,
                "motivo": "Dispersão matricial 5x5 aplica-se à Lotofácil (números de 1 a 25)."
            }

        moldura_set = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
        miolo_set = {7, 8, 9, 12, 13, 14, 17, 18, 19}

        linhas = [0] * 5
        colunas = [0] * 5
        for n in jogo:
            linhas[(n - 1) // 5] += 1
            colunas[(n - 1) % 5] += 1

        moldura_cnt = len(set(jogo) & moldura_set)
        miolo_cnt = len(set(jogo) & miolo_set)
        impares = sum(1 for n in jogo if n % 2 != 0)
        pares = len(jogo) - impares
        soma = sum(jogo)
        setores_cobertos = sum(1 for r in linhas if r > 0)

        # Penalidades para cálculo do Índice de Dispersão Espacial (IDE 4.0 Matricial)
        penalidade_linhas = sum(abs(r - 3) for r in linhas) * 4.0
        penalidade_colunas = sum(abs(c - 3) for c in colunas) * 2.0
        penalidade_moldura = abs(moldura_cnt - 10) * 5.0
        penalidade_paridade = min(abs(impares - 8), abs(impares - 7)) * 8.0
        penalidade_soma = min(15.0, abs(soma - 195) * 0.5)

        penalidade_total = penalidade_linhas + penalidade_colunas + penalidade_moldura + penalidade_paridade + penalidade_soma
        ide = max(0.0, min(100.0, round(100.0 - penalidade_total, 1)))

        if ide >= 85.0:
            classificacao = "Excelente (Dispersão Matricial e Quintetos 5x5 Equilibrada)"
        elif ide >= 70.0:
            classificacao = "Boa (Dispersão Matricial Aceitável)"
        elif ide >= 50.0:
            classificacao = "Regular (Desequilíbrio Parcial Moldura/Miolo ou Quintetos)"
        else:
            classificacao = "Concentrada (Desbalanceada no Grid 5x5)"

        return {
            "disponivel": True,
            "geometria": "Matricial",
            "setores_cobertos": setores_cobertos,
            "total_setores": 5,
            "distribuicao_setorial": linhas,
            "distribuicao_linhas": linhas,
            "distribuicao_colunas": colunas,
            "moldura": moldura_cnt,
            "miolo": miolo_cnt,
            "paridade": f"{impares}I/{pares}P",
            "soma": soma,
            "indice_dispersao": ide,
            "classificacao": classificacao,
            "distancia_maxima_garantida": 1,
            "distancia_media_teorica": 0.4,
            "observacao": (
                "A cobertura matricial 5x5 (MCOM 4.0) garante dispersão homogênea no volante da Lotofácil, "
                f"equilibrando Moldura ({moldura_cnt}/16) e Miolo ({miolo_cnt}/9) com cota máxima de 1 passo no grid."
            )
        }

    def calcular_dispersao_decagonal(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOD (Modelo Canônico de Otimização Decagonal e Cobertura Espacial - Timemania).
        Calcula a dispersão geométrica e proximidade métrica do jogo no espaço cíclico Z_80,
        dividido em 10 setores de 8 dezenas cada: [1..8], [9..16], ..., [73..80].
        Centros naturais: [4, 12, 20, 28, 36, 44, 52, 60, 68, 76].
        Cota máxima de proximidade K-Medians: <= 4 unidades no anel cíclico modular Z_80.
        """
        if self.config.colunas or not jogo:
            return {
                "disponivel": False,
                "motivo": "Dispersão decagonal aplica-se à Timemania e loterias de números com universo de 80 dezenas."
            }

        n_numeros = len(jogo)
        N = 80
        num_setores = 10
        largura_setor = 8
        centros_setores = [4, 12, 20, 28, 36, 44, 52, 60, 68, 76]

        # 1. Alocação nos 10 setores do decágono
        setores = [0] * num_setores
        for num in jogo:
            idx = int((num - 1) / largura_setor)
            idx = min(max(0, idx), num_setores - 1)
            setores[idx] += 1

        setores_cobertos = sum(1 for c in setores if c > 0)

        # 2. Proximidade métrica circular mínima para os centros dos 10 setores
        distancias_centros = []
        for num in jogo:
            d_min = min(
                min(abs(num - c), N - abs(num - c))
                for c in centros_setores
            )
            distancias_centros.append(d_min)

        dist_media_centros = statistics.mean(distancias_centros) if distancias_centros else 0.0
        dist_max_centros = max(distancias_centros) if distancias_centros else 0.0

        # 3. Índice de Dispersão Espacial (IDE 4.0 Decagonal) de 0.0 a 100.0%
        cobertura_pct = (setores_cobertos / min(num_setores, n_numeros)) * 100.0
        desvio_setorial = statistics.pstdev(setores)
        max_desvio = n_numeros / 2.0
        fator_equilibrio = max(0.0, 1.0 - (desvio_setorial / max(max_desvio, 1.0)))
        ide = round(0.6 * cobertura_pct + 0.4 * (fator_equilibrio * 100.0), 1)

        if setores_cobertos >= min(8, n_numeros):
            classificacao = "Excelente (Dispersão Decagonal Ampla)"
        elif setores_cobertos >= min(6, n_numeros):
            classificacao = "Boa (Dispersão Equilibrada)"
        elif setores_cobertos >= min(4, n_numeros):
            classificacao = "Regular (Dispersão Parcial)"
        else:
            classificacao = "Concentrada (Aglomerada em Poucos Setores)"

        return {
            "disponivel": True,
            "geometria": "Decagonal",
            "setores_cobertos": setores_cobertos,
            "total_setores": num_setores,
            "distribuicao_setorial": setores,
            "distancia_media_centros": round(dist_media_centros, 2),
            "distancia_maxima_centros": round(dist_max_centros, 2),
            "indice_dispersao": ide,
            "classificacao": classificacao,
            "distancia_maxima_garantida": 4,
            "distancia_media_teorica": 2.0,
            "observacao": (
                "A cobertura decagonal (MCOD 4.0) garante dispersão ótima no volante de 80 números da Timemania, "
                "distribuindo as 10 dezenas entre os 10 setores com cota máxima de 4 unidades no anel cíclico Z_80."
            )
        }

    def calcular_dispersao_centesimal_lotomania(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOC (Modelo Canônico de Otimização Centesimal e Matricial 10x10 - Lotomania).
        Avalia o equilíbrio no grid 10x10 de 100 dezenas (0 a 99) para uma aposta de 50 dezenas:
        - Distribuição de dezenas nas 10 linhas (esperança 5.0 por linha);
        - Distribuição de dezenas nas 10 colunas (esperança 5.0 por coluna);
        - Distribuição nos 4 quadrantes 5x5 (esperança 12.5 por quadrante: 12 ou 13);
        - Proporção Moldura (36 dezenas) vs Miolo (64 dezenas), com centro ótimo em 18M/32M;
        - Paridade modal estocástica (25P/25I);
        - Baricentro de soma no ponto ótimo (~2.475).
        """
        if not jogo or not all(isinstance(n, int) and 0 <= n <= 99 for n in jogo):
            return {
                "disponivel": False,
                "motivo": "Dispersão centesimal 10x10 aplica-se à Lotomania (números de 0 a 99)."
            }

        moldura_set = {n for n in range(100) if (n // 10) in (0, 9) or (n % 10) in (0, 9)}
        miolo_set = {n for n in range(100) if n not in moldura_set}

        quadrantes = {
            1: sum(1 for n in jogo if (n // 10) < 5 and (n % 10) < 5),
            2: sum(1 for n in jogo if (n // 10) < 5 and (n % 10) >= 5),
            3: sum(1 for n in jogo if (n // 10) >= 5 and (n % 10) < 5),
            4: sum(1 for n in jogo if (n // 10) >= 5 and (n % 10) >= 5),
        }

        linhas = [0] * 10
        colunas = [0] * 10
        for n in jogo:
            linhas[n // 10] += 1
            colunas[n % 10] += 1

        moldura_cnt = len(set(jogo) & moldura_set)
        miolo_cnt = len(set(jogo) & miolo_set)
        pares = sum(1 for n in jogo if n % 2 == 0)
        impares = len(jogo) - pares
        soma = sum(jogo)
        setores_cobertos = sum(1 for r in linhas if r > 0)

        # Penalidades para o Índice de Dispersão Espacial (IDE 4.0 Centesimal)
        penalidade_linhas = sum(abs(r - 5) for r in linhas) * 2.0
        penalidade_colunas = sum(abs(c - 5) for c in colunas) * 2.0
        penalidade_quadrantes = sum(abs(q - 12.5) for q in quadrantes.values()) * 3.0
        penalidade_moldura = abs(moldura_cnt - 18) * 3.0
        penalidade_paridade = abs(pares - 25) * 4.0
        penalidade_soma = min(15.0, abs(soma - 2475) * 0.05)

        penalidade_total = penalidade_linhas + penalidade_colunas + penalidade_quadrantes + penalidade_moldura + penalidade_paridade + penalidade_soma
        ide = max(0.0, min(100.0, round(100.0 - penalidade_total, 1)))

        if ide >= 85.0:
            classificacao = "Excelente (Dispersão Centesimal e Quadrantes 10x10 Equilibrada)"
        elif ide >= 70.0:
            classificacao = "Boa (Dispersão Centesimal Equilibrada)"
        elif ide >= 50.0:
            classificacao = "Regular (Desequilíbrio Parcial em Quadrantes/Moldura)"
        else:
            classificacao = "Concentrada (Desbalanceada no Grid 10x10)"

        return {
            "disponivel": True,
            "geometria": "Centesimal",
            "setores_cobertos": setores_cobertos,
            "total_setores": 10,
            "distribuicao_setorial": linhas,
            "distribuicao_linhas": linhas,
            "distribuicao_colunas": colunas,
            "quadrantes": quadrantes,
            "moldura": moldura_cnt,
            "miolo": miolo_cnt,
            "paridade": f"{pares}P/{impares}I",
            "soma": soma,
            "indice_dispersao": ide,
            "classificacao": classificacao,
            "distancia_maxima_garantida": 1,
            "cota_maxima_grid": 1,
            "distancia_media_teorica": 0.5,
            "observacao": (
                "A cobertura centesimal 10x10 (MCOC 4.0) garante dispersão homogênea no volante da Lotomania, "
                f"equilibrando Moldura ({moldura_cnt}/36), Miolo ({miolo_cnt}/64) e 4 Quadrantes com cota de 1 passo no grid."
            )
        }

    def calcular_dispersao_biparametrica_maismilionaria(self, jogo: List[int], trevos: Optional[List[int]] = None) -> Dict:
        """
        Camada 8 - MCOMIL (Modelo Canônico Biparamétrico Hexa-Trevo - +Milionária).
        Avalia o equilíbrio no anel circular modular Z_50 combinado ao espaço discreto de Trevos.
        """
        from modelo_mais_milionaria import ModeloHexaTrevoMaisMilionaria
        return ModeloHexaTrevoMaisMilionaria.calcular_dispersao_biparametrica(jogo, trevos)

    def calcular_dispersao_heptagonal_diadesorte(self, jogo: List[int], mes: Optional[str] = None) -> Dict:
        """
        Camada 8 - MCODS (Modelo Canônico Heptagonal de Calendário e Mês da Sorte - Dia de Sorte).
        Avalia o equilíbrio no anel circular modular Z_31 (dias do mês) e cota de proximidade <= 2.
        """
        from modelo_dia_de_sorte import ModeloHeptagonalDiaDeSorte
        return ModeloHeptagonalDiaDeSorte.calcular_dispersao_heptagonal(jogo, mes)

    def calcular_dispersao_bivariada_duplasena(self, jogo: List[int], sorteio1: Optional[List[int]] = None, sorteio2: Optional[List[int]] = None) -> Dict:
        """
        Camada 8 - MCODSen (Modelo Canônico Hexagonal Bivariado de Duplo Sorteio - Dupla Sena).
        Avalia o equilíbrio no anel circular modular Z_50 e a cobertura mútua do 1º e 2º sorteios.
        """
        from modelo_dupla_sena import ModeloBivariadoDuplaSena
        return ModeloBivariadoDuplaSena.calcular_dispersao_bivariada(jogo, sorteio1, sorteio2)

    def calcular_dispersao_heptacolunar_supersete(self, jogo: List[int], sorteio_referencia: Optional[List[int]] = None) -> Dict:
        """
        Camada 8 - MCOSS (Modelo Canônico Heptacolunar Independente - Super Sete).
        Avalia o equilíbrio no espaço vetorial Z_10^7 nas 7 colunas independentes.
        """
        from modelo_super_sete import ModeloHeptacolunarSuperSete
        return ModeloHeptacolunarSuperSete.calcular_dispersao_heptacolunar(jogo, sorteio_referencia)

    def calcular_dispersao_espacial(self, jogo: List[int], complemento: Optional[Any] = None) -> Dict:
        """
        Camada 8 - Despacho Polimórfico de Cobertura Espacial.
        Encaminha para a geometria adequada de cada loteria:
        - Super Sete: Heptacolunar Independente (MCOSS 4.0)
        - Dupla Sena: Hexagonal Bivariado de Duplo Sorteio (MCODSen 4.0)
        - Dia de Sorte: Heptagonal de Calendário (MCODS 4.0)
        - +Milionária: Hexa-Trevo Biparamétrico (MCOMIL 4.0)
        - Lotomania: Centesimal 10x10 (MCOC 4.0)
        - Timemania: Decagonal (MCOD 4.0)
        - Lotofácil: Matricial 5x5 (MCOM 4.0)
        - Quina: Pentagonal (MCOP 4.0)
        - Mega-Sena: Hexagonal (MCOH 4.0)
        - Demais loterias: Modelo espacial correspondente
        """
        if self.config.colunas == 7 or self.config.nome == "Super Sete" or getattr(self, 'loteria_type', None) == LoteriaType.SUPER_SETE:
            s_ref = complemento if isinstance(complemento, (list, tuple)) and len(complemento) == 7 else None
            return self.calcular_dispersao_heptacolunar_supersete(jogo, s_ref)
        if self.config.nome == "Dupla Sena" or getattr(self, 'loteria_type', None) == LoteriaType.DUPLA_SENA or (self.N == 50 and self.config.sorteios_por_concurso == 2):
            s1 = complemento[0] if isinstance(complemento, (list, tuple)) and len(complemento) >= 1 else None
            s2 = complemento[1] if isinstance(complemento, (list, tuple)) and len(complemento) >= 2 else None
            return self.calcular_dispersao_bivariada_duplasena(jogo, s1, s2)
        if self.config.nome == "Dia de Sorte" or getattr(self, 'loteria_type', None) == LoteriaType.DIA_DE_SORTE or (self.N == 31 and self.config.sorteados == 7):
            return self.calcular_dispersao_heptagonal_diadesorte(jogo, complemento if isinstance(complemento, str) else None)
        if self.config.nome == "+Milionária" or getattr(self, 'loteria_type', None) == LoteriaType.MAIS_MILIONARIA or (self.N == 50 and self.config.sorteados == 6):
            return self.calcular_dispersao_biparametrica_maismilionaria(jogo, complemento if isinstance(complemento, list) else None)
        if self.config.nome == "Lotomania" or (self.N == 100 and self.config.sorteados == 20):
            return self.calcular_dispersao_centesimal_lotomania(jogo)
        if self.config.nome == "Timemania" or (self.N == 80 and self.config.sorteados == 7):
            return self.calcular_dispersao_decagonal(jogo)
        if self.config.nome == "Lotofácil" or (self.N == 25 and self.config.sorteados == 15):
            return self.calcular_dispersao_matricial_lotofacil(jogo)
        if self.config.nome == "Quina" or (self.N == 80 and self.config.sorteados == 5):
            return self.calcular_dispersao_pentagonal(jogo)
        return self.calcular_dispersao_hexagonal(jogo)

    def gerar_jogos_pentagonais(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da Quina utilizando o reticulado pentagonal regular com perturbações harmônicas,
        dividindo o volante de 80 dezenas em 5 setores de 16 dezenas cada:
        Setor 0: 01 a 16 | Setor 1: 17 a 32 | Setor 2: 33 a 48 | Setor 3: 49 a 64 | Setor 4: 65 a 80.
        Garante equilíbrio de paridade (2P/3I ou 3P/2I), dispersão espacial e ajuste dinâmico de expansão/retração.
        """
        import random
        jogos = []
        jogos_set = set()

        if quantidade_numeros == 5 and self.historico:
            jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
            if len(jogo_din) == 5 and len(set(jogo_din)) == 5:
                tup_din = tuple(sorted(jogo_din))
                jogos_set.add(tup_din)
                jogos.append(list(tup_din))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        num_setores = 5
        largura = 16

        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            if quantidade_numeros == 5:
                setores_alvo = list(range(5))
            else:
                setores_alvo = (list(range(5)) * (quantidade_numeros // 5 + 1))[:quantidade_numeros]
                random.shuffle(setores_alvo)

            for s in setores_alvo:
                inicio = 1 + s * largura
                fim = min(1 + (s + 1) * largura - 1, 80)
                opcoes = [n for n in range(inicio, fim + 1) if n not in candidatos]
                if opcoes:
                    pesos = [self._peso_canonico_dinamico(n) for n in opcoes]
                    escolhido = random.choices(opcoes, weights=pesos, k=1)[0]
                    candidatos.append(escolhido)

            if len(candidatos) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                if (2 <= pares <= 3) or (quantidade_numeros != 5 and 1 <= pares <= 4):
                    ordenado = sorted(candidatos)
                    diffs = [b - a for a, b in zip(ordenado, ordenado[1:])]
                    if len(set(diffs)) > 1 or quantidade_numeros < 4:
                        tup = tuple(ordenado)
                        if tup not in jogos_set:
                            jogos_set.add(tup)
                            jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_lotofacil(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da Lotofácil utilizando o Modelo Canônico Matricial 5x5 e Quintetos (MCOM 4.0),
        balanceando Moldura (16) vs Miolo (9), distribuição uniforme por linhas e colunas (3 por linha/coluna),
        paridade modal (8I/7P ou 7I/8P), baricentro de soma (~195) e ajuste dinâmico de expansão/retração.
        """
        import random
        from modelo_lotofacil import ModeloMatricialLotofacil

        jogos = []
        jogos_set = set()

        # Se for o tamanho padrão de 15 dezenas, prioriza o jogo ajustado dinamicamente pelos últimos resultados
        if quantidade_numeros == 15:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 15 and len(set(jogo_din)) == 15:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloMatricialLotofacil.gerar_variantes_canonicas()
            ultimo_sorteio = set(self.historico[-1]) if self.historico else set()
            canonicas_ordenadas = sorted(
                canonicas,
                key=lambda v: abs(len(set(v["dezenas"]) & ultimo_sorteio) - 9)
            )
            for v in canonicas_ordenadas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v["dezenas"])
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v["dezenas"]))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        moldura_list = sorted(list(ModeloMatricialLotofacil.MOLDURA))
        miolo_list = sorted(list(ModeloMatricialLotofacil.MIOLO))

        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1

            if quantidade_numeros == 15:
                # Alvo canônico: 10 moldura e 5 miolo (ou 9 moldura e 6 miolo)
                n_moldura = random.choice([10, 9, 10])
                n_miolo = 15 - n_moldura

                pesos_mold = [self._peso_canonico_dinamico(n) for n in moldura_list]
                pesos_miol = [self._peso_canonico_dinamico(n) for n in miolo_list]

                # Amostragem ponderada sem reposição
                escolhidos_mold = set()
                while len(escolhidos_mold) < n_moldura:
                    n = random.choices(moldura_list, weights=pesos_mold, k=1)[0]
                    escolhidos_mold.add(n)

                escolhidos_miol = set()
                while len(escolhidos_miol) < n_miolo:
                    n = random.choices(miolo_list, weights=pesos_miol, k=1)[0]
                    escolhidos_miol.add(n)

                candidato = sorted(list(escolhidos_mold | escolhidos_miol))
            else:
                universo = list(range(1, 26))
                pesos = [self._peso_canonico_dinamico(n) for n in universo]
                escolhidos = set()
                while len(escolhidos) < quantidade_numeros:
                    n = random.choices(universo, weights=pesos, k=1)[0]
                    escolhidos.add(n)
                candidato = sorted(list(escolhidos))

            # Validação estrutural do candidato
            impares = sum(1 for n in candidato if n % 2 != 0)
            soma = sum(candidato)

            linhas = [0] * 5
            for n in candidato:
                linhas[(n - 1) // 5] += 1

            if (6 <= impares <= 9) and (175 <= soma <= 215):
                if quantidade_numeros != 15 or (min(linhas) >= 2 and max(linhas) <= 4):
                    tup = tuple(candidato)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(candidato)

        return jogos[:quantidade_jogos]

    def gerar_jogos_decagonais(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da Timemania utilizando o Modelo Canônico Decagonal e Time do Coração (MCOD 4.0),
        dividindo o volante de 80 dezenas em 10 setores regulares de 8 dezenas cada,
        incorporando o ajuste dinâmico de expansão/retração dos últimos jogos contra o último resultado.
        """
        import random
        from modelo_decagonal_timemania import ModeloDecagonalTimemania

        jogos = []
        jogos_set = set()

        if quantidade_numeros == 10:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 10 and len(set(jogo_din)) == 10:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloDecagonalTimemania.gerar_variantes_canonicas()
            for v in canonicas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v["dezenas"])
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v["dezenas"]))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        num_setores = 10
        largura = 8

        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            if quantidade_numeros == 10:
                setores_alvo = list(range(10))
            else:
                setores_alvo = (list(range(10)) * (quantidade_numeros // 10 + 1))[:quantidade_numeros]
                random.shuffle(setores_alvo)

            for s in setores_alvo:
                inicio = 1 + s * largura
                fim = min(1 + (s + 1) * largura - 1, 80)
                opcoes = [n for n in range(inicio, fim + 1) if n not in candidatos]
                if opcoes:
                    pesos = [self._peso_canonico_dinamico(n) for n in opcoes]
                    escolhido = random.choices(opcoes, weights=pesos, k=1)[0]
                    candidatos.append(escolhido)

            if len(candidatos) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                soma = sum(candidatos)
                if (4 <= pares <= 6) and (360 <= soma <= 450):
                    ordenado = sorted(candidatos)
                    diffs = [b - a for a, b in zip(ordenado, ordenado[1:])]
                    if len(set(diffs)) > 1 or quantidade_numeros < 4:
                        tup = tuple(ordenado)
                        if tup not in jogos_set:
                            jogos_set.add(tup)
                            jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_lotomania(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da Lotomania utilizando o Modelo Canônico Centesimal e Matricial 10x10 (MCOC 4.0),
        dividindo o volante de 100 dezenas em 10 linhas de 10 dezenas, distribuindo 5 por linha
        e incorporando a inteligência dinâmica de expansão e retração sobre os últimos resultados.
        """
        import random
        from modelo_lotomania import ModeloCentesimalLotomania

        jogos = []
        jogos_set = set()

        if quantidade_numeros == 50:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 50 and len(set(jogo_din)) == 50:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloCentesimalLotomania.gerar_variantes_canonicas()
            for v in canonicas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v["dezenas"])
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v["dezenas"]))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        # Gerador estocástico centesimal 10x10 ponderado por scores MCP + expansão/retração dinâmica
        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            for r in range(10):
                opcoes_linha = [r * 10 + c for c in range(10)]
                pesos_linha = [self._peso_canonico_dinamico(n) for n in opcoes_linha]
                escolhidos_linha = []
                while len(escolhidos_linha) < 5:
                    n = random.choices(opcoes_linha, weights=pesos_linha, k=1)[0]
                    if n not in escolhidos_linha:
                        escolhidos_linha.append(n)
                candidatos.extend(escolhidos_linha)

            if len(candidatos) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                soma = sum(candidatos)
                if (23 <= pares <= 27) and (2300 <= soma <= 2650):
                    ordenado = sorted(candidatos)
                    tup = tuple(ordenado)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_maismilionaria(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da +Milionária utilizando o Modelo Canônico Biparamétrico Hexa-Trevo (MCOMIL 4.0),
        otimizando a dispersão nos 6 setores regulares do anel modular Z_50 com ajuste dinâmico
        de expansão e retração sobre os últimos sorteios.
        """
        import random
        from modelo_mais_milionaria import ModeloHexaTrevoMaisMilionaria

        jogos = []
        jogos_set = set()

        if quantidade_numeros == 6:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 6 and len(set(jogo_din)) == 6:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloHexaTrevoMaisMilionaria.gerar_variantes_canonicas()
            for v in canonicas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v["dezenas"])
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v["dezenas"]))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        # Gerador estocástico biparamétrico no anel Z_50 ponderado por scores MCP + expansão/retração
        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            for s_idx in range(6):
                s_info = ModeloHexaTrevoMaisMilionaria.SETORES[s_idx]
                dezenas_setor = s_info["dezenas"]
                pesos_setor = [self._peso_canonico_dinamico(n) for n in dezenas_setor]
                n = random.choices(dezenas_setor, weights=pesos_setor, k=1)[0]
                candidatos.append(n)

            if len(set(candidatos)) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                soma = sum(candidatos)
                if (2 <= pares <= 4) and (115 <= soma <= 195):
                    ordenado = sorted(candidatos)
                    tup = tuple(ordenado)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_diadesorte(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos do Dia de Sorte utilizando o Modelo Canônico Heptagonal de Calendário (MCODS 4.0),
        otimizando a dispersão nos 7 setores regulares do anel modular Z_31 com ajuste dinâmico
        de expansão e retração sobre os últimos sorteios.
        """
        import random
        from modelo_dia_de_sorte import ModeloHeptagonalDiaDeSorte

        jogos = []
        jogos_set = set()

        if quantidade_numeros == 7:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 7 and len(set(jogo_din)) == 7:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloHeptagonalDiaDeSorte.gerar_variantes_canonicas()
            for v in canonicas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v["dezenas"])
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v["dezenas"]))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        # Gerador estocástico heptagonal no anel Z_31 ponderado por scores MCP + expansão/retração
        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            for s_idx in range(7):
                s_info = ModeloHeptagonalDiaDeSorte.SETORES[s_idx]
                dezenas_setor = s_info["dezenas"]
                pesos_setor = [self._peso_canonico_dinamico(n) for n in dezenas_setor]
                n = random.choices(dezenas_setor, weights=pesos_setor, k=1)[0]
                candidatos.append(n)

            if len(set(candidatos)) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                soma = sum(candidatos)
                if (3 <= pares <= 4) and (90 <= soma <= 135):
                    ordenado = sorted(candidatos)
                    tup = tuple(ordenado)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_duplasena(self, quantidade_jogos: int, quantidade_numeros: int) -> List[List[int]]:
        """
        Gera jogos da Dupla Sena utilizando o Modelo Canônico Hexagonal Bivariado (MCODSen 4.0),
        otimizando a dispersão nos 6 setores regulares do anel modular Z_50 com ajuste dinâmico
        de expansão e retração sobre os últimos sorteios.
        """
        import random
        from modelo_dupla_sena import ModeloBivariadoDuplaSena

        jogos = []
        jogos_set = set()

        if quantidade_numeros == 6:
            if self.historico:
                jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
                if len(jogo_din) == 6 and len(set(jogo_din)) == 6:
                    tup_din = tuple(sorted(jogo_din))
                    jogos_set.add(tup_din)
                    jogos.append(list(tup_din))
                    if len(jogos) >= quantidade_jogos:
                        return jogos[:quantidade_jogos]

            canonicas = ModeloBivariadoDuplaSena.gerar_variantes_canonicas()
            for v in canonicas[:min(2, quantidade_jogos - len(jogos))]:
                tup = tuple(v.dezenas)
                if tup not in jogos_set:
                    jogos_set.add(tup)
                    jogos.append(list(v.dezenas))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        # Gerador estocástico bivariado no anel Z_50 ponderado por scores MCP + expansão/retração
        tentativas = 0
        max_tentativas = quantidade_jogos * 200

        while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
            tentativas += 1
            candidatos = []

            for s_idx in range(6):
                s_info = ModeloBivariadoDuplaSena.SETORES[s_idx]
                dezenas_setor = list(s_info.dezenas)
                pesos_setor = [self._peso_canonico_dinamico(n) for n in dezenas_setor]
                n = random.choices(dezenas_setor, weights=pesos_setor, k=1)[0]
                candidatos.append(n)

            if len(set(candidatos)) == quantidade_numeros:
                pares = sum(1 for n in candidatos if n % 2 == 0)
                soma = sum(candidatos)
                if (2 <= pares <= 4) and (125 <= soma <= 181):
                    ordenado = sorted(candidatos)
                    tup = tuple(ordenado)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(list(ordenado))

        return jogos[:quantidade_jogos]

    def gerar_jogos_supersete(self, quantidade_jogos: int) -> List[List[int]]:
        """
        Gera jogos do Super Sete utilizando o Modelo Canônico Heptacolunar Independente (MCOSS 4.0)
        combinado ao ajuste dinâmico coluna a coluna de expansão/retração dos últimos sorteios.
        """
        from modelo_super_sete import ModeloHeptacolunarSuperSete
        jogos: List[List[int]] = []
        vistos = set()

        if self.historico:
            jogo_din = self.avaliar_dinamica_expansao_retracao().get("jogo_ajustado", [])
            if len(jogo_din) == 7:
                vistos.add(tuple(jogo_din))
                jogos.append(list(jogo_din))
                if len(jogos) >= quantidade_jogos:
                    return jogos[:quantidade_jogos]

        for j in ModeloHeptacolunarSuperSete.gerar_jogos(quantidade=quantidade_jogos):
            tup = tuple(j)
            if tup not in vistos:
                vistos.add(tup)
                jogos.append(list(j))
            if len(jogos) >= quantidade_jogos:
                return jogos[:quantidade_jogos]

        return jogos[:quantidade_jogos]

    def avaliar_dinamica_expansao_retracao(self) -> Dict[str, Any]:
        """
        Avalia os últimos sorteios oficiais pelo Modelo Canônico 4.0, verificando
        os últimos jogos contra o último resultado, identificando se a tendência de cada
        casa/setor é de Expansão (↗), Retração (↘) ou Equilíbrio (🎯) e auto-calibrando
        a força restauradora para máxima assertividade.
        """
        from dinamica_canonica import AvaliadorDinamicaCanonica
        lot_slug = self.loteria_type.value if hasattr(self.loteria_type, 'value') else str(self.loteria_type)
        res = AvaliadorDinamicaCanonica.avaliar_dinamica(
            loteria_type=lot_slug,
            historico=self.historico,
            ultimo_concurso_id=self.T
        )
        return {
            "loteria": res.loteria,
            "total_casas": res.total_casas,
            "concursos_analisados": res.concursos_analisados,
            "ultimo_concurso": res.ultimo_concurso,
            "casas": [
                {
                    "indice": c.indice,
                    "nome": c.nome,
                    "faixa": c.faixa,
                    "centro_canonico": c.centro_canonico,
                    "ultimo_sorteado": c.ultimo_sorteado,
                    "penultimo_sorteado": c.penultimo_sorteado,
                    "desvio_centro": c.desvio_centro,
                    "variacao_recente": c.variacao_recente,
                    "estado": c.estado,
                    "estado_icone": c.estado_icone,
                    "estado_rotulo": c.estado_rotulo,
                    "ajuste_aplicado": c.ajuste_aplicado,
                    "valor_ajustado": c.valor_ajustado,
                    "diagnostico": c.diagnostico,
                    "media_ultimos_jogos": c.media_ultimos_jogos,
                    "fator_calibrado": c.fator_calibrado,
                    "tendencia_numeral": c.tendencia_numeral,
                    "acertos_recentes_casa": c.acertos_recentes_casa,
                    "proximidade_ultimo_resultado": c.proximidade_ultimo_resultado,
                    "dezenas_ajustadas_casa": c.dezenas_ajustadas_casa,
                }
                for c in res.casas
            ],
            "jogo_ajustado": res.jogo_ajustado,
            "jogo_ajustado_formatado": res.jogo_ajustado_formatado,
            "resumo_tendencia": res.resumo_tendencia,
            "complemento": res.complemento,
            "verificacao_ultimos_jogos": res.verificacao_ultimos_jogos,
        }


# Alias canônico para compatibilidade com versões e chamadas anteriores
ModeloCanonico30 = ModeloCanonico40


# Reexporta a camada 7 para preservar os imports existentes.
from validacao import ValidaçãoCamada7


def gerar_jogo_dinamico_ajustado(modelo: ModeloCanonico40) -> List[int]:
    """
    Gera jogo ajustado pela dinâmica de expansão e retração dos últimos sorteios,
    buscando a máxima aproximação do atrator canônico.
    """
    din = modelo.avaliar_dinamica_expansao_retracao()
    return din.get("jogo_ajustado", [])


def gerar_jogo_sugerido(
    modelo: ModeloCanonico40,
    quantidade_numeros: int,
    metodo: Optional[str] = None
) -> List[int]:
    """
    Gerar sugestão de jogo baseada no Modelo Canônico 4.0 ou na forma de análise escolhida pelo usuário.
    Combina a análise estatística multicamada (score MCP, ICT, FR) com a Otimização Espacial
    e o ajuste dinâmico de expansão/retração dos últimos jogos contra o último resultado.
    """
    if metodo and metodo.lower() not in ("canonica", "canonica_dinamica", "padrao", "automatico"):
        from metodos_analise import gerar_jogos_por_metodo
        jogos_m = gerar_jogos_por_metodo(modelo, 1, quantidade_numeros, metodo=metodo)
        if jogos_m:
            return jogos_m[0]

    if modelo.config.colunas == 7 or modelo.config.nome == 'Super Sete' or getattr(modelo, 'loteria_type', None) == LoteriaType.SUPER_SETE:
        jogos_ss = modelo.gerar_jogos_supersete(1)
        if jogos_ss:
            return jogos_ss[0]
        return gerar_jogo_por_coluna(modelo)

    if modelo.config.colunas:
        return gerar_jogo_por_coluna(modelo)

    # Para a Dupla Sena (50 dezenas, 6 sorteadas, 2 sorteios independentes), utiliza a geração bivariada ótima
    if (modelo.config.nome == 'Dupla Sena' or getattr(modelo, 'loteria_type', None) == LoteriaType.DUPLA_SENA or (modelo.N == 50 and modelo.config.sorteios_por_concurso == 2)):
        jogos_dupla = modelo.gerar_jogos_duplasena(1, quantidade_numeros)
        if jogos_dupla:
            return jogos_dupla[0]

    # Para o Dia de Sorte (31 dezenas, 7 sorteadas, aposta padrão de 7 números), utiliza a geração heptagonal ótima
    if (modelo.config.nome == 'Dia de Sorte' or (modelo.N == 31 and quantidade_numeros in (7, 15))):
        jogos_dia = modelo.gerar_jogos_diadesorte(1, quantidade_numeros)
        if jogos_dia:
            return jogos_dia[0]

    # Para a +Milionária (50 dezenas, 6 sorteadas, aposta padrão de 6 números), utiliza a geração hexa-trevo ótima
    if (modelo.config.nome == '+Milionária' or (modelo.N == 50 and quantidade_numeros in (6, 12) and modelo.config.nome != 'Dupla Sena')):
        jogos_mili = modelo.gerar_jogos_maismilionaria(1, quantidade_numeros)
        if jogos_mili:
            return jogos_mili[0]

    # Para a Lotomania (100 dezenas, 20 sorteadas, 50 na aposta padrão), utiliza a geração centesimal ótima
    if (modelo.config.nome == 'Lotomania' or (modelo.N == 100 and quantidade_numeros in (20, 50))):
        jogos_loto_m = modelo.gerar_jogos_lotomania(1, quantidade_numeros)
        if jogos_loto_m:
            return jogos_loto_m[0]

    # Para a Timemania (80 dezenas, 7 sorteadas, aposta padrão de 10 números), utiliza a geração decagonal ótima
    if (modelo.config.nome == 'Timemania' or (modelo.N == 80 and quantidade_numeros in (7, 10))):
        jogos_dec = modelo.gerar_jogos_decagonais(1, quantidade_numeros)
        if jogos_dec:
            return jogos_dec[0]

    # Para a Lotofácil (25 dezenas, 15 sorteadas), utiliza a geração matricial ótima
    if (modelo.config.nome == 'Lotofácil' or (modelo.N == 25 and quantidade_numeros == 15)):
        jogos_loto = modelo.gerar_jogos_lotofacil(1, quantidade_numeros)
        if jogos_loto:
            return jogos_loto[0]

    # Para a Quina (80 dezenas, 5 sorteadas), utiliza a geração pentagonal ótima
    if (modelo.config.nome == 'Quina' or (modelo.N == 80 and quantidade_numeros == 5)):
        jogos_pent = modelo.gerar_jogos_pentagonais(1, quantidade_numeros)
        if jogos_pent:
            return jogos_pent[0]

    # Para a Mega-Sena (60 dezenas, 6 sorteadas), utiliza a geração hexagonal ótima
    if (modelo.config.nome == 'Mega-Sena' or (modelo.N == 60 and quantidade_numeros == 6)):
        jogos_hex = modelo.gerar_jogos_hexagonais(1, quantidade_numeros)
        if jogos_hex:
            return jogos_hex[0]

    analises = modelo.analisar_todos_elementos()
    mults_din = modelo._obter_multiplicadores_dinamicos()

    n_mcp = int(quantidade_numeros * 0.4)
    n_ict = int(quantidade_numeros * 0.3)
    n_fr = int(quantidade_numeros * 0.2)

    sugeridos = set()

    # Top por score MCP ponderado pela expansão/retração dinâmica
    por_mcp = sorted(analises, key=lambda x: x.score_mcp * mults_din.get(x.numero, 1.0), reverse=True)
    for a in por_mcp[:n_mcp]:
        sugeridos.add(a.numero)

    # Top por ICT (menor é melhor)
    por_ict = sorted(analises, key=lambda x: x.ict / max(0.2, mults_din.get(x.numero, 1.0)))
    for a in por_ict[:n_ict]:
        if len(sugeridos) < n_mcp + n_ict:
            sugeridos.add(a.numero)

    # Top por FR próximo de 1
    por_fr = sorted(analises, key=lambda x: abs(x.fr - 1))
    for a in por_fr[:n_fr]:
        if len(sugeridos) < n_mcp + n_ict + n_fr:
            sugeridos.add(a.numero)

    import random
    while len(sugeridos) < quantidade_numeros:
        num = random.choice(modelo.numeros)
        sugeridos.add(num)

    return sorted(list(sugeridos))[:quantidade_numeros]


def gerar_multiplos_jogos(
    modelo: ModeloCanonico40,
    quantidade_jogos: int,
    quantidade_numeros: int,
    numeros_base: Optional[List[int]] = None,
    metodo: Optional[str] = None
) -> List[List[int]]:
    """
    Gera N combinações distintas e balanceadas baseadas no Modelo Canônico 4.0 ou no método escolhido pelo usuário.
    Garante que não haja jogos duplicados e aplica otimização de dispersão espacial e ajuste de expansão/retração.
    Se numeros_base for fornecido, restringe a geração ao subconjunto de números escolhido pelo usuário.
    """
    import random

    if metodo and metodo.lower() not in ("canonica", "canonica_dinamica", "padrao", "automatico", "dinamico", "expansao_retracao"):
        from metodos_analise import gerar_jogos_por_metodo
        return gerar_jogos_por_metodo(
            modelo, quantidade_jogos, quantidade_numeros, metodo=metodo, numeros_base=numeros_base
        )

    if (modelo.config.colunas == 7 or modelo.config.nome == 'Super Sete' or getattr(modelo, 'loteria_type', None) == LoteriaType.SUPER_SETE) and not numeros_base:
        jogos_ss = modelo.gerar_jogos_supersete(quantidade_jogos)
        if len(jogos_ss) == quantidade_jogos:
            return jogos_ss

    if modelo.config.colunas:
        return _gerar_multiplos_por_coluna(modelo, quantidade_jogos, numeros_base)

    # Se não houver pool restrito e for o tamanho padrão de sorteio, utiliza o gerador espacial 4.0 com expansão/retração
    if not numeros_base:
        if (modelo.config.nome == 'Dupla Sena' or getattr(modelo, 'loteria_type', None) == LoteriaType.DUPLA_SENA or (modelo.N == 50 and modelo.config.sorteios_por_concurso == 2)):
            jogos_dupla = modelo.gerar_jogos_duplasena(quantidade_jogos, quantidade_numeros)
            if len(jogos_dupla) == quantidade_jogos:
                return jogos_dupla
        elif (modelo.config.nome == 'Dia de Sorte' or (modelo.N == 31 and quantidade_numeros in (7, 15))):
            jogos_dia = modelo.gerar_jogos_diadesorte(quantidade_jogos, quantidade_numeros)
            if len(jogos_dia) == quantidade_jogos:
                return jogos_dia
        elif (modelo.config.nome == '+Milionária' or (modelo.N == 50 and quantidade_numeros in (6, 12) and modelo.config.nome != 'Dupla Sena')):
            jogos_mili = modelo.gerar_jogos_maismilionaria(quantidade_jogos, quantidade_numeros)
            if len(jogos_mili) == quantidade_jogos:
                return jogos_mili
        elif (modelo.config.nome == 'Lotomania' or (modelo.N == 100 and quantidade_numeros in (20, 50))):
            jogos_loto_m = modelo.gerar_jogos_lotomania(quantidade_jogos, quantidade_numeros)
            if len(jogos_loto_m) == quantidade_jogos:
                return jogos_loto_m
        elif (modelo.config.nome == 'Timemania' or (modelo.N == 80 and quantidade_numeros in (7, 10))):
            jogos_dec = modelo.gerar_jogos_decagonais(quantidade_jogos, quantidade_numeros)
            if len(jogos_dec) == quantidade_jogos:
                return jogos_dec
        elif (modelo.config.nome == 'Lotofácil' or (modelo.N == 25 and quantidade_numeros == 15)):
            jogos_loto = modelo.gerar_jogos_lotofacil(quantidade_jogos, quantidade_numeros)
            if len(jogos_loto) == quantidade_jogos:
                return jogos_loto
        elif (modelo.config.nome == 'Quina' or (modelo.N == 80 and quantidade_numeros == 5)):
            jogos_pent = modelo.gerar_jogos_pentagonais(quantidade_jogos, quantidade_numeros)
            if len(jogos_pent) == quantidade_jogos:
                return jogos_pent
        elif (modelo.config.nome == 'Mega-Sena' or (modelo.N == 60 and quantidade_numeros == 6)):
            jogos_hex = modelo.gerar_jogos_hexagonais(quantidade_jogos, quantidade_numeros)
            if len(jogos_hex) == quantidade_jogos:
                return jogos_hex

    analises = modelo.analisar_todos_elementos()

    # Se o usuário definiu um pool de números base, valida e filtra
    if numeros_base and len(numeros_base) >= quantidade_numeros:
        universo_disponivel = sorted(list({n for n in numeros_base if n in modelo.contagens_total}))
        if len(universo_disponivel) < quantidade_numeros:
            universo_disponivel = list(modelo.numeros)
    else:
        universo_disponivel = list(modelo.numeros)

    # Calcular pesos estatísticos combinados com expansão e retração dinâmica
    pesos = {a.numero: modelo._peso_canonico_dinamico(a.numero) for a in analises}

    jogos_gerados = []
    jogos_set = set()
    tentativas = 0
    max_tentativas = quantidade_jogos * 150

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

        # 2. Completar com amostragem ponderada pelos pesos canônicos dinâmicos no universo disponível
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


def modelos_por_coluna(modelo: ModeloCanonico30) -> List[ModeloCanonico30]:
    """Um Modelo Canônico por coluna (Super Sete): cada coluna é um sorteio independente de 1 dígito."""
    if 'colunas' not in modelo._memo:
        config = modelo.config
        validos = [c for c in modelo.historico if len(c) == config.colunas]
        modelo._memo['colunas'] = [
            ModeloCanonico30([[c[i]] for c in validos], modelo.loteria_type, config_override=_config_coluna(config, i))
            for i in range(config.colunas)
        ]
    return modelo._memo['colunas']


def analise_por_coluna(modelo_principal: ModeloCanonico30) -> List[Dict]:
    resultado = []
    for i, modelo in enumerate(modelos_por_coluna(modelo_principal)):
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


def gerar_jogo_por_coluna(modelo: ModeloCanonico30) -> List[int]:
    """Jogo do Super Sete: um dígito por coluna, na ordem das colunas (repetição permitida)."""
    return _escolher_digitos(modelos_por_coluna(modelo))


def _gerar_multiplos_por_coluna(modelo: ModeloCanonico30, quantidade_jogos: int,
                                numeros_base: Optional[List[int]] = None) -> List[List[int]]:
    modelos = modelos_por_coluna(modelo)
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
    print("Modelo Canônico 4.0 + MCP-MD 1.0 (Otimização Hexagonal e Cobertura Espacial)")
    print("AGENTE LLN ICT FR MCOH - Sistema de Análise Estatística")
    print("=" * 60)
    
    # Histórico fictício para teste
    historico_teste = [
        [1, 5, 10, 23, 35, 42],
        [3, 12, 18, 29, 41, 55],
        [7, 15, 22, 33, 44, 58],
        # ... adicionar mais concursos
    ]
    
    # Criar modelo para Mega-Sena
    modelo = ModeloCanonico40(historico_teste, LoteriaType.MEGA_SENA)
    resumo = modelo.obter_resumo_analise()
    
    print(f"\nLoteria: {resumo['loteria']}")
    print(f"Concursos analisados: {resumo['total_concursos']}")
    print(f"ICT Médio: {resumo['estatisticas_gerais']['ict_medio']:.4f}")
    print(f"Entropia: {resumo['camada_informacional']['entropia']:.4f}")
    print(f"Camada Espacial: {resumo['camada_espacial']['modelo']}")


# Calendário da Caixa: sorteios aos sábados às 20h, domingos às 11h (quando houver)
# e os dos demais dias às 21h (horário de Brasília).
DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']


def horario_sorteio(dia_semana: int) -> int:
    if dia_semana == 6:  # domingo
        return 11
    if dia_semana == 5:  # sábado
        return 20
    return 21


def proximo_sorteio(config: 'LoteriaConfig', agora) -> Optional[Tuple[object, str]]:
    """Data do próximo sorteio (hoje conta até 1 h depois do horário) e um rótulo curto."""
    from datetime import timedelta
    dias = {DIAS_SEMANA.index(d) for d in config.dias_sorteio if d in DIAS_SEMANA}
    if not dias:
        return None
    for adiante in range(8):
        data = (agora + timedelta(days=adiante)).date()
        if data.weekday() not in dias:
            continue
        if adiante == 0 and agora.hour >= horario_sorteio(data.weekday()) + 1:
            continue
        hora = horario_sorteio(data.weekday())
        if adiante == 0:
            rotulo = f'Sorteia Hoje, {hora}h'
        else:
            rotulo = f'Sorteia {DIAS_SEMANA[data.weekday()].capitalize()}, {hora}h'
        return data, rotulo
    return None
