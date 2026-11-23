# Framework de Aprendizado e Comparação de Modelos 1.0

**Status:** framework de pesquisa; baselines iniciais da Mega-Sena implementados; não habilitado no gerador de jogos  
**Escopo:** Calculadora da Sorte — Modelo Canônico 4.0 e módulos especializados  
**Relação com documentos existentes:** complementa `APRENDIZADO_NEURAL_1_0.md`; não o substitui  
**Princípio:** comparar métodos de aprendizado sob o mesmo protocolo, sem presumir que complexidade computacional represente capacidade preditiva.

---

## 1. Objetivo

Estabelecer uma estrutura controlada para estudar diferentes famílias de Machine Learning e verificar se alguma delas extrai informação preditiva reproduzível dos históricos das loterias.

O framework não parte da hipótese de que existam padrões exploráveis. A hipótese de pesquisa é condicional: **se houver sinal estatístico estável além do esperado pelo mecanismo aleatório, um método poderá identificá-lo fora da amostra**. A ausência de ganho é um resultado válido.

A camada é subordinada ao Modelo Canônico 4.0. Não altera topologias, métricas, fórmulas, setores, variantes, módulos específicos ou a lógica atual do gerador.

## 2. Correção conceitual: não é uma escada histórica linear

Os nove métodos abaixo são uma sequência didática útil para comparar diferentes formas de aprender, mas não constituem uma evolução histórica obrigatória em que cada algoritmo deriva diretamente do anterior.

Eles pertencem a famílias distintas:

- modelos lineares e probabilísticos;
- modelos baseados em regras e árvores;
- ensembles;
- métodos baseados em distância;
- aprendizado não supervisionado;
- redes neurais profundas;
- modelos de linguagem.

A escolha deve decorrer da pergunta estatística, do formato dos dados e do protocolo de validação — não da posição do algoritmo em uma lista.

## 3. Mapa dos nove métodos

### 3.1 Regressão Linear

\[
\hat{y}=w^T x+b
\]

Estima uma variável numérica contínua por uma combinação linear das entradas.

**Uso experimental:** baseline numérico para estudar relações entre atributos históricos e alvos numéricos definidos de forma legítima.

**Limite:** não representa, por si só, relações não lineares. Não deve ser usada para inventar uma variável-alvo contínua sem justificativa estatística.

### 3.2 Regressão Logística

\[
p(y=1\mid x)=\sigma(w^T x+b)
\]

Transforma uma combinação linear em uma probabilidade de classe.

**Uso experimental:** estimar, para cada elemento do universo de uma modalidade, uma probabilidade marginal de ocorrência no próximo concurso, usando somente informações anteriores ao sorteio.

**Limite:** a fronteira é linear nas variáveis fornecidas; a calibração e a comparação com a probabilidade teórica são obrigatórias. Uma probabilidade estimada não altera a probabilidade matemática do mecanismo do sorteio.

### 3.3 Árvore de Decisão

\[
G=1-\sum_k p_k^2
\]

Divide os dados por regras sucessivas. O índice de Gini é uma das medidas possíveis de impureza em tarefas de classificação.

**Uso experimental:** investigar interações e regras condicionais entre variáveis históricas previamente documentadas.

**Limite:** árvores isoladas podem ser instáveis e sobreajustar. Profundidade, tamanho mínimo de folha e poda devem ser definidos na validação cronológica.

### 3.4 Random Forest

\[
\hat{y}=\operatorname{mode}(h_1(x),\ldots,h_B(x))
\]

Em classificação, combina árvores por votação; em regressão, normalmente combina por média. As árvores são treinadas com aleatoriedade em amostras e/ou subconjuntos de atributos.

**Uso experimental:** comparar se um conjunto de árvores oferece generalização melhor do que uma árvore isolada e do que os baselines.

**Limite:** votação não equivale automaticamente a probabilidade calibrada. Probabilidades e escores precisam de avaliação própria.

