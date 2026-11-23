# Regressão Logística — Mega-Sena 1.0

**Status:** implementação experimental; não integrada ao gerador canônico.  
**Módulo:** `regressao_logistica_mega_sena.py`

## Objetivo

Estimar uma probabilidade marginal para cada dezena (01–60) no próximo concurso, usando classificação binária supervisionada. Cada exemplo representa uma dezena em uma origem temporal: o rótulo vale 1 se a dezena apareceu no concurso daquela origem e 0 caso contrário.

## Atributos

Para cada dezena, são calculados exclusivamente a partir do prefixo anterior à origem:

- frequência nas janelas de 30, 60, 100 e 150 concursos;
- frequência acumulada desde o início do histórico disponível;
- distância temporal desde a última ocorrência, limitada à maior janela;
- identidade da dezena, codificada em one-hot com 60 posições.

A identidade permite interceptos específicos por dezena dentro do classificador compartilhado. A padronização é ajustada dentro de cada retreinamento, usando apenas os exemplos de treino.

## Treinamento e avaliação

- Modelo: `StandardScaler + LogisticRegression` (L2, `lbfgs`, `C=1`, semente 42).
- Rótulos: 60 alvos binários por concurso.
- Histórico inicial para atributos: 150 concursos.
- Origens históricas mínimas para o primeiro ajuste: 150.
- Primeiro alvo de teste: após 300 concursos.
- Retreinamento padrão: a cada 25 alvos; entre ajustes, o classificador fica congelado.
- Métrica principal: Brier médio nos 60 indicadores por concurso.
- Comparador: baseline uniforme no mesmo período de teste.
- Métrica descritiva adicional: média de acertos das seis dezenas de maior probabilidade.

A previsão de cada alvo usa somente rótulos de origens anteriores. O retreinamento em blocos reduz custo computacional, mas significa que resultados ocorridos entre dois retreinamentos só entram no ajuste seguinte.

## Dependências e execução

Instalar:

```bash
pip install numpy scikit-learn
```

Executar com histórico completo em JSON, em ordem cronológica:

```bash
python scripts/avaliar_regressao_logistica_mega_sena.py --historico data/mega_sena_historico_completo.json
```

## Limitações e interpretação

O modelo não altera as probabilidades matemáticas do sorteio. Em uma Mega-Sena justa, cada dezena tem probabilidade marginal teórica de 6/60 = 0,10 em cada concurso. Probabilidades estimadas diferentes de 0,10 são hipóteses aprendidas do histórico e precisam demonstrar calibração e ganho fora da amostra.

A implementação é experimental. Os testes de unidade verificam a construção temporal das features; a execução integral e a avaliação com a base completa ainda precisam ser realizadas em ambiente com NumPy, scikit-learn e histórico auditado. Nenhum resultado de desempenho é declarado neste documento.
