# 📜 Registro Oficial de Alterações (CHANGELOG)
## Projeto Calculadora da Sorte — Modelo Canônico 4.0 + MCOH + MCP-MD 1.0

Todas as alterações, adições de recursos, correções e versões deste software são registradas de forma contínua neste documento e versionadas no repositório GitHub oficial: [`https://github.com/SPTOXI/calculodasorte.git`](https://github.com/SPTOXI/calculodasorte.git).

### [v4.5.0] - 2026-10-06 — Modelo Canônico 4.0 Especializado: MCOMIL (Otimização Biparamétrica Hexa-Trevo da +Milionária)
#### 🔬 Motor de Otimização Biparamétrica Hexa-Trevo (`modelo_mais_milionaria.py`, `core.py`, `avaliacao.py`, `templates/analise.html`, `templates/seo_metodologia.html`)
- **Implementação do Modelo Canônico 4.0 Exclusivo da +Milionária (MCOMIL 4.0):**
  - Especialização da **Camada 8 de Cobertura Espacial** para o produto cartesiano $\mathbb{Z}_{50} \times \mathcal{P}_2(\{1..6\})$ da +Milionária ($N=50, k=6$, aposta simples de $m=6$ dezenas + 2 trevos dentre 6):
    - Partição regular do anel circular modular $\mathbb{Z}_{50}$ em **6 setores regulares de 8,33 dezenas cada**:
      `S0: [01..08]` (C: 04), `S1: [09..17]` (C: 13), `S2: [18..25]` (C: 21),
      `S3: [26..34]` (C: 30), `S4: [35..42]` (C: 38), `S5: [43..50]` (C: 46).
    - Cota máxima de proximidade circular no anel $\mathbb{Z}_{50}$: **determinística e estritamente $\le 4$ unidades** para todos os 50 números do volante.
    - Equilíbrio modal hipergeométrico nas dezenas: $3\text{P}/3\text{I}$ ($33,29\%$).
    - Baricentro de soma ótimo calibrado em $\mu = 6 \times 25,5 = 153,0$.
    - **Modelagem do Subespaço de Trevos:** Paridade modal de 1 Par e 1 Ímpar ($60\%$ de probabilidade teórica) com baricentro de soma $\mathbb{E}[S_T] = 7,0$.
  - Cinco variantes biparamétricas canônicas: Base Pura Hexa-Trevo, Alpha ($3\text{P}/3\text{I}$, trevos $[3,4]$), Beta (Soma 153 exata, trevos $[1,6]$), Gamma (Harmônica setorial, trevos $[2,5]$) e Delta (Anti-divisão de prêmio, trevos $[3,5]$).
- **Despacho Polimórfico Espacial Sêxtuplo Consolidado em `core.py`:**
  - `core.py` agora despacha dinamicamente `calcular_dispersao_espacial`, `gerar_jogo_sugerido` e `gerar_multiplos_jogos` para as 6 loterias com modelos geométricos canônicos dedicados:
    - **+Milionária** $\to$ Hexa-Trevo Biparamétrico (MCOMIL 4.0, anel $\mathbb{Z}_{50}$ + Trevos $\mathcal{T}$, cota $\le 4$).
    - **Lotomania** $\to$ Centesimal (MCOC 4.0, grid $10 \times 10$, quadrantes, moldura/miolo, cota Manhattan $\le 1$).
    - **Timemania** $\to$ Decagonal (MCOD 4.0, 10 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 4$).
    - **Lotofácil** $\to$ Matricial 5x5 (MCOM 4.0, quintetos, moldura/miolo, cota $\le 1$).
    - **Quina** $\to$ Pentagonal (MCOP 4.0, 5 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 8$).
    - **Mega-Sena** $\to$ Hexagonal (MCOH 4.0, 6 setores no anel $\mathbb{Z}_{60}$, cota máxima $\le 5$).
- **Sincronização de Dados Oficiais da Caixa (Até Concurso 395):**
  - Compilação de 150 concursos oficiais da +Milionária (246 a 395, sorteio de 03/10/2026) em `data/mais_milionaria_historico_completo.json`.
  - Atualização dos metadados e arquivos de histórico em `data/mais_milionaria_*`.
- **Validação Empírica de Backtest:**
  - Distância circular média observada nos sorteios reais: $2,03$ a $2,09$ unidades (aderente ao teórico de $\approx 2,1$).
  - Distância máxima observada: estritamente $\le 4$ unidades em 100% dos 150 concursos analisados.
  - Mais de $60\%$ das dezenas sorteadas a $\le 2$ unidades dos centros canônicos.
- **Suíte de Testes:**
  - Adicionado `test_modelo_biparametrico_maismilionaria.py` com 6 testes unitários e de integração (100% aprovados, totalizando 53 testes na suíte global).

---

### [v4.4.0] - 2026-10-06 — Modelo Canônico 4.0 Especializado: MCOC (Otimização Centesimal e Matricial 10x10 da Lotomania)
#### 🔬 Motor de Otimização Centesimal e Matricial 10x10 (`modelo_lotomania.py`, `core.py`, `avaliacao.py`, `templates/analise.html`, `templates/seo_metodologia.html`)
- **Implementação do Modelo Canônico 4.0 Exclusivo da Lotomania (MCOC 4.0):**
  - Especialização da **Camada 8 de Cobertura Espacial** para a topologia da Lotomania ($N=100, k=20$, aposta simples de $m=50$ dezenas de 00 a 99):
    - Mapeamento bijetivo do volante em **matriz bidimensional reticulada $10 \times 10$** com coordenadas cartesianas discretas $(r, c) = (\lfloor n/10 \rfloor, n \bmod 10)$.
    - Métrica ortogonal de **distância de Manhattan ($L_1$)**: $d(a, b) = |r_a - r_b| + |c_a - c_b|$.
    - **Partição em 4 Quadrantes $5 \times 5$:** $25$ dezenas por quadrante (Q1 Noroeste, Q2 Nordeste, Q3 Sudoeste, Q4 Sudeste), com valor esperado teórico de $\mathbb{E}[Q_i] = 12,5$ dezenas (partição canônica $13/12/12/13$).
    - **Bipartição Moldura ($36$ números) vs. Miolo ($64$ números):** Proporção hipergeométrica calibrada em $18\text{M} / 32\text{M}$ ($50\%$ de cada).
    - **Equilíbrio modal de paridade estocástica:** Moda em $25\text{P} / 25\text{I}$ ($15,8\%$ no universo de 50 dezenas sorteadas).
    - **Baricentro de soma ótimo:** $\mu = 50 \times 49,5 = 2.475,0$.
  - **Base Centesimal Pura em Padrão Xadrez ($(r + c) \equiv 0 \pmod 2$):**
    - $50$ dezenas marcadas cobrindo simetricamente o volante ($5$ por linha e $5$ por coluna).
    - Cota máxima de Manhattan provada: qualquer número não marcado dista no máximo $\le 1$ passo ortogonal no grid.
  - Cinco variantes centesimais canônicas: Regular Puro (Xadrez), Alpha ($13/12/12/13$), Beta (Espelho $(r+c) \equiv 1$), Gamma (Alternância cruzada) e Delta (Descorrelacionada $\le 2$).
- **Despacho Polimórfico Espacial Quíntuplo Consolidado em `core.py`:**
  - `core.py` agora despacha dinamicamente `calcular_dispersao_espacial`, `gerar_jogo_sugerido` e `gerar_multiplos_jogos` para as 5 loterias com modelos geométricos canônicos dedicados:
    - **Lotomania** $\to$ Centesimal (MCOC 4.0, grid $10 \times 10$, quadrantes, moldura/miolo, cota Manhattan $\le 1$).
    - **Timemania** $\to$ Decagonal (MCOD 4.0, 10 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 4$).
    - **Lotofácil** $\to$ Matricial 5x5 (MCOM 4.0, quintetos, moldura/miolo, cota $\le 1$).
    - **Quina** $\to$ Pentagonal (MCOP 4.0, 5 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 8$).
    - **Mega-Sena** $\to$ Hexagonal (MCOH 4.0, 6 setores no anel $\mathbb{Z}_{60}$, cota máxima $\le 5$).
- **Sincronização de Dados Oficiais da Caixa (Até Concurso 2984):**
  - Download e compilação de 150 concursos oficiais da Lotomania (2835 a 2984, sorteio de 05/10/2026) em `data/lotomania_historico_completo.json`.
  - Atualização dos metadados e arquivos de histórico em `data/lotomania_*`.
- **Validação Empírica de Backtest:**
  - Distância média observada nos sorteios reais: $0,49$ a $0,51$ passos de Manhattan.
  - $100,0\%$ das dezenas sorteadas possuem um vizinho no jogo canônico a $\le 1$ passo de distância no grid.
  - Média de acertos exatos por concurso: $10,02$ acertos (convergência estrita com a esperança teórica de $10,0$).
- **Suíte de Testes:**
  - Adicionado `test_modelo_centesimal_lotomania.py` com 7 testes unitários e de integração (100% aprovados, totalizando 47 testes na suíte global).

---

### [v4.3.0] - 2026-10-05 — Modelo Canônico 4.0 Especializado: MCOD (Otimização Decagonal e Time do Coração da Timemania)
#### 🔬 Motor de Otimização Decagonal e Time do Coração (`modelo_decagonal_timemania.py`, `core.py`, `avaliacao.py`, `app.py`)
- **Implementação do Modelo Canônico 4.0 Exclusivo da Timemania (MCOD 4.0):**
  - Especialização da **Camada 8 de Cobertura Espacial** para a topologia da Timemania ($N=80, k=7$, aposta simples de $m=10$ números + 1 Time do Coração):
    - Divisão exata do volante em **10 setores regulares de 8 dezenas cada** no anel modular cíclico $\mathbb{Z}_{80}$ ($80 / 10 = 8.0$ exato):
      `S0: [01..08]` (C: 04), `S1: [09..16]` (C: 12), `S2: [17..24]` (C: 20), `S3: [25..32]` (C: 28), `S4: [33..40]` (C: 36),
      `S5: [41..48]` (C: 44), `S6: [49..56]` (C: 52), `S7: [57..64]` (C: 60), `S8: [65..72]` (C: 68), `S9: [73..80]` (C: 76).
    - Cota analítica máxima provada: qualquer dezena sorteada está a uma distância cíclica $K\text{-Medians} \le 4$ unidades da base decagonal.
    - Distância média teórica exata de apenas $2.00$ unidades.
    - Equilíbrio modal hipergeométrico de paridade: $5\text{P}/5\text{I}$ ($26,30\%$), acompanhado de $6\text{P}/4\text{I}$ e $4\text{P}/6\text{I}$ ($21,31\%$ cada, totalizando quase $70\%$ dos jogos).
    - Baricentro de soma ótimo calibrado em $\mu = 10 \times 40.5 = 405.0$.
  - Cinco variantes decagonais canônicas balanceadas: Base Pura Regular, Alpha ($5\text{P}/5\text{I}$), Beta ($5\text{P}/5\text{I}$, soma 405 exata), Gamma ($5\text{P}/5\text{I}$) e Delta ($5\text{P}/5\text{I}$).
- **Integração Integral do Catálogo de Times do Coração:**
  - Criação do catálogo oficial em `data/timemania_clubes.json` contendo 92 clubes cadastrados (cobrindo integralmente os 80 oficiais da Caixa, séries A/B/C do Brasileirão e clubes históricos).
  - Atualização de `opcoes_complemento('timemania')` em `app.py` para disponibilizar dinamicamente o catálogo completo de 80/82 times nas interfaces, formulários e apostas.
  - Implementação de `analisar_times_historico` com cálculo de frequência, atraso e fator de recorrência (FR) de cada clube.
- **Despacho Polimórfico Espacial Quádruplo Consolidado em `core.py`:**
  - `core.py` agora despacha dinamicamente `calcular_dispersao_espacial`, `gerar_jogo_sugerido` e `gerar_multiplos_jogos` para as 4 grandes loterias:
    - **Timemania** $\to$ Decagonal (MCOD 4.0, 10 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 4$).
    - **Lotofácil** $\to$ Matricial 5x5 (MCOM 4.0, quintetos, moldura/miolo, cota $\le 1$).
    - **Quina** $\to$ Pentagonal (MCOP 4.0, 5 setores no anel $\mathbb{Z}_{80}$, cota máxima $\le 8$).
    - **Mega-Sena** $\to$ Hexagonal (MCOH 4.0, 6 setores no anel $\mathbb{Z}_{60}$, cota máxima $\le 5$).
  - Parecer técnico em `avaliacao.py` reporta dinamicamente a geometria `Decagonal` com sigla `MCOD 4.0`.
- **Sincronização de Dados Reais da Caixa (Até Concurso 2450):**
  - Download e compilação de 151 concursos oficiais da Timemania (2300 a 2450, sorteio de 03/10/2026) em `data/timemania_historico_completo.json`.
  - Atualização de `data/timemania_concursos.json`, `data/timemania_historico.json`, `data/timemania_times.json` e `data/timemania_meta.json`.
- **Validação Empírica de Backtest:**
  - Distância média observada nos sorteios reais: $1.968$ unidades (aderente ao teórico de $2.00$).
  - $98.68\%$ dos concursos com pelo menos 1 vizinho direto ($\le 1$) do reticulado decagonal.
- **Suíte de Testes:**
  - Adicionado `test_modelo_decagonal_timemania.py` com 9 testes unitários e de integração cobrindo métricas em $\mathbb{Z}_{80}$, cota máxima $\le 4$, geradores, parecer técnico e catálogo de clubes (100% aprovados).

---

### [v4.2.0] - 2026-10-05 — Modelo Canônico 4.0 Especializado: MCOM (Otimização Matricial 5x5 e Quintetos da Lotofácil)
#### 🔬 Motor de Otimização Matricial e Quintetos (`modelo_lotofacil.py`, `core.py`, `avaliacao.py`)
- **Implementação do Modelo Canônico 4.0 Exclusivo da Lotofácil (MCOM 4.0):**
  - Especialização da **Camada 8 de Cobertura Espacial** para a topologia bidimensional da Lotofácil ($N=25, k=15$, densidade amostral ultra-alta de $60\%$):
    - Matriz reticulada $5 \times 5$ com análise de quintetos horizontais e verticais.
    - Balanceamento canônico ótimo entre **Moldura (16 dezenas)** e **Miolo (9 dezenas)** no ponto modal $10\text{M}/5\text{M}$ (ou $9\text{M}/6\text{M}$), faixa que concentra mais de $78\%$ de todos os sorteios históricos.
    - Distribuição perfeitamente equilibrada de 3 dezenas por linha ($3-3-3-3-3$) e 3 por coluna.
    - Equilíbrio modal estocástico de paridade: $8\text{I}/7\text{P}$ ($31,19\%$ hipergeométrico) e $7\text{I}/8\text{P}$ ($25,99\%$).
    - Teorema aritmético da paridade da soma: baricentro em 195 para $7\text{I}/8\text{P}$ e $194/196$ para $8\text{I}/7\text{P}$.
  - Cota analítica superior provada: toda aposta balanceada do MCOM 4.0 possui cota máxima no grid $\le 1$ passo de Manhattan, assegurando **100% de vizinhança imediata** para qualquer número sorteado.
  - Cinco variantes canônicas estruturadas: Base Matricial Pura, Alpha ($8\text{I}/7\text{P}$), Beta ($7\text{I}/8\text{P}$), Gamma ($8\text{I}/7\text{P}$ 9M/6M) e Delta ($7\text{I}/8\text{P}$ 9M/6M).
- **Backtest Empírico nos 2.921 Concursos Históricos da Lotofácil:**
  - Avaliação extensiva em toda a base histórica oficial consolidada (do concurso 876 ao 3796):
    - **100,0% das dezenas sorteadas** em toda a história da Lotofácil estão a uma distância Manhattan $\le 1$ de qualquer variante do modelo.
    - Média observada de acertos exatos: **9,01 a 9,05 por concurso** (convergência estocástica perfeita com a esperança teórica de $9,00$).
    - Taxa de concursos premiados ($\ge 11$ acertos): **10,65% a 11,30%** (alinhada com a probabilidade hipergeométrica cumulativa de $\approx 11,2\%$).
- **Despacho Polimórfico Espacial Ternário:**
  - `core.py` agora despacha dinamicamente `calcular_dispersao_espacial`, `gerar_jogo_sugerido` e `gerar_multiplos_jogos`:
    - **Lotofácil** $\to$ Camada 8 Matricial 5x5 e Quintetos (MCOM 4.0).
    - **Quina** $\to$ Camada 8 Pentagonal (MCOP 4.0).
    - **Mega-Sena** $\to$ Camada 8 Hexagonal (MCOH 4.0).
  - Parecer técnico em `avaliacao.py` reporta dinamicamente a geometria e a sigla correspondente (`MCOM 4.0` na Lotofácil).
- **Sincronização de Dados Oficiais da Lotofácil:**
  - Atualização do resultado oficial Caixa até o concurso **3796** (03/10/2026: `03 04 05 06 07 09 10 11 12 15 16 19 20 21 24`).
  - Criação de `data/lotofacil_concursos.json`, atualização de `data/lotofacil_historico.json` e arquivamento de 2.921 concursos em `data/lotofacil_historico_completo.json`.
- **Suíte de Testes:**
  - Adicionado `test_modelo_matricial_lotofacil.py` com 12 testes unitários e de integração (100% aprovados).

---

### [v4.1.0] - 2026-10-05 — Modelo Canônico 4.0 Especializado: MCOP (Otimização Pentagonal da Quina)
#### 🔬 Motor de Otimização Espacial Pentagonal (`modelo_pentagonal.py`, `core.py`, `avaliacao.py`)
- **Implementação do Modelo Pentagonal Exclusivo da Quina (MCOP 4.0):**
  - Especialização da **Camada 8 de Cobertura Espacial** por topologia de loteria: enquanto a Mega-Sena ($N=60, k=6$) opera com o reticulado **Hexagonal (MCOH)** de 6 setores, a Quina ($N=80, k=5$) agora opera nativamente com o reticulado **Pentagonal (MCOP)** de 5 setores regulares de 16 dezenas no anel modular cíclico $\mathbb{Z}_{80}$.
  - Divisão perfeita do volante em 5 setores contínuos: Setor 1 [01..16], Setor 2 [17..32], Setor 3 [33..48], Setor 4 [49..64] e Setor 5 [65..80], com centros naturais em `[08, 24, 40, 56, 72]`.
  - Cota analítica superior provada: qualquer dezena de 01 a 80 dista no máximo $\le 8$ unidades de um vértice pentagonal, com distância média teórica de exatamente $4,00$ unidades.
  - Variantes harmônicas canônicas (Alpha, Beta, Gamma, Delta) com perturbação mínima ($\pm 1$) para equilíbrio estatístico de paridade ($3\text{P}/2\text{I}$ ou $2\text{P}/3\text{I}$) e respeito às diretrizes anti-compartilhamento de prêmio.
- **Backtest Empírico nos 5.326 Concursos Históricos da Quina:**
  - Avaliação extensiva em toda a base histórica oficial (concursos 1809 a 7134, cobrindo 19 anos):
    - Distância média observada nos sorteios reais: **3,98 unidades** (confirmando a previsão teórica).
    - Em **65,7% de todos os concursos da história da Quina**, pelo menos uma dezena sorteada caiu a uma distância $\le 1$ dos vértices pentagonais.
- **Despacho Polimórfico Espacial:**
  - `core.py` agora despacha dinamicamente `calcular_dispersao_espacial`, `gerar_jogo_sugerido` e `gerar_multiplos_jogos`:
    - Quina $\to$ Camada 8 Pentagonal (MCOP).
    - Mega-Sena $\to$ Camada 8 Hexagonal (MCOH).
  - Preservação total de retrocompatibilidade com `calcular_dispersao_hexagonal`.
- **Sincronização de Dados Oficiais da Quina:**
  - Atualização do resultado oficial Caixa até o concurso **7134** (03/10/2026: `14 15 43 54 72`).
  - Criação de `data/quina_concursos.json`, atualização de `data/quina_historico.json` e armazenamento da base completa em `data/quina_historico_completo.json`.
- **Suíte de Testes:**
  - Adicionado `test_modelo_pentagonal_quina.py` com 10 testes unitários e de integração (100% aprovados).

---

### [v4.0.0] - 2026-10-05 — Modelo Canônico 4.0 (MCOH — Otimização Hexagonal & Dispersão Espacial K-Medians)
#### 🔬 Novo Motor de Otimização Espacial (`core.py`, `modelo_hexagonal.py`, `avaliacao.py`)
- **Implementação do Modelo Canônico 4.0 (`ModeloCanonico40`):**
  - Substituição da arquitetura prévia pelo **Modelo Canônico 4.0**, incorporando a **Camada 8: Dispersão Espacial Hexagonal (MCOH)** e cobertura geométrica K-Medians.
  - Otimização com base no espaço fechado $\mathbb{Z}_N$ ($N=60$ para Mega-Sena), provando que um arranjo de hexágono regular com espaçamento $\delta = 10$ assegura distância máxima $\le 5$ unidades e distância média observada de 2,49 unidades para qualquer concurso histórico.
  - Implementação de métricas geométricas no parecer: **IDE (Índice de Dispersão Espacial)**, setores hexagonais cobertos (1 a 6) e distribuição harmônica par/ímpar (3P/3I).
- **Módulo Dedicado `modelo_hexagonal.py`:**
  - Gerador de redes hexagonais simétricas puras (`[05, 15, 25, 35, 45, 55]`) e variantes harmônicas balanceadas (Alpha, Beta, Gamma).
  - Cálculo de distâncias ciclotômicas e métricas de vizinhança $\le 1$ unidade.
- **Retrocompatibilidade Garantida:**
  - Criação do alias `ModeloCanonico30 = ModeloCanonico40` para suporte transparente a integrações legadas e testes existentes sem quebras.
- **Interface e Apresentação (UI & IA):**
  - Atualização completa de landing page, parecer de análise, metodologia SEO, planos de assinatura e prompts do agente de IA (`ai_agent.py`) para **Modelo Canônico 4.0**.
  - Exibição de badge e métricas de dispersão hexagonal no modal de parecer de jogos gerados.
- **Suíte de Testes:**
  - Adicionado `test_modelo_canonico_40.py` com testes unitários rigorosos cobrindo cálculo de IDE, setores cobertos, geração de volantes hexagonais, retrocompatibilidade e integração do parecer.

---

### [v1.8.0] - 2026-09-29 — Alinhamento do Modelo Canônico ao documento (janelas de 100/150 concursos) & Importação de resultados anteriores
#### 🔬 Modelo Canônico 3.0 / MCP-MD (`core.py`, `validacao.py`) — commit `399f42c`
- **MCP-MD só com histórico completo:** o IMC, o γ e o score MCP exigem **pelo menos 150 concursos**, para completar as janelas formais **W1 = 100** e **W2 = 150** (antes eram calculados com janelas truncadas). Abaixo disso, o modelo informa `MCP-MD indisponível` e o motivo em `obter_status_mcp()`, sem contribuição do MCP no score.
- **γ = Var(W1) / Var(histórico)**, sem elevar ao quadrado uma segunda vez; indefinido quando a dispersão histórica é nula.
- **Classes do ICT por quartis** do próprio histórico (empates na mesma classe), no lugar dos limites fixos 0,25 / 0,50 / 0,75. As classes A–D são descritores relativos, não probabilidade de acerto.
- **Aproximações operacionais declaradas:** ICT, ISEG, C_i, P_i, pesos do ILLA e limiares de maturidade não têm fórmula no documento canônico; agora aparecem como aproximações na resposta da API e na página de metodologia.
- **Validação estatística em módulo próprio (`validacao.py`):** Monte Carlo reprodutível (semente fixa), Bayes Factor, correção de população finita e backtest walk-forward em blocos cronológicos disjuntos. **Todos os critérios** são obrigatórios: Z acumulado > 2, Bayes Factor > 10, percentil Monte Carlo < 1%, persistência em múltiplos blocos independentes e robustez no walk-forward. Com dados insuficientes o resultado é **inconclusivo**; critérios não atendidos significam "não validado nesse recorte" (não prova ruído nem vantagem futura).
- **Validação dos dados de entrada:** o histórico é conferido (inteiros, sem repetição, faixa da loteria) antes do cálculo; Dupla Sena conta os dois sorteios e Super Sete trata as colunas.
- Testes novos: `test_modelo_canonico.py` e `test_validacao_canonica.py`. README e página `/metodologia` atualizados.

#### 📥 Importação de resultados anteriores (Admin → Loterias)
- Por loteria, a partir de **planilha Excel (.xlsx)**, **CSV**, **link do Google Sheets** ou **texto colado do Excel**; a planilha oficial da Caixa é aceita sem edição (colunas extras são ignoradas).
- **Botão "Baixar tudo da API":** busca os concursos em rodadas curtas, compatíveis com o limite de tempo do Vercel.
- **Só os últimos N concursos** (padrão **300**; 0 = todos) e **concursos que já existem são ignorados**; a prévia mostra novos × existentes antes de gravar.
- Os dados ficam no PostgreSQL (`concursos_importados`) e são reaplicados após cada sincronização e a cada instância nova do Vercel.
- **Efeito sobre o modelo:** o histórico do repositório tem só 27–50 concursos por loteria, então o MCP-MD ficava indisponível. Com **150 ou mais** concursos o MCP-MD passa a ser calculado; a validação walk-forward usa blocos de 50 concursos e precisa de **300** (150 de treino + 3 × 50) para completar os 3 blocos, por isso o padrão de importação é 300. Com 200 ela fica inconclusiva (1 bloco). Nenhuma linha do modelo (`core.py`, `validacao.py`) foi alterada; a validação com 300 concursos leva cerca de 0,25 s.

---

### [v1.7.0] - 2026-09-08 — Preço Único de R$ 5,00 para Análise Avulsa & Padrões de Privacidade LGPD (Lei nº 13.709/2018)
#### 🚀 Novas Funcionalidades
- **Preço Único de R$ 5,00 para Análise Avulsa:**
  - Padronização do valor da recarga avulsa para **R$ 5,00 fixo para qualquer loteria** da Caixa Econômica Federal (Mega-Sena, Lotofácil, Quina, etc.), eliminando disparidades de preço e simplificando o funil de conversão.
  - Enforced no backend (`/api/checkout/pix` e `/api/checkout/infinitepay`) e nas interfaces (`landing.html` e `planos.html`).
- **Conformidade Completa com a LGPD (Lei nº 13.709/2018):**
  - **Consentimento Explícito no Cadastro (`/cadastro`):** Checkbox obrigatório de concordância com os Termos de Uso e Política de Privacidade e declaração de maioridade (+18 anos), gravando `accepted_terms_at` no banco SQLite.
  - **Página de Política de Privacidade (`/privacidade`):** Documento jurídico completo indicando Encarregado pelo Tratamento de Dados (DPO Silvio Luis Morais, `silvio.luis.morais@gmail.com`), bases legais (Art. 7º), segurança criptográfica e finalidades.
  - **Página de Termos de Uso e Jogo Responsável (`/termos`):** Definição da natureza estocástica/matemática do Modelo Canônico 3.0, isenção de promessa de ganhos fáceis, política de entretenimento e alerta contra vício em apostas.
  - **Portabilidade de Dados Pessoais (`GET /api/usuario/exportar-dados`):** Implementação do Art. 18, V da LGPD com download em JSON estruturado do cadastro e histórico de apostas.
  - **Eliminação e Direito ao Esquecimento (`POST /api/usuario/excluir-conta`):** Implementação do Art. 18, VI da LGPD com exclusão definitiva de conta e apostas, e anonimização de registros fiscais de pagamentos (Art. 16, I).
  - **Banner de Cookies LGPD:** Componente flutuante com persistência em `localStorage` para avisar sobre cookies de sessão essenciais.
  - **Rodapé Institucional com Links de Transparência:** Links diretos para Termos, Privacidade e Canal do DPO em `landing.html`, `index.html` e `planos.html`.

#### 🧪 Testes Automatizados
- Adicionados testes 16, 17, 18 e 19 em `test_features.py` cobrindo validação de consentimento, rotas institucionais, portabilidade, exclusão de dados e garantia do preço único de R$ 5,00 (19/19 testes passando).

---

### [v1.6.0] - 2026-09-08 — Integração InfinitePay (Taxa Zero & D+0 Instantâneo) e Gestão de Pagamentos no Admin
#### 🚀 Novas Funcionalidades
- **Checkout Oficial InfinitePay Integrado (`api.checkout.infinitepay.io`):**
  - Integração nativa com a InfinitePay utilizando o handle do administrador (`silvio_morais_`).
  - **Taxa Zero no PIX (0% de comissão)** e recebimento **imediato na hora (D+0)** na conta InfinitePay.
  - Suporte tanto a PIX quanto a Cartão de Crédito em até 12x para os apostadores.
  - Redirecionamento seguro para a página de checkout oficial com retorno automático para `/planos?checkout=sucesso`.
- **Webhook Automatizado de Pagamentos (`POST /api/webhook/infinitepay`):**
  - Confirmação em tempo real de transações pagas.
  - Liberação instantânea do Plano VIP (30 dias) ou créditos de análise para o apostador sem intervenção manual.
- **Painel Administrativo — Nova Aba "💰 Gestão de Pagamentos PIX & InfinitePay":**
  - Visualização de todas as transações registradas no sistema (ID, nome/e-mail do apostador, modalidade, valor, status e data).
  - Botão de aprovação manual com 1 clique para qualquer transação pendente.

---

### [v1.5.0] - 2026-09-08 — Landing Page de Alta Conversão, Cadastro Obrigatório, Monetização PIX & Agente Consultor IA
#### 🚀 Novas Funcionalidades
- **Landing Page de Alta Conversão (`/`):**
  - Apresentação visual moderna e persuasiva para atrair apostadores de loteria.
  - Seções de destaque: Hero com chamada para ação ("Gerar Palpites com IA"), vitrine interativa das 9 modalidades oficiais da Caixa, os 3 Pilares Científicos do Modelo Canônico 3.0, Tabela de Planos e Depoimentos de Apostadores.
  - Visitantes não autenticados veem a Landing Page; usuários autenticados são direcionados automaticamente para o `/dashboard`.
- **Autenticação Obrigatória & Cadastro de Apostadores (`/cadastro` e `/login`):**
  - Registro de novos usuários com nome, e-mail e senha.
  - Cada apostador possui conta própria e histórico privado e seguro de palpites e conferências.
  - Concessão automática de **1 crédito de degustação gratuito** no cadastro para testar a inteligência do sistema sem custo inicial.
- **Sistema de Monetização com Checkout PIX Imediato (`/planos`):**
  - **Plano VIP Mensal (R$ 29,90/mês):** Acesso ilimitado a todas as 9 loterias, gerações sem limite, exportações e pareceres com o Agente IA.
  - **Plano Avulso por Análise (R$ 3,00 a R$ 5,00):** Cobrança unitária por lote de palpites gerados ao valor exato da aposta oficial da loteria.
  - Geração automática de chave Copia e Cola do PIX e QR Code para pagamento instantâneo.
  - Tabela `payments` no SQLite para rastreamento de transações, txid e aprovação.
  - Modal de Paywall automático na interface quando os créditos se esgotam.
- **Agente IA Consultor Estatístico (`ai_agent.py`):**
  - Integração nativa e priorizada com **Moonshot AI Kimi K3** (`MOONSHOT_API_KEY`), compatível com OpenAI, com suporte a raciocínio estocástico profundo e failover ágil de alto desempenho (`kimi-k2.7-code-highspeed`).
  - Integração via REST com **Google Gemini** (chave `GEMINI_API_KEY` ou `GOOGLE_API_KEY`, modelos `gemini-flash-latest` e `gemini-2.5-flash`) e **Anthropic Claude** (`ANTHROPIC_API_KEY`).
  - **Motor Heurístico Canônico 3.0 Nativo (Fallback):** Produz pareceres técnicos e didáticos humanizados mesmo sem chaves de API externas configuradas.
  - Card de Parecer Técnico da IA na Aba do Gerador de Jogos avaliando estabilidade estocástica, entropia e balanceamento das cartelas geradas.
  - Chat Flutuante Interativo (Widget IA) no canto inferior direito para tirar dúvidas matemáticas sobre as probabilidades e estratégias da loteria em tempo real.
- **Barra de Perfil & Créditos em Tempo Real:**
  - Exibição de badge VIP (`👑 VIP ILIMITADO`) ou créditos restantes (`🪙 X CRÉDITO(S)`) no topo de todas as páginas (`/dashboard` e `/analise/<loteria>`).

---

### [v1.4.0] - 2026-09-08 — Histórico de Apostas do Usuário & Conferência Caixa
#### 🚀 Novas Funcionalidades
- **Histórico Permanente de Apostas (`user_bets`):** Criada tabela no banco SQLite (`database.db`) para persistir todos os jogos gerados e salvos pelo usuário, vinculados ao seu login ou sessão.
- **Aba "📋 Meus Jogos Salvos":**
  - Visualização em cartões de todas as apostas salvas pelo usuário com data, horário, modalidade e quantidade de jogos.
  - Badge dinâmico no cabeçalho das abas informando a contagem de apostas salvas.
  - Opções de re-download individual de cada aposta em formato `.TXT` ou `.MD`.
  - Opção para excluir apostas do histórico.
- **Conferência Automática Oficial de Acertos (`/api/apostas/conferir/<id>`):**
  - Botão **`🔍 Conferir com a Caixa`** em cada aposta salva.
  - Consulta automática ao último concurso oficial registrado da Caixa.
  - Destaca visualmente as dezenas sorteadas em cada cartela (esferas verdes/douradas).
  - Identifica e exibe premiações oficiais (ex: Sena, Quina, Quadra, Terno, etc.).
- **Botão "Salvar no Meu Histórico" no Gerador:** Adicionado na barra de exportação da Aba 3 para persistir com 1 clique qualquer pacote de jogos recém-gerado.

#### 🛡️ Correções & Segurança
- **Isolamento Total dos Dados:** O botão "Salvar no Histórico Pessoal" da Aba 2 agora grava exclusivamente na tabela `user_bets` do usuário, garantindo que o arquivo oficial de resultados da Caixa nunca seja sobrescrito por apostas manuais.

---

### [v1.3.0] - 2026-09-08 — Separação em Abas Informativas & Fechamento Manual
#### 🚀 Novas Funcionalidades
- **Separação Estrutural em Abas:**
  - **Aba 1 (`🏛️ Resultados da Caixa`):** Área estritamente informativa e somente leitura com os últimos sorteios oficiais da Caixa Econômica Federal em ordem decrescente, busca por concurso/dezenas e botão de sincronização imediata.
  - **Aba 2 (`✍️ Meus Números (Manual)`):** Área limpa e livre de JSON para o usuário digitar, colar e analisar suas próprias sequências numéricas.
  - **Aba 3 (`🎲 Gerador de Jogos`):** Gerador inteligente com seleção entre 2 modos de composição.
- **Gerador Dual-Mode com Fechamento / Desdobramento:**
  - **Modo 1 (Automático Caixa):** Composição estatística baseada no Modelo Canônico 3.0 a partir do histórico de sorteios da Caixa.
  - **Modo 2 (Composição Manual / Fechamento):** O apostador escolhe seu grupo favorito de dezenas através de um volante interativo (esferas clicáveis 1 a N) e o sistema gera as combinações selecionando unicamente dentro do universo definido.

#### 🔧 Ajustes de Regras Oficiais
- Correção do limite máximo de aposta da **Quina** para 15 números (conforme norma da Caixa).

---

### [v1.2.0] - 2026-09-08 — Sincronização Diária às 23:59h, Downloads & Validação Visual
#### 🚀 Novas Funcionalidades
- **Agendador Pontual Diário às 23:59h:**
  - Implementação de agendador em segundo plano no `updater.py` com cálculo exato do tempo restante até as 23:59:00.
  - Endpoint de cron no Vercel (`/api/cron/atualizar`) configurado no `vercel.json` (`schedule: "59 23 * * *"`).
- **Download do Histórico Oficial:** Rotas de download em formato `.MD` e `.TXT` disponíveis diretamente no topo de cada loteria.
- **Gerador de Múltiplos Jogos:** Permite selecionar quantidade de jogos (1 a 100) e quantidade de dezenas por jogo, com exportação em `.TXT`, `.MD` e layout para impressão / PDF.
- **Sinalização Visual de Regras:** Banners com regras oficiais (números no volante, dezenas sorteadas, mínimo e máximo permitidos, custo em R$) e chips interativos de seleção rápida.
- **Entrada Amigável:** Parser inteligente que aceita números separados por espaços, quebras de linha ou vírgulas (ex: `06 11 25 45 48 58`), eliminando a exibição de colchetes e arrays JSON na interface.

---

### [v1.1.0] - 2026-09-08 — Painel Administrativo, Usuários & Atualizador Caixa
#### 🚀 Novas Funcionalidades
- **Painel Administrativo (`/admin`):**
  - Autenticação e tela de login (`/login`).
  - Criação de usuário administrador padrão (`silvio.luis.morais@gmail.com`).
  - Gestão completa de usuários (criação, listagem, bloqueio/desbloqueio, exclusão e alteração de senha).
- **Módulo Atualizador Caixa (`updater.py`):**
  - Comunicação direta com a API da Caixa Econômica Federal para as 9 modalidades de loteria.
  - Armazenamento em arquivos JSON locais com metadados de último concurso e data de apuração.
  - Registro de logs de sincronização na tabela `sync_logs` do SQLite.
- **Otimização para Vercel Serverless:**
  - Remoção de dependências pesadas de compilação C/C++ (`numpy`), mantendo o cálculo matemático puro em Python nativo.
  - Armazenamento tolerante em `/tmp/data` no ambiente de nuvem.

---

### [v1.0.0] - 2026-09-08 — Lançamento Inicial do Modelo Canônico 3.0 + MCP-MD 1.0
#### 🚀 Funcionalidades Iniciais
- **Motor Estatístico Canônico 3.0 (MCSCE - 7 Camadas):**
  - Camada 1: Convergência (LLN, Fator de Recorrência FR).
  - Camada 2: Estabilidade (Índice de Convergência Temporal ICT e Classes A, B, C, D).
  - Camada 3: Saturação (ISEG, IIE, FCT).
  - Camada 4: Dinâmica (ILLA, ILLA Dinâmico, Aceleração Entrópica AE).
  - Camada 5: Informacional (Entropia de Shannon, Complexidade, Compressibilidade Lempel-Ziv).
  - Camada 6: Não Linear (Dimensão Fractal, Caos).
  - Camada 7: Validação (Monte Carlo, Inferência Bayesiana e Backtest).
- **Extensão MCP-MD 1.0:**
  - Janelas aninhadas de microdinâmica (W1=100, W2=150, T=Total).
  - Gradientes Δ1, Δ2, Índice de Microcompressão (IMC) e Score MCP.
- **Suporte às 9 Loterias Oficiais do Brasil:**
  - Mega-Sena, Quina, Lotofácil, Lotomania, +Milionária, Dia de Sorte, Super Sete, Timemania, Dupla Sena.
