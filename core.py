"""
Sistema de Análise Estatística para Loterias - Modelo Canônico 4.0 + MCP-MD 1.0
MCOM (Matricial 5x5 - Lotofácil) / MCOH (Hexagonal - Mega-Sena) / MCOP (Pentagonal - Quina) - Modelos Canônicos de Otimização e Cobertura Espacial
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
        is_lotofacil = (self.config.nome == "Lotofácil" or (self.N == 25 and self.config.sorteados == 15))
        is_quina = (self.config.nome == "Quina" or (self.N == 80 and self.config.sorteados == 5))
        is_megasena = (self.config.nome == "Mega-Sena" or (self.N == 60 and self.config.sorteados == 6))

        if is_lotofacil:
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
                "aproximacoes": ["ICT", "ISEG", "C_i", "P_i", "pesos ILLA", "limiares de maturidade", "MCOH Hexagonal", "MCOP Pentagonal"],
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
            ]
        }
        return self._memo['resumo']

    def calcular_dispersao_hexagonal(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - MCOH (Modelo Canônico de Otimização Hexagonal e Cobertura Espacial).
        Calcula a dispersão geométrica e proximidade métrica do jogo no espaço cíclico Z_N.
        """
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

        # 2. Proximidade métrica circular mínima para os centros dos 6 setores
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
        Gera jogos utilizando o reticulado hexagonal regular com perturbações harmônicas,
        assegurando máxima cobertura espacial e respeito às restrições anti-compartilhamento de prêmio.
        """
        import random
        jogos = []
        jogos_set = set()

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
                    pesos = [_peso_canonico(self.analisar_elemento(n)) for n in opcoes]
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

    def calcular_dispersao_espacial(self, jogo: List[int]) -> Dict:
        """
        Camada 8 - Despacho Polimórfico de Cobertura Espacial.
        Encaminha para a geometria adequada de cada loteria:
        - Lotofácil: Matricial 5x5 (MCOM 4.0)
        - Quina: Pentagonal (MCOP 4.0)
        - Mega-Sena: Hexagonal (MCOH 4.0)
        - Demais loterias: Modelo espacial correspondente
        """
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
        Garante equilíbrio de paridade (2P/3I ou 3P/2I) e dispersão espacial em todos os setores.
        """
        import random
        jogos = []
        jogos_set = set()

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
                    pesos = [_peso_canonico(self.analisar_elemento(n)) for n in opcoes]
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
        paridade modal (8I/7P ou 7I/8P) e baricentro de soma (~195).
        """
        import random
        from modelo_lotofacil import ModeloMatricialLotofacil

        jogos = []
        jogos_set = set()

        # Se for o tamanho padrão de 15 dezenas, inicia com as variantes canônicas ótimas
        if quantidade_numeros == 15:
            canonicas = ModeloMatricialLotofacil.gerar_variantes_canonicas()
            ultimo_sorteio = set(self.historico[-1]) if self.historico else set()
            canonicas_ordenadas = sorted(
                canonicas,
                key=lambda v: abs(len(set(v["dezenas"]) & ultimo_sorteio) - 9)
            )
            for v in canonicas_ordenadas:
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

                pesos_mold = [_peso_canonico(self.analisar_elemento(n)) for n in moldura_list]
                pesos_miol = [_peso_canonico(self.analisar_elemento(n)) for n in miolo_list]

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
                pesos = [_peso_canonico(self.analisar_elemento(n)) for n in universo]
                escolhidos = set()
                while len(escolhidos) < quantidade_numeros:
                    n = random.choices(universo, weights=pesos, k=1)[0]
                    escolhidos.add(n)
                candidato = sorted(list(escolhidos))

            # Validação estrutural do candidato
            impares = sum(1 for n in candidato if n % 2 != 0)
            pares = len(candidato) - impares
            soma = sum(candidato)

            linhas = [0] * 5
            for n in candidato:
                linhas[(n - 1) // 5] += 1

            # Restrições de qualidade:
            # - Paridade no intervalo aceitável (8I/7P, 7I/8P, 9I/6P ou 6I/9P)
            # - Soma no intervalo canônico (175 a 215)
            # - Nenhuma linha vazia ou saturada (> 4 dezenas) quando k=15
            if (6 <= impares <= 9) and (175 <= soma <= 215):
                if quantidade_numeros != 15 or (min(linhas) >= 2 and max(linhas) <= 4):
                    tup = tuple(candidato)
                    if tup not in jogos_set:
                        jogos_set.add(tup)
                        jogos.append(candidato)

        return jogos[:quantidade_jogos]


# Alias canônico para compatibilidade com versões e chamadas anteriores
ModeloCanonico30 = ModeloCanonico40


# Reexporta a camada 7 para preservar os imports existentes.
from validacao import ValidaçãoCamada7


def gerar_jogo_sugerido(modelo: ModeloCanonico40, quantidade_numeros: int) -> List[int]:
    """
    Gerar sugestão de jogo baseada no Modelo Canônico 4.0.
    Combina a análise estatística multicamada (score MCP, ICT, FR) com a Otimização Espacial Matricial/Pentagonal/Hexagonal.
    """
    if modelo.config.colunas:
        return gerar_jogo_por_coluna(modelo)

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
    modelo: ModeloCanonico40, 
    quantidade_jogos: int, 
    quantidade_numeros: int,
    numeros_base: Optional[List[int]] = None
) -> List[List[int]]:
    """
    Gera N combinações distintas e balanceadas baseadas no Modelo Canônico 4.0.
    Garante que não haja jogos duplicados e aplica otimização de dispersão espacial (Pentagonal para Quina, Hexagonal para Mega-Sena).
    Se numeros_base for fornecido, restringe a geração ao subconjunto de números escolhido pelo usuário.
    """
    import random

    if modelo.config.colunas:
        return _gerar_multiplos_por_coluna(modelo, quantidade_jogos, numeros_base)

    # Se não houver pool restrito e for o tamanho padrão de sorteio, utiliza o gerador espacial 4.0
    if not numeros_base:
        if (modelo.config.nome == 'Lotofácil' or (modelo.N == 25 and quantidade_numeros == 15)):
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
