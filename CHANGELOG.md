# 📜 Registro Oficial de Alterações (CHANGELOG)
## Projeto Calculadora da Sorte — Modelo Canônico 3.0 + MCP-MD 1.0

Todas as alterações, adições de recursos, correções e versões deste software são registradas de forma contínua neste documento e versionadas no repositório GitHub oficial: [`https://github.com/SPTOXI/calculodasorte.git`](https://github.com/SPTOXI/calculodasorte.git).

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
