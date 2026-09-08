# 📜 Registro Oficial de Alterações (CHANGELOG)
## Projeto Calculadora da Sorte — Modelo Canônico 3.0 + MCP-MD 1.0

Todas as alterações, adições de recursos, correções e versões deste software são registradas de forma contínua neste documento e versionadas no repositório GitHub oficial: [`https://github.com/SPTOXI/calculodasorte.git`](https://github.com/SPTOXI/calculodasorte.git).

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
  - Integração via REST de alto desempenho com **Google Gemini 1.5 Flash** (chave `GEMINI_API_KEY` ou `GOOGLE_API_KEY`) e **Anthropic Claude 3.5 Haiku** (`ANTHROPIC_API_KEY`), compatível com Vercel (sem dependências pesadas de C++).
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
