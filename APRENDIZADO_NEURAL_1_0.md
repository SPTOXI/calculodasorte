# Camada Neural Experimental 1.0 — Especificação de Integração à Calculadora da Sorte

**Status:** especificação técnica; não habilitada no gerador de jogos  
**Base:** Modelo Canônico 4.0 e módulos especializados por loteria  
**Objetivo:** testar se uma rede neural consegue extrair sinal preditivo fora da amostra, sem alterar as regras canônicas nem sugerir que padrões históricos mudam as probabilidades matemáticas do sorteio.

## 1. Princípio de integração

A camada neural é experimental e subordinada à validação estatística. Ela não substitui MCOH, MCOP, MCOM, MCODSen, MCOMIL, MCOD, MCOC, MCODS ou MCOSS, nem altera seus setores, topologias, métricas ou variantes canônicas.

Cada modalidade deve ser treinada e avaliada separadamente. Não se misturam universos, regras, sorteios, colunas, trevos ou variáveis de modalidades diferentes.

A camada neural começa em modo de pesquisa: seus resultados são relatórios e diagnósticos. O gerador canônico continua sendo a referência até que exista evidência robusta, replicável e fora da amostra de desempenho superior ao baseline matemático.

## 2. Unidade de aprendizado e prevenção de vazamento

Cada exemplo de treinamento representa um concurso previsto usando somente informações disponíveis antes daquele concurso.

- Entrada X(t): atributos calculados exclusivamente com concursos anteriores a t.
- Alvo Y(t): resultado efetivamente observado no concurso t, codificado como vetor multi-hot.
- Nunca usar dados do próprio concurso previsto para calcular atributos de entrada.
- Separar treino, validação e teste cronologicamente; nunca embaralhar concursos entre esses conjuntos.
- Usar walk-forward: treinar no passado, prever o bloco seguinte e avançar no tempo.
- Todas as transformações e normalizações são ajustadas apenas no conjunto de treino de cada janela.

## 3. Variáveis de entrada candidatas

As variáveis são calculadas por modalidade e por elemento compatível com sua estrutura:

- Frequências observadas em janelas históricas disponíveis (por exemplo, 25, 50, 100, 150 e histórico total, respeitando o tamanho da base).
- Diferença entre frequências de janelas, dispersão temporal e estabilidade.
- Intervalo desde a última ocorrência (atraso), tratado como descrição histórica, não como probabilidade de compensação.
- Métricas canônicas já documentadas e calculadas pelo módulo específico.
- Atributos topológicos próprios da modalidade, quando existirem e estiverem formalmente definidos.

A inclusão de uma variável exige definição, teste de integridade e comprovação de que não contém informação posterior ao concurso-alvo. Não se criam índices ou pesos sem documentação.

## 4. Saída da rede

Para modalidades de sorteio de dezenas, a saída é um vetor de N escores, um por elemento do universo, interpretados como estimativas condicionais experimentais de ocorrência no próximo sorteio.

Para modalidades especiais, a saída respeita a estrutura própria:
- Dupla Sena: duas saídas independentes, uma para cada sorteio; eventual análise de relação entre sorteios é uma avaliação adicional e não soma as frequências dos dois para gerar uma única previsão.
- +Milionária: dezenas e trevos são saídas distintas.
- Dia de Sorte: dias e mês são saídas distintas.
- Super Sete: saída por coluna, sem colapsar as sete colunas em um único universo.

A rede não deve ser forçada a produzir uma combinação como se seus escores fossem probabilidades comprovadas. Se houver etapa de seleção top-k, ela é apenas uma transformação operacional dos escores e precisa ser avaliada separadamente.

## 5. Ciclo de treinamento em sete etapas

### 5.1 Forward pass — previsão

\[
\hat{Y}=f(X;W)
\]

A rede recebe os atributos históricos e produz um escore para cada elemento da modalidade.

### 5.2 Erro

\[
E=\hat{Y}-Y
\]

Compara a saída prevista com o vetor multi-hot do resultado real.

### 5.3 Perda

Para manter correspondência com o ciclo didático definido para esta integração, a função inicial de referência é o erro quadrático médio:

\[
L=\frac{1}{N}\sum_{i=1}^{N}(\hat{y}_i-y_i)^2
\]

A função de perda, a normalização e a escala devem ser idênticas ao comparar modelos e baselines. Uma alternativa como entropia cruzada só poderá ser introduzida como experimento separado, com documentação e comparação justa.

