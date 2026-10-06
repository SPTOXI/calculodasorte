# Loteria Canônica - Sistema de Análise Estatística

## Modelo Canônico 4.0 (MCOD / MCOM / MCOH / MCOP) + MCP-MD 1.0
### AGENTE LLN ICT FR & OTIMIZAÇÃO ESPACIAL POLIMÓRFICA

Sistema web completo para análise estatística de loterias brasileiras baseado no **Modelo Canônico 4.0** especializado por topologia lotérica (MCOD para Timemania, MCOM para Lotofácil, MCOH para Mega-Sena, MCOP para Quina) e sua extensão **MCP-MD 1.0**.

---

## 📊 Loterias Suportadas

- **Mega-Sena** (60 números, 6 sorteados — Modelo Hexagonal MCOH 4.0)
- **Quina** (80 números, 5 sorteados — Modelo Pentagonal MCOP 4.0)
- **Lotofácil** (25 números, 15 sorteados — Modelo Matricial 5x5 MCOM 4.0)
- **Timemania** (80 números, 7 sorteados, 10 na aposta + Time do Coração — Modelo Decagonal MCOD 4.0)
- **Lotomania** (100 números de 00 a 99, 20 sorteados, 50 na aposta simples — Modelo Centesimal MCOC 4.0)
- **+Milionária** (50 números + 6 trevos — Modelo Biparamétrico Hexa-Trevo MCOMIL 4.0)
- **Dia de Sorte** (31 números + Mês da Sorte — Modelo Heptagonal Calendário MCODS 4.0)
- **Super Sete** (7 colunas de 0-9)
- **Dupla Sena** (50 números, 2 sorteios)

---

## 🔧 Instalação

```bash
# Instalar dependências
pip install flask

# Executar aplicação
python app.py
```

A aplicação estará disponível em: `http://localhost:5000`

---

## 📐 Arquitetura do Sistema

### Núcleo Matemático (`core.py`, `modelo_dia_de_sorte.py`, `modelo_mais_milionaria.py`, `modelo_lotomania.py`, `modelo_decagonal_timemania.py`, `modelo_lotofacil.py`, `modelo_pentagonal.py`, `modelo_hexagonal.py`)

#### Modelo Canônico 4.0 - 8 Camadas:

1. **Convergência** - LLN, FR (Fator de Recorrência)
2. **Estabilidade** - ICT (Índice de Convergência Temporal)
3. **Saturação** - ISEG, IIE, FCT
4. **Dinâmica** - ILLA, ILLA Dinâmico, AE
5. **Informacional** - Entropia, Complexidade, Compressibilidade
6. **Não Linear** - Fractal, Multifractal, Caos
7. **Validação** - Monte Carlo, Bayesiano, Backtest
8. **Dispersão e Cobertura Espacial Especializada** - MCODS (Heptagonal Calendário - Dia de Sorte), MCOMIL (Biparamétrico Hexa-Trevo - +Milionária), MCOC (Centesimal 10x10 - Lotomania), MCOD (Decagonal - Timemania), MCOM (Matricial 5x5 e Quintetos - Lotofácil), MCOH (Hexagonal - Mega-Sena), MCOP (Pentagonal - Quina), K-Medians no grid/anel cíclico modular $\mathbb{Z}_N$, Índice de Dispersão Espacial (IDE 4.0).

#### MCP-MD 1.0 - Microdinâmica Condicionada:

- Janelas temporais aninhadas (W1=100, W2=150, T=total)
- Gradientes: Δ1 = f_i(W1) - f_i(W2), Δ2 = f_i(W1) - f_i(T)
- IMC (Índice de Microcompressão): IMC_i = Δ1 + Δ2
- Fator adaptativo: γ = (σ_W1 / σ_hist)²
- Score MCP: Score_i = ILLA_i + γ · IMC_i(norm)

---

## 🎯 Funcionalidades

### Página Inicial
- Seleção de loteria
- Informações detalhadas de cada loteria
- Configurações completas (universo, apostas, custos, dias)

### Importar Dados
- Carregar histórico de concursos em JSON
- Salvar histórico localmente
- Gerador de dados de exemplo para testes

### Análise Completa
- Estatísticas gerais (ICT médio, entropia, compressibilidade)
- Distribuição por classes (A, B, C, D)
- Classificação de maturidade estatística
- Análise individual de cada número

### Tabela de Números
- Contagem histórica
- Frequência observada
- FR (Fator de Recorrência)
- HI (Desvio de Harmonia)
- ICT (Índice de Convergência Temporal)
- Classe (A-D)
- Maturidade
- Score MCP