### 3.5 Gradient Boosting

\[
F_m(x)=F_{m-1}(x)+\eta h_m(x)
\]

Constrói modelos sequencialmente, ajustando novos componentes para reduzir a função de perda por meio de gradientes.

**Uso experimental:** testar relações não lineares e interações entre atributos históricos.

**Limite:** sensível a hiperparâmetros e risco de sobreajuste. Toda seleção de hiperparâmetros deve ocorrer exclusivamente na validação cronológica.

### 3.6 k-Nearest Neighbors (KNN)

\[
\hat{y}=\operatorname{mode}\{y_i:i\in N_k(x)\}
\]

Classifica uma observação pela resposta dos vizinhos mais próximos; em regressão, pode usar a média ou uma média ponderada.

**Uso experimental:** procurar concursos ou janelas historicamente semelhantes, desde que a representação e a métrica de distância sejam definidas antes da avaliação.

**Limite:** depende fortemente de escala, representação, métrica e escolha de k. Similaridade geométrica não demonstra dependência estatística nem poder de previsão.

### 3.7 K-Means

\[
\min_{C_1,\ldots,C_K}\sum_{j=1}^{K}\sum_{x_i\in C_j}\|x_i-\mu_j\|^2
\]

Agrupa observações sem rótulos, atribuindo cada ponto ao centroide mais próximo e recalculando os centroides iterativamente.

**Uso experimental:** exploração de agrupamentos de concursos por atributos matemáticos e estatísticos.

**Limite:** agrupamentos não são previsões. A existência de clusters não implica que o próximo sorteio pertença a um grupo previsível. Número de grupos, inicialização e estabilidade devem ser documentados.

### 3.8 Redes Neurais

\[
a^{(l)}=\phi(W^{(l)}a^{(l-1)}+b^{(l)})
\]

Empilham transformações lineares e funções de ativação não lineares. Os parâmetros são ajustados por otimização, com gradientes e retropropagação.

**Uso experimental:** aprender representações e relações não lineares entre atributos históricos e alvos multi-hot definidos por modalidade.

**Limite:** maior capacidade não garante melhor generalização. Exige controle de vazamento temporal, regularização, comparação com métodos simples, reprodutibilidade e avaliação fora da amostra.

A implementação neural segue a especificação separada `APRENDIZADO_NEURAL_1_0.md`, inclusive seu ciclo de sete etapas e seus baselines obrigatórios.

### 3.9 Grandes Modelos de Linguagem (LLMs)

\[
P(t_{n+1}\mid t_1,\ldots,t_n)=\operatorname{softmax}(Wh)
\]

LLMs são redes neurais de grande escala, em geral baseadas em Transformers, treinadas para modelar sequências de tokens. Atenção, representações contextuais, dados e escala são partes importantes da arquitetura; não se resumem a uma reta e uma sigmoide.

**Uso previsto no projeto:** apoio à documentação, explicação de resultados, consulta metodológica, geração de relatórios e interface em linguagem natural, sempre com dados e cálculos produzidos por componentes verificáveis.

**Não usar como preditor de sorteios por padrão:** capacidade de gerar texto coerente não demonstra capacidade de prever eventos aleatórios. Uma eventual experiência numérica exigiria protocolo próprio e comparação com baselines, sem substituir os modelos estatísticos.

## 4. Unidade de previsão e separação por modalidade

Cada modalidade deve possuir adaptador, universo, alvo, baseline e avaliação próprios. Não misturar diretamente dezenas, trevos, meses, colunas ou sorteios distintos.

Para sorteios simples de k elementos em um universo de N, a referência marginal uniforme de cada elemento é:

\[
p_0=\frac{k}{N}
\]

Essa referência deve ser adaptada às regras reais de cada modalidade. Em estruturas especiais, usar saídas separadas conforme a especificação neural:

