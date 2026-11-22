# Framework de Aprendizado e Comparação de Modelos 1.0

**Status:** conceito técnico aprovado para pesquisa; não habilitado no gerador de jogos  
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
