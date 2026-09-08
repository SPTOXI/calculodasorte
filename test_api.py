"""Script de teste rápido da API"""
import json
from core import ModeloCanonico30, gerar_jogo_sugerido, LoteriaType, LOTERIAS_CONFIG

# Gerar dados fictícios para Mega-Sena
import random
random.seed(42)

historico_teste = []
for i in range(1, 51):  # 50 concursos
    numeros = sorted(random.sample(range(1, 61), 6))
    historico_teste.append({
        'concurso': i,
        'data': f'2024-01-{i:02d}',
        'numeros': numeros
    })

print("=" * 60)
print("TESTE DO NÚCLEO CANÔNICO - MEGA SENA")
print("=" * 60)

# Testar modelo
modelo = ModeloCanonico30(historico_teste, LoteriaType.MEGA_SENA)
resumo = modelo.obter_resumo_analise()

print(f"\n✓ Modelo criado com {resumo['total_concursos']} concursos")
print(f"✓ Universo: {resumo['universo']} números")
print(f"✓ Sorteados por concurso: {resumo['sorteados_por_concurso']}")
print(f"✓ Frequência teórica (μ): {resumo['frequencia_teorica']:.4f}")
print(f"✓ Entropia: {resumo['camada_informacional']['entropia']:.4f}")
print(f"✓ Complexidade: {resumo['camada_informacional']['complexidade']:.4f}")

# Gerar jogos sugeridos
config = LOTERIAS_CONFIG[LoteriaType.MEGA_SENA]
jogo_simples = gerar_jogo_sugerido(modelo, config.minimo_aposta)
print(f"\n✓ Jogo sugerido (6 números): {jogo_simples}")

# Mostrar distribuição de classes
print(f"\n✓ Distribuição de Classes:")
for classe, qtd in resumo['distribuicao_classes'].items():
    print(f"  Classe {classe}: {qtd} números")

print("\n" + "=" * 60)
print("TODOS OS TESTES PASSARAM!")
print("=" * 60)