- Dupla Sena: uma saída para cada sorteio;
- +Milionária: dezenas e trevos separados;
- Dia de Sorte: dias e mês separados;
- Super Sete: uma saída por coluna;
- demais modalidades: respeitar universo, quantidade sorteada e regras próprias.

O alvo supervisionado deve refletir o resultado real do concurso previsto. Cada vetor de entrada deve ser construído exclusivamente com dados disponíveis antes desse concurso.

## 5. Protocolo comum de comparação

Todos os métodos supervisionados devem receber a mesma divisão temporal, a mesma definição de alvo e o mesmo conjunto de informações disponíveis em cada origem de previsão.

1. **Auditoria dos dados:** integridade, duplicidades, concursos ausentes, regras e datas.
2. **Construção temporal:** para cada concurso-alvo t, calcular atributos apenas com concursos anteriores a t.
3. **Walk-forward:** treinar no passado, prever o bloco seguinte e avançar no tempo.
4. **Transformações:** ajustar normalização, seleção de atributos e demais transformações apenas no treino de cada janela.
5. **Validação:** escolher hiperparâmetros sem consultar o bloco final de teste.
6. **Teste final:** manter período cronológico intocado até a definição do modelo e dos critérios.
7. **Reprodutibilidade:** registrar semente, versão do código, hash dos dados, hiperparâmetros e previsões anteriores ao resultado.
8. **Relatório:** divulgar quantidade de concursos, períodos, blocos, experimentos e limitações.

Não embaralhar concursos entre treino e teste. Não calcular atributos de uma previsão com informações do próprio concurso previsto ou de concursos futuros.

## 6. Baselines e métricas

A comparação mínima deve incluir:

- baseline uniforme teórico, respeitando o mecanismo da modalidade;
- frequência histórica simples, calculada somente com o passado disponível;
- Modelo Canônico atual, sem camada experimental;
- métodos de Machine Learning habilitados para aquele experimento.

Registrar, conforme aplicável:

- Brier score/MSE e log loss;
- calibração das probabilidades;
- distribuição de acertos por concurso, não apenas a média;
- comparação com a expectativa matemática;
- intervalos de confiança e testes adequados;
- estabilidade entre blocos temporais;
- testes de permutação/Monte Carlo;
- número de modelos, hiperparâmetros e tentativas, com controle de múltiplas comparações.

Métricas de classificação, regressão, agrupamento e linguagem não são intercambiáveis. K-Means, por exemplo, deve ser avaliado como ferramenta exploratória, e não receber artificialmente uma métrica de previsão supervisionada.

## 7. Regras contra falsas descobertas

- Frequência histórica, atraso e agrupamento são descrições dos dados; não representam compensação futura.
- Não selecionar retrospectivamente apenas o período, métrica ou modelo que apresentou o melhor resultado.
- Não testar muitos modelos e divulgar somente o vencedor sem contabilizar as tentativas.
- Não usar o bloco final de teste para escolher variáveis, hiperparâmetros ou arquitetura.
- Não interpretar pequenas diferenças de acertos como evidência suficiente.
- Investigar vazamento, viés de seleção, alterações no mecanismo do sorteio e erros de implementação antes de atribuir qualquer ganho ao modelo.
- Não declarar que uma combinação individual teve sua probabilidade matemática alterada.

## 8. Regra de promoção operacional

Nenhum modelo experimental altera a geração canônica automaticamente.

Para ser considerado candidato à promoção, deverá demonstrar:

- ganho consistente contra o baseline uniforme e o Modelo Canônico, em avaliação adequada à modalidade;
- replicação em múltiplos blocos cronológicos independentes;
- calibração aceitável, quando produzir probabilidades;
- robustez a escolhas razoáveis de janela, inicialização e hiperparâmetros;
- significância e intervalos de confiança adequados;
- correção ou controle para múltiplas comparações;
- ausência de vazamento e reprodutibilidade independente.

