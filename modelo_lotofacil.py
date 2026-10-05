"""
Modelo de Dispersão e Proximidade Matricial 5x5 e Quintetos (MCOM 4.0) - Lotofácil
==================================================================================
Desenvolvido para otimização métrica de cobertura espacial (K-Medians) na Lotofácil (N=25, k=15).
Minimiza a distância média e máxima entre as dezenas apostadas e qualquer sorteio futuro
no reticulado bidimensional 5x5 e anel modular Z_25, otimizando o equilíbrio entre:
1. Moldura (16 dezenas periféricas) e Miolo (9 dezenas centrais);
2. Distribuição uniforme nos 5 quintetos/linhas (3-3-3-3-3) e colunas;
3. Paridade modal estocástica (8I/7P ou 7I/8P);
4. Baricentro de soma das dezenas no ponto ótimo (~195).
"""

from typing import List, Dict, Tuple, Any
import math


class ModeloMatricialLotofacil:
    TOTAL_DEZENAS = 25
    TOTAL_SORTEADOS = 15
    LINHAS = 5
    COLUNAS = 5
    CENTROS_QUINTETOS = [3, 8, 13, 18, 23]
    
    MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
    MIOLO = {7, 8, 9, 12, 13, 14, 17, 18, 19}
    
    IMPARES = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25}
    PARES = {2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24}

    @staticmethod
    def coordenadas(n: int) -> Tuple[int, int]:
        """Retorna as coordenadas (linha, coluna) de 0 a 4 na matriz 5x5."""
        return (n - 1) // 5, (n - 1) % 5

    @classmethod
    def distancia_manhattan(cls, a: int, b: int) -> int:
        """Calcula a distância reticulada de Manhattan no grid 5x5."""
        r1, c1 = cls.coordenadas(a)
        r2, c2 = cls.coordenadas(b)
        return abs(r1 - r2) + abs(c1 - c2)

    @classmethod
    def distancia_circular(cls, a: int, b: int) -> int:
        """Calcula a menor distância cíclica/circular no anel Z_25 de 25 números."""
        diff = abs(a - b)
        return min(diff, 25 - diff)

    @classmethod
    def analisar_composicao(cls, jogo: List[int]) -> Dict[str, Any]:
        """Analisa a composição estrutural de uma aposta da Lotofácil."""
        jogo_set = set(jogo)
        moldura_count = len(jogo_set & cls.MOLDURA)
        miolo_count = len(jogo_set & cls.MIOLO)
        impares_count = len(jogo_set & cls.IMPARES)
        pares_count = len(jogo_set & cls.PARES)
        
        linhas = [0] * 5
        colunas = [0] * 5
        for n in jogo:
            r, c = cls.coordenadas(n)
            linhas[r] += 1
            colunas[c] += 1
            
        soma = sum(jogo)
        
        return {
            "moldura": moldura_count,
            "miolo": miolo_count,
            "impares": impares_count,
            "pares": pares_count,
            "linhas": linhas,
            "colunas": colunas,
            "soma": soma,
            "desvio_linhas": sum(abs(r - 3) for r in linhas),
            "desvio_colunas": sum(abs(c - 3) for c in colunas),
        }

    @classmethod
    def gerar_base_pura(cls) -> List[int]:
        """
        Retorna a aposta base canônica pura do Modelo Matricial 5x5.
        Possui exatamente 3 dezenas por linha e 3 por coluna, 10 dezenas na Moldura,
        5 no Miolo, paridade 7I/8P e baricentro exato de soma 195.
        """
        return [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 22, 24, 25]

    @classmethod
    def gerar_variantes_canonicas(cls) -> List[Dict[str, Any]]:
        """
        Gera combinações do Modelo Canônico 4.0 Matricial e Quintetos (MCOM 4.0)
        que preservam a máxima proximidade espacial (distância de Manhattan no grid <= 1)
        e respeitam as proporções modais estocásticas da Lotofácil (10M/5M ou 9M/6M, 8I/7P ou 7I/8P, soma ~195).
        """
        variantes = [
            {
                "nome": "Matricial Regular Puro (Base Canônica 5x5)",
                "dezenas": [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 22, 24, 25],
                "dist_max_grid": 1,
                "moldura": 10,
                "miolo": 5,
                "impares": 7,
                "pares": 8,
                "soma": 195,
                "descricao": "Reticulado estritamente simétrico com 3 dezenas por linha e por coluna, proporção modal perfeita 10 Moldura / 5 Miolo e baricentro exato em 195."
            },
            {
                "nome": "Matricial Equilibrado 8I/7P (Variante Alpha)",
                "dezenas": [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 21, 24, 25],
                "dist_max_grid": 1,
                "moldura": 10,
                "miolo": 5,
                "impares": 8,
                "pares": 7,
                "soma": 194,
                "descricao": "Configuração canônica no pico modal da paridade 8I/7P, com 10 dezenas na Moldura e 5 no Miolo, mantendo cobertura homogênea dos 5 quintetos."
            },
            {
                "nome": "Matricial Equilibrado 7I/8P (Variante Beta)",
                "dezenas": [1, 2, 3, 6, 9, 10, 11, 12, 14, 18, 19, 20, 22, 23, 25],
                "dist_max_grid": 1,
                "moldura": 10,
                "miolo": 5,
                "impares": 7,
                "pares": 8,
                "soma": 195,
                "descricao": "Distribuição ortogonal 3x3 em linhas e colunas, baricentro de soma 195 e alternância harmônica no miolo central."
            },
            {
                "nome": "Matricial Harmônico 8I/7P (Variante Gamma)",
                "dezenas": [1, 2, 3, 6, 8, 10, 13, 14, 15, 17, 18, 19, 21, 22, 25],
                "dist_max_grid": 1,
                "moldura": 9,
                "miolo": 6,
                "impares": 8,
                "pares": 7,
                "soma": 194,
                "descricao": "Expansão harmônica no miolo central (9M/6M) capturando transições internas e paridade modal 8I/7P."
            },
            {
                "nome": "Matricial Harmônico 7I/8P (Variante Delta)",
                "dezenas": [1, 2, 3, 6, 8, 10, 12, 14, 15, 17, 18, 19, 21, 24, 25],
                "dist_max_grid": 1,
                "moldura": 9,
                "miolo": 6,
                "impares": 7,
                "pares": 8,
                "soma": 195,
                "descricao": "Perfeita simetria bidimensional com 3 por linha e 3 por coluna, soma 195, integrando miolo estendido (9M/6M) com baixa popularidade."
            }
        ]
        return variantes

    @classmethod
    def avaliar_proximidade(cls, jogo: List[int], sorteios: List[List[int]]) -> Dict[str, Any]:
        """
        Avalia as métricas espaciais e matriciais do jogo frente a um histórico de sorteios da Lotofácil.
        """
        if not sorteios:
            return {
                "distancia_grid_media": 0.0,
                "distancia_maxima_grid": 0,
                "pct_dezenas_dist_le_1": 0.0,
                "pct_concursos_com_vizinho": 0.0,
                "media_acertos_exatos_por_concurso": 0.0,
                "pct_concursos_premiados": 0.0,
                "distribuicao_acertos": {}
            }

        distancias_grid = []
        acertos_exatos = 0
        acertos_dist_1 = 0
        concursos_com_vizinho = 0
        acertos_dist = {i: 0 for i in range(16)}
        total_dezenas = len(sorteios) * 15

        jogo_set = set(jogo)
        jogo_coords = [cls.coordenadas(p) for p in jogo]

        for d in sorteios:
            exatos = len(jogo_set & set(d))
            acertos_exatos += exatos
            acertos_dist[exatos] += 1
            todos_vizinhos = True

            for bola in d:
                br, bc = cls.coordenadas(bola)
                min_d = min(abs(br - jr) + abs(bc - jc) for jr, jc in jogo_coords)
                distancias_grid.append(min_d)
                if min_d <= 1:
                    acertos_dist_1 += 1
                else:
                    todos_vizinhos = False

            if todos_vizinhos:
                concursos_com_vizinho += 1

        concursos_premiados = sum(acertos_dist[k] for k in range(11, 16))

        return {
            "distancia_grid_media": round(sum(distancias_grid) / len(distancias_grid), 4),
            "distancia_maxima_grid": max(distancias_grid) if distancias_grid else 0,
            "pct_dezenas_dist_le_1": round((acertos_dist_1 / total_dezenas) * 100, 2),
            "pct_concursos_com_vizinho": round((concursos_com_vizinho / len(sorteios)) * 100, 2),
            "media_acertos_exatos_por_concurso": round(acertos_exatos / len(sorteios), 4),
            "pct_concursos_premiados": round((concursos_premiados / len(sorteios)) * 100, 2),
            "distribuicao_acertos": {k: v for k, v in acertos_dist.items() if v > 0}
        }


# Alias universal
ModeloMatricial = ModeloMatricialLotofacil


if __name__ == "__main__":
    modelo = ModeloMatricialLotofacil()
    print("=== MODELO MATRICIAL 5x5 E QUINTETOS (LOTOFÁCIL N=25) ===")
    for v in modelo.gerar_variantes_canonicas():
        print(f"\n[{v['nome']}]")
        print(f"  Dezenas: {v['dezenas']}")
        print(f"  Moldura/Miolo: {v['moldura']}M / {v['miolo']}M")
        print(f"  Paridade: {v['impares']}I / {v['pares']}P | Soma: {v['soma']}")
        print(f"  Distância máxima no grid: <= {v['dist_max_grid']}")
        print(f"  Descrição: {v['descricao']}")
