"""
Modelo de Dispersão e Proximidade Hexagonal (H-Model)
=====================================================
Desenvolvido para otimização métrica de cobertura espacial (K-Medians) na Mega-Sena.
Minimiza a distância média e máxima entre as dezenas apostadas e qualquer sorteio futuro.
"""

from typing import List, Dict, Tuple
import math

class ModeloHexagonal:
    TOTAL_DEZENAS = 60
    SETORES = 6
    LARGURA_SETOR = 10

    @staticmethod
    def distancia_circular(a: int, b: int) -> int:
        """Calcula a menor distância cíclica/circular no anel de 60 números."""
        diff = abs(a - b)
        return min(diff, 60 - diff)

    @classmethod
    def gerar_base_pura(cls, delta: int = 5) -> List[int]:
        """
        Gera o reticulado hexagonal regular puro para um dado deslocamento delta (1 a 10).
        Exemplo: delta=5 -> [05, 15, 25, 35, 45, 55]
        Garante distância máxima <= 5 unidades para qualquer número de 1 a 60.
        """
        assert 1 <= delta <= 10, "Delta deve estar entre 1 e 10."
        jogo = [((cls.LARGURA_SETOR * i + delta - 1) % cls.TOTAL_DEZENAS) + 1 for i in range(cls.SETORES)]
        return sorted(jogo)

    @classmethod
    def gerar_variantes_canonicas(cls) -> List[Dict[str, any]]:
        """
        Gera jogos baseados no reticulado hexagonal que preservam a máxima proximidade espacial
        (distância máxima <= 5 ou 6 unidades) e respeitam as restrições anti-compartilhamento
        do Modelo Canônico 4.0 (equilíbrio de pares/ímpares, sem PA óbvia, ocupando 6 setores).
        """
        variantes = [
            {
                "nome": "Hexagonal Regular Puro (Delta=5)",
                "dezenas": [5, 15, 25, 35, 45, 55],
                "dist_max": 5,
                "pares": 0,
                "descricao": "Reticulado estritamente simétrico no centro de cada lado do hexágono."
            },
            {
                "nome": "Hexagonal Equilibrado 3P/3I (Variante Alpha)",
                "dezenas": [4, 15, 26, 33, 44, 55],
                "dist_max": 5,
                "pares": 3,
                "descricao": "Perturbação harmônica mínima mantendo distância máxima de 5 e equilíbrio 3P/3I."
            },
            {
                "nome": "Hexagonal Equilibrado 3P/3I (Variante Beta)",
                "dezenas": [6, 15, 24, 35, 46, 53],
                "dist_max": 6,
                "pares": 3,
                "descricao": "Alternância simétrica de vértices mantendo dispersão setorial e baixa popularidade."
            },
            {
                "nome": "Hexagonal Equilibrado 3P/3I (Variante Gamma)",
                "dezenas": [5, 14, 27, 36, 43, 56],
                "dist_max": 6,
                "pares": 3,
                "descricao": "Expansão angular oposta, rompendo finais repetidos e preservando proximidade média."
            }
        ]
        return variantes

    @classmethod
    def avaliar_proximidade(cls, jogo: List[int], sorteios: List[List[int]]) -> Dict[str, float]:
        """
        Avalia as métricas espaciais do jogo frente a um histórico de sorteios.
        """
        distancias = []
        acertos_exatos = 0
        acertos_dist_1 = 0
        
        total_dezenas = len(sorteios) * 6
        for d in sorteios:
            exatos = len(set(jogo) & set(d))
            acertos_exatos += exatos
            
            for bola in d:
                min_d = min(cls.distancia_circular(bola, p) for p in jogo)
                distancias.append(min_d)
                if min_d <= 1:
                    acertos_dist_1 += 1
                    
        return {
            "distancia_media": sum(distancias) / len(distancias),
            "distancia_maxima": max(distancias),
            "pct_dezenas_dist_le_1": (acertos_dist_1 / total_dezenas) * 100,
            "media_acertos_exatos_por_concurso": acertos_exatos / len(sorteios)
        }

if __name__ == "__main__":
    modelo = ModeloHexagonal()
    print("=== MODELO HEXAGONAL DE DISPERSÃO E PROXIMIDADE ===")
    for v in modelo.gerar_variantes_canonicas():
        print(f"\n[{v['nome']}]")
        print(f"  Dezenas: {v['dezenas']}")
        print(f"  Distância máxima garantida: <= {v['dist_max']} unidades")
        print(f"  Equilíbrio Pares: {v['pares']}P / {6 - v['pares']}I")
        print(f"  Descrição: {v['descricao']}")