Se os critérios não forem atendidos, registrar **“sem evidência de ganho preditivo”** ou **“resultado inconclusivo”**, conforme a quantidade e a qualidade dos dados.

Mesmo um ganho estatístico aparente não autoriza afirmar que as probabilidades matemáticas do sorteio foram modificadas.

## 9. Sequência recomendada de implementação

### Fase 0 — Documentação e auditoria
- Manter este framework e a especificação neural como documentos de referência.
- Auditar módulos, formatos de histórico, regras e testes existentes.
- Definir uma modalidade-piloto e congelar a definição dos alvos e métricas.

### Fase 1 — Baselines reproduzíveis
- Implementar ou confirmar baselines uniforme e de frequência histórica.
- Criar pipeline walk-forward reutilizável.
- Gerar previsões registradas antes de cada concurso-alvo.

### Fase 2 — Modelos clássicos
- Avaliar regressão logística como baseline probabilístico.
- Avaliar árvore, Random Forest e Gradient Boosting.
- Avaliar KNN somente após especificar métrica e escala.
- Usar regressão linear apenas para alvos numéricos justificáveis.

### Fase 3 — Exploração não supervisionada
- Avaliar K-Means como diagnóstico exploratório.
- Verificar estabilidade dos agrupamentos e se acrescentam informação mensurável.
- Não converter clusters diretamente em previsões.

### Fase 4 — Rede neural
- Implementar a especificação `APRENDIZADO_NEURAL_1_0.md`.
- Testar dimensões, gradientes por diferenças finitas, vazamento e reprodutibilidade.
- Comparar com todos os baselines aplicáveis.

### Fase 5 — Relatório e decisão
- Publicar resultados completos, inclusive resultados negativos.
- Decidir por modalidade, sem transferência automática de conclusões entre loterias.
- Manter a camada experimental isolada até eventual aprovação formal.

### Fase transversal — LLM
- Usar LLM para documentação, interpretação e interface.
- Exigir que números, métricas e previsões venham de rotinas determinísticas ou modelos estatísticos rastreáveis.
- Não atribuir ao LLM autoridade para alterar o gerador.

## 10. Relação com a arquitetura atual

Este framework complementa a arquitetura registrada no README:

- as oito camadas do Modelo Canônico 4.0 e a dinâmica MCO-DYN permanecem intactas;
- MCP-MD 1.0 permanece intacto;
- os módulos especializados por modalidade permanecem responsáveis por suas estruturas;
- a Camada Neural Experimental 1.0 continua regida por sua especificação própria;
- este framework organiza os comparadores, protocolos, critérios e governança de experimentos.

**Estado após esta documentação:** conceito formalizado. Isso não significa que os algoritmos clássicos ou a rede neural já estejam implementados, treinados ou validados no código da aplicação.

## 11. Estado de implementação (22/11/2026)

Primeira entrega de código concluída para Mega-Sena:

- `ml_baselines.py`: baseline uniforme teórico e frequência histórica empírica;
- avaliação walk-forward com previsão do alvo antes de incorporar seu resultado;
- Brier score médio por concurso e comparação entre os dois baselines;
- validação da estrutura de cada concurso;
- `test_ml_baselines.py`: testes unitários;
- `scripts/avaliar_baselines_mega_sena.py`: runner local em JSON.

**Limitação atual dos dados versionados:** `data/mega_sena_historico.json` contém 53 concursos e `data/mega_sena_meta.json` também informa 53 registros, embora o metadado aponte último concurso 3069. Com a configuração padrão de 150 concursos iniciais, a avaliação walk-forward ainda não pode ser executada sobre esse arquivo. É necessário disponibilizar um histórico íntegro com mais de 150 concursos, em ordem cronológica, antes de produzir métricas retrospectivas.

Os testes foram adicionados ao repositório, mas ainda não foram executados em um ambiente de CI ou local nesta etapa. Não há alegação de desempenho superior, treinamento ou validação estatística concluída.

