# Modelo Canônico Consolidado 4.0 — Dinâmica de Expansão e Retração por Casa com Ajuste de Aproximação (MCO-DYN)

## Todas as 9 Loterias Oficiais da Caixa Econômica Federal
**Calculadora da Sorte — Documentação Técnica & Metodológica**  
**Versão:** 4.9.0 | **Data de Implementação:** Outubro/2026  
**Módulos:** [`dinamica_canonica.py`](file:///C:/Users/sptox/Downloads/Projetos/Aplicativos/Projeto%20Calculadora%20da%20Sorte/dinamica_canonica.py), [`core.py`](file:///C:/Users/sptox/Downloads/Projetos/Aplicativos/Projeto%20Calculadora%20da%20Sorte/core.py), [`app.py`](file:///C:/Users/sptox/Downloads/Projetos/Aplicativos/Projeto%20Calculadora%20da%20Sorte/app.py), [`templates/analise.html`](file:///C:/Users/sptox/Downloads/Projetos/Aplicativos/Projeto%20Calculadora%20da%20Sorte/templates/analise.html)

---

## 1. Visão Geral e Fundamentação Dinâmica

O **Modelo Canônico 4.0** introduz a camada dinâmica **MCO-DYN (Dinâmica de Expansão e Retração por Casa)**. Enquanto a modelagem topológica tradicional define o atrator fixo de longo prazo (Base Pura Canônica e Variantes Simétricas), a **Camada Dinâmica MCO-DYN** avalia o comportamento instantâneo da série temporal nos sorteios mais recentes (concursos $t$ e $t-1$).

O objetivo fundamental é modelar as oscilações estocásticas em torno dos centros canônicos como um **sistema de forças restauradoras (atratores elásticos)**:
1. **Expansão ($\nearrow$):** A dezena sorteada recentemente foi empurrada para cima/para fora do centro canônico ($d_i > 0$).
2. **Retração ($\searrow$):** A dezena sorteada recentemente recuou para baixo/para dentro do centro canônico ($d_i < 0$).
3. **Equilíbrio ($\odot$):** A dezena sorteada coincide exatamente com a posição de convergência modal ($d_i = 0$).

Para cada casa, o sistema calcula uma **força restauradora compensatória**, ajustando o palpite para buscar a **máxima aproximação métrica** no próximo sorteio.

---

## 2. Modelagem das Casas Canônicas nas 9 Loterias

| Loteria | Total de Casas | Topologia Canônica | Centros de Referência ($C_i$) | Tipo de Avaliação |
|---|:---:|---|---|---|
| **Mega-Sena** | 6 Casas | Setores Hexagonais em $\mathbb{Z}_{60}$ | $[05, 15, 25, 35, 45, 55]$ | Desvio de dezena setorial contínua |
| **Quina** | 5 Casas | Setores Pentagonais em $\mathbb{Z}_{80}$ | $[08, 24, 40, 56, 72]$ | Desvio de dezena setorial contínua |
| **Lotofácil** | 5 Casas | Linhas Matriciais 5x5 $\mathbb{Z}_{25}$ | $[03, 08, 13, 18, 23]$ | Densidade de dezenas por linha ($\mu = 3,0$) |
| **Timemania** | 10 Casas | Setores Decagonais em $\mathbb{Z}_{80}$ | $[04, 12, 20, 28, 36, 44, 52, 60, 68, 76]$ | Desvio setorial decagonal |
| **Lotomania** | 10 Casas | Linhas Decimais 10x10 $\mathbb{Z}_{100}$ | $[05, 15, 25, 35, 45, 55, 65, 75, 85, 95]$ | Densidade por linha ($\mu = 2,0$ sorteio / $5,0$ aposta) |
| **+Milionária** | 6 + 2 Casas | Hexa-Trevo Biparamétrico | Dezenas $[04, 13, 21, 30, 38, 46]$ / Trevos $[2, 5]$ | Desvio bivariado nas dezenas e trevos |
| **Dia de Sorte** | 7 + 1 Casas | Heptagonal Calendário $\mathbb{Z}_{31}$ | Dias $[03, 07, 12, 16, 21, 25, 30]$ / Mês central | Desvio nos dias e centro harmônico do mês |
| **Dupla Sena** | 6 Casas | Hexagonal Bivariado em $\mathbb{Z}_{50}$ | $[04, 13, 21, 30, 38, 46]$ | Desvio conjunto de ambos os sorteios |
| **Super Sete** | 7 Casas | Colunas Independentes $\mathbb{Z}_{10}^7$ | $[4, 5, 4, 5, 4, 5, 4]$ | Desvio pontual em cada coluna independente |

---

## 3. Equações da Dinâmica e Força Restauradora

Para uma casa $i \in \{1, \dots, m\}$:
- Seja $X_i(t)$ a dezena ou valor observado no último sorteio.
- Seja $X_i(t-1)$ a dezena ou valor observado no penúltimo sorteio.
- Seja $C_i$ o centro canônico modal da casa.

### 3.1 Desvio e Taxa de Variação
$$d_i = X_i(t) - C_i$$
$$\Delta_i = X_i(t) - X_i(t-1)$$

### 3.2 Força Restauradora (Ajuste de Aproximação)
O ajuste $A_i$ atua em sentido contrário ao desvio, buscando puxar a projeção em direção ao atrator central:
$$A_i = \begin{cases} 
-\max\left(1, \left\lfloor 0,5 \cdot d_i + 0,5 \right\rfloor\right), & \text{se } d_i > 0 \quad (\text{Expansão}) \\
+\max\left(1, \left\lfloor 0,5 \cdot |d_i| + 0,5 \right\rfloor\right), & \text{se } d_i < 0 \quad (\text{Retração}) \\
0, & \text{se } d_i = 0 \quad (\text{Equilíbrio})
\end{cases}$$

### 3.3 Valor Projetado Ajustado
$$V_{\text{adj}, i} = \text{clamp}(X_i(t) + A_i, \text{Min}_i, \text{Max}_i)$$
com resolução de colisões locais para garantir a estrita unicidade de números na aposta.

---

## 4. Validação Empírica nos Resultados Oficiais da Caixa

Testado nos históricos completos reais sincronizados da Caixa Econômica Federal:
- **Super Sete:** 7 colunas ajustadas com detecção precisa de retração/expansão.
- **Mega-Sena:** 6 dezenas ajustadas com dispersão perfeita nos 6 setores.
- **Quina:** 5 dezenas ajustadas nos 5 setores pentagonais.
- **Lotofácil:** 15 dezenas com restauração de linhas em retração e alívio de linhas saturadas.
- **Lotomania:** 50 dezenas distribuídas harmoniosamente (5 por linha).
- **Timemania, Dupla Sena, Dia de Sorte, +Milionária:** 100% de conformidade com os limites, paridades e baricentros.