### 5.4 Gradiente

\[
\nabla_W L=\left(\frac{\partial L}{\partial w_1},\ldots,\frac{\partial L}{\partial w_n}\right)
\]

Calcula a sensibilidade da perda a cada parâmetro treinável.

### 5.5 Backpropagation

Aplica a regra da cadeia da camada de saída até a camada de entrada, calculando os gradientes de cada conexão. A implementação deve ter testes numéricos de gradiente (diferenças finitas) para verificar as derivadas.

### 5.6 Atualização

\[
W\leftarrow W-\eta\nabla_W L
\]

A taxa de aprendizado e demais hiperparâmetros são selecionados exclusivamente na validação cronológica, nunca no bloco final de teste.

### 5.7 Nova previsão e repetição

A rede atualizada produz novas previsões. O ciclo se repete por épocas, com registro da perda de treino e validação, critério de parada e checkpoint do modelo.

## 6. Baselines obrigatórios

A rede neural não será avaliada isoladamente. Deve ser comparada, no mínimo, com:

1. Baseline uniforme teórico: probabilidade marginal de ocorrência igual a k/N para cada dezena de um sorteio simples, respeitando a modalidade.
2. Frequência histórica simples, calculada apenas com o passado disponível em cada janela.
3. Modelo canônico atual, sem a camada neural.

Nas modalidades com estrutura especial, os baselines devem respeitar o mecanismo de sorteio e a unidade correta de previsão.

## 7. Critérios de avaliação fora da amostra

Registrar por janela e no agregado:

- MSE/Brier score e log loss, quando aplicável e definido;
- calibração das probabilidades;
- acertos médios e distribuição completa de acertos por concurso;
- comparação com expectativa matemática e baseline uniforme;
- intervalos de confiança e testes de significância adequados;
- estabilidade entre blocos temporais;
- resultados de testes de permutação/Monte Carlo;
- efeito de múltiplas tentativas de modelos e hiperparâmetros.

O relatório deve informar quantidade de concursos, período, tamanho dos blocos, número de experimentos e critérios definidos antes da avaliação.

## 8. Regra de promoção

A camada neural permanece experimental e não influencia as combinações exibidas como canônicas enquanto não demonstrar, em dados cronológicos não usados no treinamento ou na escolha de hiperparâmetros:

- melhora consistente sobre o baseline uniforme e sobre o modelo canônico;
- repetição do resultado em múltiplos blocos independentes;
- calibração aceitável;
- robustez a mudanças razoáveis de janela e inicialização;
- evidência estatística corrigida para múltiplas comparações.

Se esses critérios não forem atendidos, a conclusão será “sem evidência de ganho preditivo”. Isso não será tratado como falha do treinamento: é um resultado válido para um processo aleatório.

Mesmo se um ganho aparente for observado, não se afirmará que a probabilidade matemática de uma combinação individual foi alterada. Será necessário investigar vazamento de dados, viés de seleção, mudanças no mecanismo do sorteio e replicação independente.

## 9. Requisitos de engenharia

- Implementação isolada em módulo próprio, sem alterar diretamente os módulos canônicos na primeira fase.
- Dependências explícitas e compatíveis com o ambiente do projeto.
- Semente aleatória controlável para reprodutibilidade.
- Testes unitários de dimensões, gradientes, vazamento temporal e integridade dos alvos.
- Registro de hiperparâmetros, versão do código, hash dos dados e métricas por execução.
- Sem treinamento automático em produção e sem alteração silenciosa de pesos.
- Nenhuma combinação gerada pela camada experimental deve substituir a saída canônica sem aprovação explícita e validação documentada.

## 10. Sequência de implementação

1. Auditar os módulos atuais e as representações dos históricos por modalidade.
2. Definir adaptadores de dados separados para cada modalidade, com tratamento especial explícito para sorteios múltiplos, trevos, mês e colunas.
3. Implementar o motor neural experimental e os testes de gradiente.
4. Implementar walk-forward e baselines.
5. Rodar avaliação retrospectiva sem usar o bloco de teste para ajustar o modelo.
6. Publicar relatório de resultados e limitações.
7. Somente então decidir se alguma saída experimental merece ser apresentada ao lado do modelo canônico.

**Regra central:** a camada neural aprende a partir dos dados, mas só recebe influência operacional se provar desempenho fora da amostra. O Modelo Canônico permanece intacto até essa comprovação.