## 12. Primeira avaliação executada com histórico até o concurso 3088 (23/11/2026)

### Auditoria da planilha recebida

A planilha enviada contém 3.088 linhas de concursos, do concurso 1 (11/03/1996) ao 3088 (19/11/2026), em ordem decrescente no arquivo original. Para a avaliação, os registros foram ordenados cronologicamente.

Verificações realizadas:

- 3.088 concursos;
- nenhum número de concurso duplicado;
- nenhum concurso ausente no intervalo 1–3088;
- seis dezenas em cada concurso;
- dezenas dentro do intervalo 1–60;
- nenhuma dezena repetida dentro do mesmo concurso;
- datas válidas.

### Walk-forward dos dois baselines

Configuração: primeiros 150 concursos usados como histórico inicial; previsão sequencial dos 2.938 concursos seguintes. Em cada etapa, a frequência histórica foi recalculada apenas com concursos anteriores ao alvo. O Brier foi calculado como a média dos erros quadráticos dos 60 indicadores marginais por concurso.

| Métrica | Baseline uniforme | Frequência histórica |
|---|---:|---:|
| Brier médio | 0,09000000 | 0,09006868 |
| Média de acertos da seleção top-6 | 0,600 esperado ao acaso | 0,60245 observado |

A diferença de Brier (uniforme menos frequência) foi -0,00006868; portanto, nesta avaliação, o baseline uniforme teve Brier ligeiramente menor. A média de acertos da seleção top-6 por frequência foi 0,60245, praticamente igual à expectativa de 0,6 para uma seleção fixa de seis dezenas em sorteio 6/60.

**Conclusão:** não há evidência de vantagem preditiva da frequência histórica sobre o baseline uniforme neste teste. A pequena diferença observada não deve ser interpretada como capacidade de previsão. O resultado é descritivo, restrito ao período e ao protocolo informados; análises adicionais devem considerar dependência temporal, incerteza estatística e replicação em períodos independentes.

### Limitação de persistência

A planilha foi auditada e usada nesta avaliação, mas não foi incorporada como arquivo de dados ao repositório nesta alteração. O arquivo versionado `data/mega_sena_historico.json` ainda contém 53 concursos. Portanto, o executor local padrão continuará limitado até que a base completa seja persistida ou indicada por caminho local. Não declarar a base do repositório atualizada com 3.088 concursos.


## 13. Regressão Logística experimental — Mega-Sena (23/11/2026)

Foi adicionada a primeira implementação supervisionada do framework:

- `regressao_logistica_mega_sena.py`: classificador binário compartilhado para as 60 dezenas, com probabilidade marginal por dezena;
- atributos temporais: frequências nas janelas 30, 60, 100 e 150, frequência acumulada, distância desde a última ocorrência e identidade one-hot da dezena;
- pipeline `StandardScaler + LogisticRegression`: padronização e ajuste refeitos apenas com dados de treino disponíveis;
- avaliação walk-forward com treino inicial e retreinamento em blocos de 25 alvos por padrão;
- Brier score comparado ao baseline uniforme no mesmo período, além da média de acertos do top-6 como métrica descritiva;
- executor: `scripts/avaliar_regressao_logistica_mega_sena.py`;
- testes: `test_regressao_logistica_mega_sena.py`.

O primeiro alvo de teste ocorre após 150 concursos para formação das variáveis e mais 150 origens rotuladas para o treino inicial (índice zero-based 300). Entre retreinamentos, o modelo permanece congelado; as previsões continuam sem vazamento, mas não incorporam os resultados intermediários até o ajuste seguinte.

Dependências adicionadas: NumPy e scikit-learn. Os testes e a avaliação integral ainda precisam ser executados em ambiente Python. O histórico completo de 3.088 concursos ainda não está persistido no repositório; o JSON versionado continua com 53 registros. Portanto, não há resultado de desempenho da regressão logística declarado nesta entrega.
