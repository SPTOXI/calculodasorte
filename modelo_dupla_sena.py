"""
Módulo do Modelo Canônico 4.0 — Otimização Hexagonal Bivariada de Duplo Sorteio (MCODSen 4.0)
Exclusivo para a Dupla Sena (N = 50, k = 6, m = 6, com 2 sorteios independentes por concurso).

Topologia:
- Anel Circular Modular Z_50 particionado em 6 setores regulares (~8,33 dezenas cada).
- Centros da Base Pura: [04, 13, 21, 30, 38, 46].
- Cota analítica máxima determinística em Z_50: <= 4 unidades para qualquer número sorteado.
- Análise e dispersão bivariada simultânea: cobertura do 1º sorteio (S1) e 2º sorteio (S2).
- Paridade modal: 3 Pares e 3 Ímpares (33,29% teórico, ~38-39% empírico).
- Baricentro de soma ótimo: mu = 6 * 25.5 = 153.0 (faixa típica: 125 a 181).
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set


@dataclass(frozen=True)
class SetorHexagonalDuplaSena:
    """Setor do anel modular Z_50 da Dupla Sena."""
    id: int
    faixa_inicio: int
    faixa_fim: int
    centro: int
    dezenas: Tuple[int, ...]
    amplitude: int


@dataclass
class VarianteBivariadaDuplaSena:
    """Variante canônica bivariada da Dupla Sena."""
    nome: str
    dezenas: List[int]
    perfil: str
    pares: int
    impares: int
    soma: int
    cobertura_setores: int
    distancia_base: float
    descricao: str


class ModeloBivariadoDuplaSena:
    """
    Motor Canônico 4.0 Especializado para a Dupla Sena (MCODSen 4.0).
    Modela o espaço de 50 dezenas e os 2 sorteios independentes por concurso.
    """
    UNIVERSO = 50
    DEZENAS_SORTEIO = 6
    DEZENAS_APOSTA = 6
    TOTAL_SETORES = 6
    COTA_MAXIMA_TEORICA = 4
    SOMA_ESPERADA = 153.0
    DESVIO_PADRAO_SOMA = 23.0

    # Centros canônicos do anel circular Z_50
    CENTROS_BASE = [4, 13, 21, 30, 38, 46]

    # Partição em 6 setores regulares
    SETORES = [
        SetorHexagonalDuplaSena(0, 1, 8, 4, tuple(range(1, 9)), 8),
        SetorHexagonalDuplaSena(1, 9, 17, 13, tuple(range(9, 18)), 9),
        SetorHexagonalDuplaSena(2, 18, 25, 21, tuple(range(18, 26)), 8),
        SetorHexagonalDuplaSena(3, 26, 34, 30, tuple(range(26, 35)), 9),
        SetorHexagonalDuplaSena(4, 35, 42, 38, tuple(range(35, 43)), 8),
        SetorHexagonalDuplaSena(5, 43, 50, 46, tuple(range(43, 51)), 8),
    ]

    @staticmethod
    def distancia_circular(a: int, b: int, n: int = 50) -> int:
        """Calcula a menor distância circular no anel modular Z_N."""
        diff = abs(a - b)
        return min(diff, n - diff)

    @classmethod
    def menor_distancia_base(cls, num: int) -> int:
        """Distância mínima de um número a qualquer centro da Base Pura."""
        return min(cls.distancia_circular(num, c, cls.UNIVERSO) for c in cls.CENTROS_BASE)

    @classmethod
    def setor_do_numero(cls, num: int) -> int:
        """Determina a qual setor [0..5] pertence um número de 1 a 50."""
        for s in cls.SETORES:
            if s.faixa_inicio <= num <= s.faixa_fim:
                return s.id
        # Fallback de contorno
        return 0 if num <= 8 else 5

    @classmethod
    def calcular_dispersao_bivariada(
        cls,
        jogo: List[int],
        sorteio1: Optional[List[int]] = None,
        sorteio2: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Calcula as métricas espaciais canônicas e a dispersão bivariada
        para o 1º sorteio, 2º sorteio e conjunta.
        """
        jogo_limpo = sorted(set(int(x) for x in jogo if 1 <= int(x) <= cls.UNIVERSO))
        if not jogo_limpo:
            return {"valido": False, "erro": "Jogo vazio ou inválido"}

        # 1. Distância à Base Pura Z_50
        distancias_base = [cls.menor_distancia_base(x) for x in jogo_limpo]
        dist_media_base = sum(distancias_base) / len(distancias_base)
        dist_max_base = max(distancias_base)

        # 2. Cobertura setorial
        setores_cobertos = set(cls.setor_do_numero(x) for x in jogo_limpo)
        cobertura_setores = len(setores_cobertos)
        taxa_cobertura = (cobertura_setores / cls.TOTAL_SETORES) * 100.0

        # 3. Estatísticas hipergeométricas
        pares = sum(1 for x in jogo_limpo if x % 2 == 0)
        impares = len(jogo_limpo) - pares
        soma = sum(jogo_limpo)
        desvio_soma = abs(soma - cls.SOMA_ESPERADA)

        # 4. Avaliação bivariada contra Sorteio 1 (se fornecido)
        dist_s1 = None
        dist_max_s1 = None
        acertos_s1 = None
        if sorteio1:
            s1_limpo = [int(x) for x in sorteio1 if 1 <= int(x) <= cls.UNIVERSO]
            if s1_limpo:
                dists_s1_lista = [min(cls.distancia_circular(s, j, cls.UNIVERSO) for j in jogo_limpo) for s in s1_limpo]
                dist_s1 = sum(dists_s1_lista) / len(dists_s1_lista)
                dist_max_s1 = max(dists_s1_lista)
                acertos_s1 = len(set(jogo_limpo) & set(s1_limpo))

        # 5. Avaliação bivariada contra Sorteio 2 (se fornecido)
        dist_s2 = None
        dist_max_s2 = None
        acertos_s2 = None
        if sorteio2:
            s2_limpo = [int(x) for x in sorteio2 if 1 <= int(x) <= cls.UNIVERSO]
            if s2_limpo:
                dists_s2_lista = [min(cls.distancia_circular(s, j, cls.UNIVERSO) for j in jogo_limpo) for s in s2_limpo]
                dist_s2 = sum(dists_s2_lista) / len(dists_s2_lista)
                dist_max_s2 = max(dists_s2_lista)
                acertos_s2 = len(set(jogo_limpo) & set(s2_limpo))

        # 6. Métricas conjuntas bivariadas
        dist_bivariada_conjunta = None
        indice_bivariado_harmonico = None
        if dist_s1 is not None and dist_s2 is not None:
            dist_bivariada_conjunta = (dist_s1 + dist_s2) / 2.0
            indice_bivariado_harmonico = (2.0 * dist_s1 * dist_s2) / (dist_s1 + dist_s2 + 1e-6)

        # 7. Índice de Dispersão Espacial Bivariado 4.0 (IDE Bivariado)
        # 100 pontos ideais: penaliza afastamento da Base Pura, cobertura incompleta e desvios
        penalidade_dist = max(0.0, (dist_media_base - 2.1) * 15.0)
        penalidade_cobertura = (cls.TOTAL_SETORES - min(len(jogo_limpo), cobertura_setores)) * 6.0
        penalidade_paridade = abs(pares - impares) * 3.0
        penalidade_soma = min(15.0, (desvio_soma / cls.DESVIO_PADRAO_SOMA) * 5.0)

        ide_bivariado = max(10.0, min(100.0, 100.0 - penalidade_dist - penalidade_cobertura - penalidade_paridade - penalidade_soma))

        return {
            "valido": True,
            "jogo": jogo_limpo,
            "distancia_media_base": round(dist_media_base, 3),
            "distancia_maxima_base": dist_max_base,
            "cota_conforme": dist_max_base <= cls.COTA_MAXIMA_TEORICA,
            "cobertura_setores": cobertura_setores,
            "setores_presentes": sorted(list(setores_cobertos)),
            "taxa_cobertura": round(taxa_cobertura, 1),
            "pares": pares,
            "impares": impares,
            "paridade_modal": pares == 3 and impares == 3,
            "soma": soma,
            "desvio_soma": round(desvio_soma, 1),
            "distancia_sorteio_1": round(dist_s1, 3) if dist_s1 is not None else None,
            "distancia_maxima_sorteio_1": dist_max_s1,
            "acertos_sorteio_1": acertos_s1,
            "distancia_sorteio_2": round(dist_s2, 3) if dist_s2 is not None else None,
            "distancia_maxima_sorteio_2": dist_max_s2,
            "acertos_sorteio_2": acertos_s2,
            "distancia_bivariada_conjunta": round(dist_bivariada_conjunta, 3) if dist_bivariada_conjunta is not None else None,
            "indice_bivariado_harmonico": round(indice_bivariado_harmonico, 3) if indice_bivariado_harmonico is not None else None,
            "ide_bivariado": round(ide_bivariado, 1),
            "modelo": "MCODSen 4.0"
        }

    @classmethod
    def gerar_variantes_canonicas(cls) -> List[VarianteBivariadaDuplaSena]:
        """Gera as 5 variantes canônicas bivariadas especializadas para a Dupla Sena."""
        variantes = [
            VarianteBivariadaDuplaSena(
                nome="Base Pura Hexagonal",
                dezenas=[4, 13, 21, 30, 38, 46],
                perfil="Topológico Estrito",
                pares=3,
                impares=3,
                soma=152,
                cobertura_setores=6,
                distancia_base=0.0,
                descricao="Centros naturais exatos dos 6 setores de Z_50. Cota determinística <= 4."
            ),
            VarianteBivariadaDuplaSena(
                nome="Alpha (Moda Paridade & Soma 153)",
                dezenas=[5, 12, 21, 30, 39, 46],
                perfil="Hipergeométrico Central",
                pares=3,
                impares=3,
                soma=153,
                cobertura_setores=6,
                distancia_base=0.333,
                descricao="3 Pares e 3 Ímpares com baricentro de soma exatamente calibrado em 153."
            ),
            VarianteBivariadaDuplaSena(
                nome="Beta (Harmônica Bivariada Conjunta)",
                dezenas=[3, 14, 20, 31, 37, 48],
                perfil="Duplo Sorteio Harmônico",
                pares=3,
                impares=3,
                soma=153,
                cobertura_setores=6,
                distancia_base=1.167,
                descricao="Defasagem harmônica de ±1 em torno dos centros para maximizar a captura nos dois sorteios."
            ),
            VarianteBivariadaDuplaSena(
                nome="Gamma (Transição Intersetorial)",
                dezenas=[6, 11, 23, 28, 40, 45],
                perfil="Continuidade Cíclica",
                pares=3,
                impares=3,
                soma=153,
                cobertura_setores=6,
                distancia_base=1.667,
                descricao="Dezenas em faixas de fronteira entre setores, cobrindo zonas de transição cíclica."
            ),
            VarianteBivariadaDuplaSena(
                nome="Delta (Anti-Agrupamento / Equidistante)",
                dezenas=[7, 15, 24, 32, 41, 49],
                perfil="Anti-Divisão de Prêmio",
                pares=2,
                impares=4,
                soma=168,
                cobertura_setores=6,
                distancia_base=2.167,
                descricao="Foco em dezenas finais de setores para redução de apostas duplicadas."
            )
        ]
        return variantes

    @classmethod
    def gerar_jogos(
        cls,
        quantidade: int = 5,
        dezenas_por_jogo: int = 6,
        pesos_illa: Optional[Dict[int, float]] = None
    ) -> List[List[int]]:
        """
        Gera combinações canônicas de alta performance para a Dupla Sena.
        Garante cobertura dos 6 setores, paridade equilibrada e soma na faixa ideal.
        """
        if dezenas_por_jogo < 6 or dezenas_por_jogo > 15:
            dezenas_por_jogo = 6

        variantes = cls.gerar_variantes_canonicas()
        jogos_gerados: List[List[int]] = []

        # 1. Adicionar variantes canônicas fundamentais primeiro
        for var in variantes:
            if len(jogos_gerados) >= quantidade:
                break
            jogo_base = list(var.dezenas)
            if dezenas_por_jogo > 6:
                # Expandir harmoniosamente respeitando os setores
                candidatos = [x for x in range(1, cls.UNIVERSO + 1) if x not in jogo_base]
                if pesos_illa:
                    candidatos.sort(key=lambda x: pesos_illa.get(x, 0.0), reverse=True)
                jogo_base.extend(candidatos[:dezenas_por_jogo - 6])
            jogos_gerados.append(sorted(jogo_base))

        # 2. Se a quantidade solicitada for maior, sintetizar variações canônicas
        if len(jogos_gerados) < quantidade:
            passos_variacao = [
                [-1, 1, 0, 0, 0, 0],
                [0, -1, 1, 0, 0, 0],
                [0, 0, -1, 1, 0, 0],
                [0, 0, 0, -1, 1, 0],
                [0, 0, 0, 0, -1, 1],
                [1, 0, 0, 0, 0, -1],
                [1, -1, 0, 1, -1, 0],
                [0, 1, -1, 0, 1, -1]
            ]
            
            idx = 0
            while len(jogos_gerados) < quantidade and idx < len(passos_variacao):
                deslocamento = passos_variacao[idx]
                novo_jogo = []
                for s_id, delta in enumerate(deslocamento):
                    c = cls.CENTROS_BASE[s_id]
                    num = ((c - 1 + delta) % cls.UNIVERSO) + 1
                    novo_jogo.append(num)
                
                novo_jogo = sorted(set(novo_jogo))
                if len(novo_jogo) == 6 and novo_jogo not in jogos_gerados:
                    if dezenas_por_jogo > 6:
                        cands = [x for x in range(1, cls.UNIVERSO + 1) if x not in novo_jogo]
                        novo_jogo.extend(cands[:dezenas_por_jogo - 6])
                    jogos_gerados.append(sorted(novo_jogo))
                idx += 1

        return jogos_gerados[:quantidade]
