"""Executa a regressão logística walk-forward da Mega-Sena.

Uso:
  python scripts/avaliar_regressao_logistica_mega_sena.py --historico caminho.json
"""
import argparse
import json

from ml_baselines import carregar_historico_json
from regressao_logistica_mega_sena import avaliar_regressao_logistica_walk_forward


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historico", required=True, help="JSON cronológico com concursos.")
    parser.add_argument("--min-historico", type=int, default=150)
    parser.add_argument("--minimo-origens-treino", type=int, default=150)
    parser.add_argument("--intervalo-retreino", type=int, default=25)
    args = parser.parse_args()

    historico = carregar_historico_json(args.historico)
    resultado = avaliar_regressao_logistica_walk_forward(
        historico,
        min_historico=args.min_historico,
        minimo_origens_treino=args.minimo_origens_treino,
        intervalo_retreino=args.intervalo_retreino,
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
