"""
Modelo de Dispersão e Proximidade Decagonal (D-Model) e Time do Coração - Timemania
==================================================================================
Desenvolvido para otimização métrica de cobertura espacial (K-Medians) na Timemania (N=80, k=7, aposta=10).
Minimiza a distância média e máxima entre as 10 dezenas apostadas e qualquer sorteio futuro
no anel cíclico modular Z_80, dividindo o volante em 10 setores de 8 dezenas cada, e integrando
a seleção harmônica do Time do Coração dentre os 80/82 clubes oficiais.
"""

from typing import List, Dict, Tuple, Any, Optional
import math
from collections import Counter


class ModeloDecagonalTimemania:
    TOTAL_DEZENAS = 80
    DEZENAS_SORTEIO = 7
    DEZENAS_APOSTA = 10
    SETORES = 10
    LARGURA_SETOR = 8
    CENTROS_NATURAIS = [4, 12, 20, 28, 36, 44, 52, 60, 68, 76]

    @staticmethod
    def distancia_circular(a: int, b: int) -> int:
        """Calcula a menor distância cíclica/circular no anel Z_80 de 80 números."""
        diff = abs(a - b)
        return min(diff, 80 - diff)

    @classmethod
    def gerar_base_pura(cls, delta: int = 4) -> List[int]:
        """
        Gera o reticulado decagonal regular puro para um dado deslocamento delta (1 a 8).
        Para delta=4, produz [04, 12, 20, 28, 36, 44, 52, 60, 68, 76].
        Garante distância máxima <= 4 unidades para qualquer número de 1 a 80.
        """
        assert 1 <= delta <= 8, "Delta deve estar entre 1 e 8."
        jogo = [((cls.LARGURA_SETOR * i + delta - 1) % cls.TOTAL_DEZENAS) + 1 for i in range(cls.SETORES)]
        return sorted(jogo)

    @classmethod
    def gerar_variantes_canonicas(cls) -> List[Dict[str, Any]]:
        """
        Gera jogos baseados no reticulado decagonal que preservam a máxima proximidade espacial
        (distância máxima <= 4 ou 5 unidades) e respeitam as restrições do Modelo Canônico 4.0:
        equilíbrio de paridade 5P/5I, 10 setores cobertos, baricentro de soma ~405 e Time do Coração sugerido.
        """
        variantes = [
            {
                "nome": "Decagonal Regular Puro (Delta=4)",
                "dezenas": [4, 12, 20, 28, 36, 44, 52, 60, 68, 76],
                "dist_max": 4,
                "pares": 10,
                "impares": 0,
                "soma": 400,
                "time_sugerido": "CORITIBA /PR",
                "descricao": "Reticulado estritamente simétrico no centro exato de cada um dos 10 setores de 8 dezenas."
            },
            {
                "nome": "Decagonal Equilibrado 5P/5I (Variante Alpha)",
                "dezenas": [4, 11, 20, 27, 36, 43, 52, 59, 68, 75],
                "dist_max": 4,
                "pares": 5,
                "impares": 5,
                "soma": 395,
                "time_sugerido": "ATLETICO /MG",
                "descricao": "Perturbação harmônica mínima alternada (-1) nos setores pares mantendo cota de 4 e equilíbrio 5P/5I."
            },
            {
                "nome": "Decagonal Equilibrado 5P/5I (Variante Beta)",
                "dezenas": [5, 12, 21, 28, 37, 44, 53, 60, 69, 76],
                "dist_max": 4,
                "pares": 5,
                "impares": 5,
                "soma": 405,
                "time_sugerido": "BAHIA /BA",
                "descricao": "Deslocamento angular simétrico atingindo o baricentro ótimo exato de soma 405 e paridade 5P/5I."
            },
            {
                "nome": "Decagonal Harmônico 5P/5I (Variante Gamma)",
                "dezenas": [3, 12, 19, 28, 35, 44, 51, 60, 67, 76],
                "dist_max": 5,
                "pares": 5,
                "impares": 5,
                "soma": 395,
                "time_sugerido": "GOIAS /GO",
                "descricao": "Expansão de amplitude harmônica cobrindo os 10 setores decagonais com dispersão ampla."
            },
            {
                "nome": "Decagonal Descorrelacionado 5P/5I (Variante Delta)",
                "dezenas": [5, 12, 20, 27, 37, 44, 52, 59, 69, 76],
                "dist_max": 5,
                "pares": 5,
                "impares": 5,
                "soma": 401,
                "time_sugerido": "FORTALEZA /CE",
                "descricao": "Perturbação setorial cruzada para máxima descorrelação com jogos populares de massa."
            }
        ]
        return variantes

    @classmethod
    def analisar_times_historico(cls, historico_times: List[str]) -> List[Dict[str, Any]]:
        """
        Analisa o histórico de Times do Coração sorteados na Timemania:
        calcula frequência absoluta, fator de recorrência (FR) e atraso de cada clube.
        """
        if not historico_times:
            return []

        total = len(historico_times)
        media_esperada = total / 80.0
        contagens = Counter(historico_times)

        # Cálculo de atrasos (concursos desde o último sorteio)
        atrasos = {}
        for dist, t in enumerate(reversed(historico_times)):
            if t not in atrasos:
                atrasos[t] = dist

        resultado = []
        for time_nome, freq in contagens.most_common():
            fr = round(freq / media_esperada, 3) if media_esperada > 0 else 1.0
            resultado.append({
                "time": time_nome,
                "frequencia": freq,
                "fr": fr,
                "atraso": atrasos.get(time_nome, total),
                "pct": round((freq / total) * 100, 2)
            })

        return resultado

    @classmethod
    def avaliar_proximidade(cls, jogo: List[int], sorteios: List[List[int]]) -> Dict[str, Any]:
        """
        Avalia as métricas espaciais do jogo decagonal frente a um histórico de sorteios da Timemania.
        """
        if not sorteios:
            return {
                "distancia_media": 0.0,
                "distancia_maxima": 0,
                "pct_dezenas_dist_le_1": 0.0,
                "pct_concursos_com_vizinho": 0.0,
                "media_acertos_exatos_por_concurso": 0.0,
                "distribuicao_acertos": {}
            }

        distancias = []
        acertos_exatos = 0
        acertos_dist_1 = 0
        concursos_com_vizinho = 0
        acertos_dist = {i: 0 for i in range(8)}
        total_dezenas = len(sorteios) * cls.DEZENAS_SORTEIO

        jogo_set = set(jogo)

        for d in sorteios:
            exatos = len(jogo_set & set(d))
            acertos_exatos += exatos
            if exatos < 8:
                acertos_dist[exatos] += 1
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
            "media_acertos_exatos_por_concurso": round(acertos_exatos / len(sorteios), 4),
            "distribuicao_acertos": {k: v for k, v in acertos_dist.items() if v > 0}
        }


# Alias universal
ModeloDecagonal = ModeloDecagonalTimemania


if __name__ == "__main__":
    modelo = ModeloDecagonalTimemania()
    print("=== MODELO DECAGONAL DE DISPERSÃO E PROXIMIDADE (TIMEMANIA N=80, m=10) ===")
    for v in modelo.gerar_variantes_canonicas():
        print(f"\n[{v['nome']}]")
        print(f"  Dezenas: {v['dezenas']}")
        print(f"  Time do Coração: {v['time_sugerido']}")
        print(f"  Distância máxima garantida: <= {v['dist_max']} unidades")
        print(f"  Equilíbrio: {v['pares']}P / {v['impares']}I | Soma: {v['soma']}")
        print(f"  Descrição: {v['descricao']}")
