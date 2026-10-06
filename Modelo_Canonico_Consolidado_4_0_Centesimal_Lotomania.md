# Modelo Canônico Consolidado 4.0 — Otimização Centesimal e Matricial 10x10 (MCOC 4.0)

## Lotomania ($N = 100, k = 20, m = 50$)
**Calculadora da Sorte — Documentação Técnica & Metodológica**  
**Versão:** 4.4.0 | **Data de Implementação:** Outubro/2026  
**Módulos:** `modelo_lotomania.py`, `core.py`, `avaliacao.py`, `templates/analise.html`, `templates/seo_metodologia.html`

---

## 1. Visão Geral e Fundamentação Teórica

A **Lotomania** possui a dinâmica combinatorial mais singular entre as loterias de prognósticos numéricos da Caixa Econômica Federal:
1. **Universo Centesimal ($N = 100$):** O volante é composto por 100 dezenas, numeradas de $00$ a $99$.
2. **Sorteio Principal ($k = 20$):** São sorteadas exatamente 20 dezenas distintas por concurso.
3. **Aposta Simples Extensa ($m = 50$):** O apostador seleciona obrigatoriamente 50 dezenas (exatamente metade do volante, $50\%$).
4. **Premiação por Faixas Múltiplas:** Faixas para 20, 19, 18, 17, 16, 15 acertos e premiação especial para 0 acertos.

O **Modelo Canônico 4.0 Centesimal (MCOC 4.0)** estabelece a formulação geométrica canônica para a Lotomania em um espaço bidimensional discreto reticulado $\mathcal{M}_{10 \times 10}$, minimizando a distância ortogonal de Manhattan ($L_1$) entre a aposta e os sorteios, garantindo simetria de quadrantes, partição moldura/miolo e equilíbrio estocástico modal de 25 pares e 25 ímpares.

---

## 2. Topologia Espacial Matricial $10 \times 10$

### 2.1 Mapeamento Cartesiano do Volante
Cada dezena $n \in \{0, \dots, 99\}$ é mapeada de forma biunívoca em coordenadas cartesianas discretas:
$$n \mapsto (r, c) = \left(\lfloor n / 10 \rfloor,\, n \bmod 10\right), \quad r, c \in \{0, 1, \dots, 9\}$$

### 2.2 Métrica de Manhattan ($L_1$)
No reticulado $10 \times 10$, a distância de Manhattan entre duas dezenas $a = (r_a, c_a)$ e $b = (r_b, c_b)$ é definida por:
$$d_{L_1}(a, b) = |r_a - r_b| + |c_a - c_b|$$

### 2.3 Partição em 4 Quadrantes $5 \times 5$
O volante é dividido simetricamente em quatro quadrantes de $25$ números cada ($5$ linhas $\times$ $5$ colunas):
- **Q1 (Noroeste):** $r < 5$ e $c < 5$ (dezenas 00-04, 10-14, 20-24, 30-34, 40-44)
- **Q2 (Nordeste):** $r < 5$ e $c \ge 5$ (dezenas 05-09, 15-19, 25-29, 35-39, 45-49)
- **Q3 (Sudoeste):** $r \ge 5$ e $c < 5$ (dezenas 50-54, 60-64, 70-74, 80-84, 90-94)
- **Q4 (Sudeste):** $r \ge 5$ e $c \ge 5$ (dezenas 55-59, 65-69, 75-79, 85-89, 95-99)

A esperança matemática teórica para uma aposta de $50$ dezenas é de exatamente:
$$\mathbb{E}[Q_i] = \frac{50}{4} = 12,5 \text{ dezenas por quadrante}$$
Configurações equilibradas canônicas adotam a partição ótima de $13 / 12 / 12 / 13$.

### 2.4 Moldura vs. Miolo
- **Moldura Exterior ($36$ dezenas):** Linhas $0$ e $9$, Colunas $0$ e $9$.
- **Miolo Interior ($64$ dezenas):** Linhas $1$ a $8$, Colunas $1$ a $8$.
- **Esperança Matemática:** Com $50\%$ do volante preenchido:
  $$\mathbb{E}[\text{Moldura}] = 36 \times 0,5 = 18 \text{ dezenas}$$
  $$\mathbb{E}[\text{Miolo}] = 64 \times 0,5 = 32 \text{ dezenas}$$