### Validação (Camada 7)
- Teste de Monte Carlo (10.000 simulações)
- Análise Bayesiana (Chi-quadrado, Bayes Factor)
- Backtest com janela de teste
- Conclusão sobre validade do MCP-MD

### Gerador de Jogos
- Sugestões baseadas na análise estatística
- Estratégia balanceada:
  - 40% melhores scores MCP
  - 30% menores ICT (mais estáveis)
  - 20% FR próximo de 1 (equilibrados)
  - 10% aleatórios (diversificação)

---

## 📁 Estrutura de Arquivos

```
/workspace
├── core.py                 # Núcleo matemático do Modelo Canônico
├── app.py                  # Aplicação Flask (API + Rotas)
├── templates/
│   ├── index.html          # Página inicial
│   └── analise.html        # Página de análise completa
├── static/                 # Arquivos estáticos (CSS, JS)
├── data/                   # Histórico salvo (JSON)
└── README.md               # Este arquivo
```

---

## ⚠️ Aviso Importante

> Este sistema **não promete resultados**, **vantagem** ou **padrão**.  
> Promete **rigor científico** e **teste estatístico**.  
> 
> A ausência de padrão detectável é um resultado científico válido.

O modelo segue os princípios do **AGENTE LLN ICT FR**:
- Não altera probabilidades do sistema
- Em sistemas equiprováveis, análise não cria vantagem
- Verifica se padrões existem (não assume existência)

---

## 🧪 Exemplo de Uso via API

```python
import requests

# Realizar análise
historico = [[1, 5, 10, 23, 35, 42], [3, 12, 18, 29, 41, 55], ...]
response = requests.post('http://localhost:5000/api/analise/mega_sena',
                        json={'historico': historico})
analise = response.json()

# Gerar jogo
response = requests.post('http://localhost:5000/gerar-jogo/mega_sena',
                        json={'historico': historico, 'quantidade': 6})
jogo = response.json()['jogo']
```

---

## 📊 Fórmulas Principais

### Fundamentos
- **μ = k / N** - Frequência teórica
- **f_i(T) = c_i / T** - Frequência observada
- **FR_i = f_i(T) / μ** - Fator de Recorrência
- **H_i = |FR_i - 1|** - Desvio de Harmonia

### MCP-MD
- **Δ1 = f_i(W1) - f_i(W2)** - Gradiente curto/médio
- **Δ2 = f_i(W1) - f_i(T)** - Gradiente curto/total
- **IMC_i = Δ1 + Δ2** - Índice de Microcompressão
- **γ = (σ_W1 / σ_hist)²** - Fator adaptativo
- **Score_i = ILLA_i + γ · IMC_i(norm)** - Score final

### Classificação ICT
- **Classe A**: até o primeiro quartil do ICT (estabilidade relativa maior)
- **Classe B**: entre o primeiro e o segundo quartil
- **Classe C**: entre o segundo e o terceiro quartil
- **Classe D**: acima do terceiro quartil (estabilidade relativa menor)

Os quartis são recalculados para cada histórico. As classes são descritores relativos e não representam frequência, atraso ou probabilidade de acerto. A fórmula operacional do ICT e as aproximações usadas nos componentes sem fórmula documental estão expostas na resposta da API e na página de metodologia.

---

## 🔬 Validação Científica

O MCP-MD só fica disponível com pelo menos 150 concursos, necessários para completar as janelas formais de 100 e 150. Sua validação usa blocos cronológicos fora da amostra e somente é considerada atendida quando satisfaz **simultaneamente**:

1. Z acumulado > 2
2. Bayes Factor > 10
3. Percentil Monte Carlo < 1%
4. Persistência em múltiplos blocos independentes
5. Robustez em walk-forward progressivo

Com dados insuficientes, o resultado é **inconclusivo**. Quando os critérios não são atendidos, a microestrutura fica **não validada nesse recorte**; isso não prova ruído puro nem vantagem futura. As escolhas operacionais do walk-forward e do prior bayesiano são apresentadas junto ao resultado.

---

## 📝 Licença

Sistema desenvolvido para fins educacionais e de pesquisa estatística.

---

## 👥 AGENTE LLN ICT FR

**Lei dos Grandes Números | Índice de Convergência Temporal | Fator de Recorrência | Otimização Hexagonal**

*Modelo Canônico 4.0 — MCSCE / MCOH*  
*Arquitetura de Convergência, Saturação, Complexidade Estatística e Dispersão Espacial*
