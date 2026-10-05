"""
Modelo de Dispersão e Proximidade Pentagonal (P-Model) - Quina
==============================================================
Desenvolvido para otimização métrica de cobertura espacial (K-Medians) na Quina (N=80, k=5).
Minimiza a distância média e máxima entre as dezenas apostadas e qualquer sorteio futuro
no anel cíclico modular Z_80, dividindo o volante em 5 setores de 16 dezenas cada.
"""

from typing import List, Dict, Tuple, Any
import math


class ModeloPentagonalQuina:
    TOTAL_DEZENAS = 80
    SETORES = 5
    LARGURA_SETOR = 16
    CENTROS_NATURAIS = [8, 24, 40, 56, 72]

    @staticmethod
    def distancia_circular(a: int, b: int) -> int:
        """Calcula a menor distância cíclica/circular no anel Z_80 de 80 números."""
        diff = abs(a - b)
        return min(diff, 80 - diff)

    @classmethod
    def gerar_base_pura(cls, delta: int = 8) -> List[int]:
        """
        Gera o reticulado pentagonal regular puro para um dado deslocamento delta (1 a 16).
        Para delta=8, produz [08, 24, 40, 56, 72].
        Garante distância máxima <= 8 unidades para qualquer número de 1 a 80.
        """
        assert 1 <= delta <= 16, "Delta deve estar entre 1 e 16."
        jogo = [((cls.LARGURA_SETOR * i + delta - 1) % cls.TOTAL_DEZENAS) + 1 for i in range(cls.SETORES)]
        return sorted(jogo)

    @classmethod
    def gerar_variantes_canonicas(cls) -> List[Dict[str, Any]]:
        """
        Gera jogos baseados no reticulado pentagonal que preservam a máxima proximidade espacial
        (distância máxima <= 8 ou 9 unidades) e respeitam as restrições anti-compartilhamento
        do Modelo Canônico da Quina (equilíbrio de pares/ímpares 3P/2I ou 2P/3I, dispersão nos 5 setores).
        """
        variantes = [
            {
                "nome": "Pentagonal Regular Puro (Delta=8)",
                "dezenas": [8, 24, 40, 56, 72],
                "dist_max": 8,
                "pares": 5,
                "impares": 0,
                "soma": 200,
                "descricao": "Reticulado estritamente simétrico no centro de cada lado do pentágono."
            },
            {
                "nome": "Pentagonal Equilibrado 3P/2I (Variante Alpha)",
                "dezenas": [7, 24, 39, 56, 72],
                "dist_max": 8,
                "pares": 3,
                "impares": 2,
                "soma": 198,
                "descricao": "Perturbação harmônica mínima mantendo distância máxima de 8 e equilíbrio 3P/2I."
            },
            {
                "nome": "Pentagonal Equilibrado 2P/3I (Variante Beta)",
                "dezenas": [8, 23, 40, 55, 71],
                "dist_max": 8,
                "pares": 2,
                "impares": 3,
                "soma": 197,
                "descricao": "Alternância simétrica de vértices ímpares mantendo dispersão setorial e baixa popularidade."
            },
            {
                "nome": "Pentagonal Equilibrado 3P/2I (Variante Gamma)",
                "dezenas": [9, 24, 41, 56, 70],
                "dist_max": 9,
                "pares": 3,
                "impares": 2,
                "soma": 200,
                "descricao": "Expansão angular oposta preservando a soma no baricentro estatístico (200)."
            },
            {
                "nome": "Pentagonal Equilibrado 2P/3I (Variante Delta)",
                "dezenas": [7, 25, 39, 56, 72],
                "dist_max": 9,
                "pares": 2,
                "impares": 3,
                "soma": 199,
                "descricao": "Micro-deslocamento nos setores 1, 2 e 3 para máxima descorrelação com jogos populares."
            }
        ]
        return variantes

    @classmethod
    def avaliar_proximidade(cls, jogo: List[int], sorteios: List[List[int]]) -> Dict[str, float]:
        """
        Avalia as métricas espaciais do jogo pentagonal frente a um histórico de sorteios da Quina.
        """
        if not sorteios:
            return {
                "distancia_media": 0.0,
                "distancia_maxima": 0,
                "pct_dezenas_dist_le_1": 0.0,
                "pct_concursos_com_vizinho": 0.0,
                "media_acertos_exatos_por_concurso": 0.0
            }

        distancias = []
        acertos_exatos = 0
        acertos_dist_1 = 0
        concursos_com_vizinho = 0
        total_dezenas = len(sorteios) * 5

        for d in sorteios:
            exatos = len(set(jogo) & set(d))
            acertos_exatos += exatos
            teve_vizinho = False

            for bola in d:
                min_d = min(cls.distancia_circular(bola, p) for p in jogo)
                distancias.append(min_d)
                if min_d <= 1:
                    acertos_dist_1 += 1
                    teve_vizinho = True

            if teve_vizinho:
                concursos_com_vizinho += 1

        return {
            "distancia_media": round(sum(distancias) / len(distancias), 4),
            "distancia_maxima": max(distancias) if distancias else 0,
            "pct_dezenas_dist_le_1": round((acertos_dist_1 / total_dezenas) * 100, 2),
            "pct_concursos_com_vizinho": round((concursos_com_vizinho / len(sorteios)) * 100, 2),
            "media_acertos_exatos_por_concurso": round(acertos_exatos / len(sorteios), 4)
        }


# Alias universal
ModeloPentagonal = ModeloPentagonalQuina


if __name__ == "__main__":
    modelo = ModeloPentagonalQuina()
    print("=== MODELO PENTAGONAL DE DISPERSÃO E PROXIMIDADE (QUINA N=80) ===")
    for v in modelo.gerar_variantes_canonicas():
        print(f"\n[{v['nome']}]")
        print(f"  Dezenas: {v['dezenas']}")
        print(f"  Distância máxima garantida: <= {v['dist_max']} unidades")
        print(f"  Equilíbrio: {v['pares']}P / {v['impares']}I | Soma: {v['soma']}")
        print(f"  Descrição: {v['descricao']}")