---

## 3. Base Pura Centesimal (Padrão Xadrez) e Cota Máxima $K\text{-Medians}$

A **Base Centesimal Pura** $\mathcal{B}_{0}$ é construída segundo a paridade da soma de índices do reticulado:
$$\mathcal{B}_0 = \{n \in \{0, \dots, 99\} \mid (r + c) \equiv 0 \pmod 2\}$$

### 3.1 Propriedades Determinísticas da Base Pura
1. **Total de Dezenas:** $|\mathcal{B}_0| = 50$ (exatamente $50\%$ do volante).
2. **Distribuição em Linhas e Colunas:** Exatamente $5$ dezenas por linha e $5$ dezenas por coluna.
3. **Equilíbrio de Paridade:** Exatamente $25$ pares e $25$ ímpares.
4. **Moldura e Miolo:** Exatamente $18$ na moldura e $32$ no miolo.
5. **Baricentro de Soma:**
   $$\sum_{n \in \mathcal{B}_0} n = 2.475 \quad (\text{Média por dezena} = 49,5)$$
6. **Cota Máxima de Manhattan no Grid:**
   $$\max_{x \in \{0,\dots,99\}} \min_{b \in \mathcal{B}_0} d_{L_1}(x, b) \le 1 \text{ passo}$$
   Todo número não marcado no volante possui pelo menos um vizinho marcado a $\le 1$ passo ortogonal.

---

## 4. As 5 Variantes Harmônicas Canônicas da Lotomania

| Variante | Perfil Estrutural | Cota Grid | Moldura / Miolo | Paridade | Soma | Propósito |
|---|---|:---:|:---:|:---:|:---:|---|
| **Regular Puro** | Padrão xadrez $(r+c) \equiv 0 \pmod 2$ | $\le 1$ | 18M / 32M | 25P / 25I | 2.475 | Cobertura reticulada máxima |
| **Alpha** | Ajuste harmônico de quadrantes ($13/12/12/13$) | $\le 1$ | 18M / 32M | 25P / 25I | 2.475 | Simetria rigorosa inter-quadrantes |
| **Beta** | Espelho ortogonal complementar $(r+c) \equiv 1 \pmod 2$ | $\le 1$ | 18M / 32M | 25P / 25I | 2.475 | Cobertura complementar simétrica |
| **Gamma** | Alternância cruzada de linhas e colunas | $\le 1$ | 18M / 32M | 25P / 25I | 2.475 | Dispersão uniforme balanceada |
| **Delta** | Deslocamento angular anti-vícios populares | $\le 2$ | 20M / 30M | 25P / 25I | ~2.475 | Anti-divisão de prêmio em rateios |

---

## 5. Validação Empírica (150 Concursos Oficiais Caixa — 2835 a 2984)

Backtest executado no histórico oficial completo da Lotomania com 20 dezenas sorteadas por concurso:

1. **Distância Média no Grid:** $\approx 0,49$ a $0,51$ passos de Manhattan.
2. **Dezenas a $\le 1$ passo:** $100,0\%$ das dezenas sorteadas pela Caixa possuem um vizinho no jogo canônico a $\le 1$ passo de distância.
3. **Média de Acertos Exatos:** **$10,02$ acertos por concurso**, convergindo exatamente para a esperança teórica $\mathbb{E}[X] = 20 \times 0,5 = 10,00$.
4. **Concursos com Todos Vizinhos a $\le 1$:** **$100,0\%$**.

---

## 6. Integração Sistêmica
- `core.py`: Implementação do método `calcular_dispersao_centesimal_lotomania(jogo)` com IDE Centesimal 4.0, geradores `gerar_jogos_lotomania` e despacho automático em `analisar_sistema`.
- `avaliacao.py`: Detecção da topologia centesimal, emissão do parecer MCOC 4.0 e indicadores de quadrantes.
- `templates/analise.html`: Badge `Dispersão Centesimal 4.0 (MCOC)` com detalhamento de quadrantes, moldura/miolo e IDE.
- `templates/seo_metodologia.html`: Documentação pública da metodologia MCOC 4.0.
