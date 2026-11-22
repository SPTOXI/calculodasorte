"""Executa a primeira comparação de baselines da Mega-Sena.

Uso:
    python scripts/avaliar_baselines_mega_sena.py
    python scripts/avaliar_baselines_mega_sena.py --historico data/mega_sena_historico.json
"""
import argparse
import json

from ml_baselines import carregar_historico_json, avaliar_walk_forward, relatorio_previsao_atual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--historico",
        default="data/mega_sena_historico.json",
        help="JSON com concursos em ordem cronológica (padrão: %(default)s)",
    )
    parser.add_argument("--minimo-treino", type=int, default=150)
    args = parser.parse_args()

    historico = carregar_historico_json(args.historico)
    saida = {
        "avaliacao_walk_forward": avaliar_walk_forward(historico, args.minimo_treino),
        "escores_para_proximo_concurso": relatorio_previsao_atual(historico, args.minimo_treino),
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
