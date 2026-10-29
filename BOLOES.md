# 🎟️ Módulo de Bolões — Documentação e Pendências

Camada de gestão de bolões construída sobre o motor de fechamentos do Cálculo da Sorte.
O sistema opera como **plataforma de tecnologia e prestação de contas**. A guarda (custódia) do
bilhete físico registrado na lotérica é do **organizador**.

> Histórico de versões: veja `CHANGELOG.md` (v5.0.0). Este arquivo descreve como o módulo
> funciona hoje e registra **tudo o que ainda está pendente**.

---

## 1. Visão geral do fluxo

```
Admin define taxa e regras ─► Organizador gera um fechamento e o salva
        │                                   │
        │                                   ▼
        │                     /organizador: cria o bolão (cotas + título)
        │                                   │  preço calculado no servidor
        ▼                                   ▼
  Aba Admin › Bolões  ◄────────  Vitrine /boloes ─► Apostador compra a cota (Pix InfinitePay)
                                            │          aceite obrigatório + reserva de N minutos
                                            ▼
                         Webhook confirma ─► cota "paga" + bilhete /bilhete/<hash>
                                            │
                    Organizador envia comprovante (foto/PDF) ─► bolão "registrado"
                                            │
              Rotina diária 23h (cron) ─► alerta de prazo · cancelamento + reembolso · conferência
                                            │
                     Admin informa prêmio líquido ─► rateio por cota publicado no bolão
```

## 2. Regra de preço

```
Valor da cota = (Custo oficial dos jogos na Caixa + Taxa de serviço) ÷ Total de cotas
```

- **Custo oficial**: `comb(dezenas_do_jogo, mínimo_da_loteria) × preço_da_aposta_simples`. Esses
  valores estão em `core.py › LOTERIAS_CONFIG`.
- **Taxa de serviço**: definida **somente pelo admin**. Pode ser percentual sobre o custo ou um valor
  fixo por bolão.
- A cota é arredondada **para cima** em centavos, para a soma das cotas nunca ficar abaixo do custo.
  A sobra do arredondamento aparece no simulador.
- O preço é **sempre recalculado no servidor**. Valores enviados pelo navegador são ignorados.

Exemplo: Lotofácil, 10 jogos de 16 números, taxa de 20% e 12 cotas.
O custo é R$ 560,00, a taxa R$ 112,00, o total R$ 672,00 e a cota **R$ 56,00**.

## 3. Ciclo de vida

| Status do bolão | Significado | Quem muda |
|---|---|---|
| `aberto` | Vendendo cotas | Criação pelo organizador |
| `fechado` | Vendas encerradas, aguardando comprovante | Organizador ("Encerrar vendas") ou admin |
| `registrado` | Comprovante enviado; vendas encerradas | Envio do comprovante |
| `premiado` / `nao_premiado` | Resultado conferido | Rotina diária |
| `cancelado` | Sem comprovante no prazo ou cancelado pelo admin | Rotina diária ou admin |

| Status da cota | Significado |
|---|---|
| `disponivel` | À venda |
| `reservada` | No checkout; volta a `disponivel` quando a reserva vence |
| `paga` | Pagamento confirmado; tem `hash_bilhete` |
| `estornada` | Bolão cancelado; o pagamento vai para reembolso |

| Status do pagamento (`tipo = cota_bolao`) | Significado |
|---|---|
| `pendente` → `aprovado` | Fluxo normal |
| `reembolso_pendente` | Bolão cancelado, ou pagamento confirmado sem cota disponível |
| `reembolsado` | Admin marcou a devolução como feita |

## 4. Perfis e telas

| Quem | Onde | O que faz |
|---|---|---|
| Admin | `/admin` › aba **Bolões** | Taxa, regras e liga/desliga do módulo; simulador; lista com arrecadação, prazo, comprovante e status; "Rodar rotina agora"; "Informar prêmio"; fila de **Reembolsos Pendentes** |
| Admin | `/admin` › aba **Usuários** | Atribui o perfil **Organizador de Bolões** |
| Organizador | `/organizador` | Cria bolão a partir de um jogo salvo; encerra vendas; envia ou troca o comprovante |
| Público | `/boloes`, `/boloes/<id>` | Vitrine, jogos, prestação de contas, comprovante e resultado |
| Apostador | `/boloes/<id>` | Compra a cota (aceite obrigatório) |
| Apostador | `/minhas-cotas`, `/bilhete/<hash>` | Cotas e bilhete digital |

Com o módulo **desligado**, só o admin vê a vitrine e cria bolões (modo de teste).

## 5. Rotas

| Método | Rota | Acesso |
|---|---|---|
| GET/POST | `/api/admin/boloes/config` | admin |
| POST | `/api/admin/boloes/simular` | admin |
| GET | `/api/admin/boloes` | admin |
| POST | `/api/admin/boloes/<id>/status` | admin (`cancelado` gera reembolsos) |
| POST | `/api/admin/boloes/rotina` | admin |
| POST | `/api/admin/boloes/<id>/premio` | admin |
| POST | `/api/admin/reembolsos/<payment_id>/concluir` | admin |
| POST | `/api/boloes/preview`, `/api/boloes` | organizador/admin |
| POST | `/api/boloes/<id>/fechar` | dono do bolão |
| POST | `/api/boloes/<id>/comprovante` | dono do bolão ou admin |
| POST | `/api/boloes/<id>/comprar` | usuário logado |
| GET | `/api/boloes`, `/boloes`, `/boloes/<id>`, `/boloes/<id>/comprovante`, `/bilhete/<hash>` | público (vitrine só com o módulo ativo) |
| GET | `/minhas-cotas`, `/organizador` | logado |
| GET/POST | `/api/cron/atualizar` | cron (agora também roda `boloes_rotina.executar()`) |

## 6. Banco de dados

As tabelas e colunas novas são criadas automaticamente por `database.init_db()`, com
`CREATE TABLE IF NOT EXISTS` e `ADD COLUMN IF NOT EXISTS`, sem precisar de migração manual.

- `boloes`: dados do bolão, preços congelados na criação, `prazo_comprovante` e `data_sorteio`
  (em UTC), comprovante, `resultado_json`, `valor_premio`, `premio_por_cota` e `cancelado_motivo`.
- `bolao_jogos`: jogos (`dezenas_json`, `custo`, `complemento`).
- `bolao_cotas`: uma linha por cota (`numero`, `status`, `user_id`, `payment_id`, `reservada_ate`,
  `aceite_termos_at`, `hash_bilhete`, `pago_em`).
- `bolao_comprovantes`: arquivo do comprovante (`BYTEA`, até 4 MB), tipo e quem enviou.
- `payments.bolao_id`: liga o pagamento ao bolão.
- `system_settings['bolao_config']`: configuração definida pelo admin.

## 7. Segurança e integridade

- **Venda dupla**: a reserva usa `FOR UPDATE SKIP LOCKED`, e há teste com compras simultâneas.
- **Pagamento**: o webhook só aprova depois de consultar a própria InfinitePay
  (`payment_check`), que precisa confirmar que foi pago o valor certo.
- **Bilhete**: o `hash_bilhete` é um SHA-256 de bolão, cota, usuário, impressão dos jogos e um valor
  aleatório. A **impressão digital dos jogos** é um SHA-256 público dos jogos e prova que eles não
  mudaram depois da venda.
- **Comprovante**: o tipo é identificado pelos primeiros bytes do arquivo (JPG, PNG ou PDF). O limite
  é de 4 MB, por causa do teto de cerca de 4,5 MB por requisição na Vercel. O arquivo é servido com
  `Content-Security-Policy` restritiva. O SHA-256 do arquivo é exibido publicamente.
- **Prazos**: gravados em UTC. Os sorteios são às 20h de Brasília (23h UTC), e as telas mostram o
  horário de Brasília.

## 8. Configuração e variáveis de ambiente

| Variável | Uso no módulo |
|---|---|
| `DATABASE_URL` / `POSTGRES_URL` | Banco (Supabase) |
| `INFINITEPAY_HANDLE` | Conta da InfinitePay que recebe as cotas |
| `CRON_SECRET` | Protege `/api/cron/atualizar`, que roda a rotina dos bolões |
| `RESEND_API_KEY` ou `SMTP_*`, `EMAIL_FROM` | E-mails de alerta de prazo, cancelamento e prêmio. Sem eles, a rotina continua funcionando, mas não envia e-mails |
| `SITE_URL` | Links nos e-mails |

Configurações no painel (Admin › Bolões): tipo e valor da taxa, mínimo e máximo de cotas, horas antes
do sorteio para o comprovante, minutos de reserva e liga/desliga.

---

## 9. ✅ Pendências registradas

### 9.1 Obrigatórias antes de ativar o módulo para o público
- [ ] **Validação jurídica**: a venda online de cotas de bolão por quem não é lotérica credenciada
      tem restrições (Caixa/SPA-MF). Validar o modelo com um advogado antes de receber dinheiro de
      terceiros.
- [ ] **Rodapé do site**: já é condicional (v5.1.0). Com o módulo ativo, o texto passa a descrever a
      plataforma como tecnologia e prestação de contas. **Validar a nova redação com um advogado.**
- [ ] **Termos de Uso (seção 6)**: validar com um advogado o texto e a promessa de reembolso em caso
      de cancelamento.
- [ ] **Teste real de ponta a ponta** em produção com o módulo desligado: criar o bolão, comprar uma
      cota de valor baixo, confirmar o Pix na InfinitePay, conferir o bilhete, enviar o comprovante
      e rodar a rotina.
- [ ] **Configurar o envio de e-mail** (`RESEND_API_KEY` ou `SMTP_*`) para os alertas de prazo e os
      avisos de cancelamento.
- [ ] **Definir `CRON_SECRET`** na Vercel, para que ninguém dispare a rotina de fora.
- [ ] Atribuir o perfil **Organizador** aos usuários que vão criar bolões.

### 9.2 Operação manual hoje (pode ser automatizada depois)
- [ ] **Reembolsos**: o sistema monta a fila, mas a devolução do dinheiro é feita manualmente na
      InfinitePay (ou por Pix). Avaliar a API de estorno da InfinitePay.
- [ ] **Valor do prêmio**: a rotina confere os acertos e as faixas, mas o **valor líquido** (depois
      do IR retido pela Caixa) é informado pelo admin. O cálculo automático exige tratar
      desdobramentos (um jogo de 7 números na Mega vale várias apostas simples), o rateio oficial
      por faixa e a Dupla Sena (dois sorteios).
- [ ] **Repasse do prêmio aos cotistas**: o valor por cota é publicado, mas o pagamento a cada
      cotista é manual. Não há controle de "prêmio repassado" por cota.
- [ ] **Repasse ao organizador**: não há controle financeiro de quanto o organizador recebe (custo
      Caixa) e quanto fica com a plataforma (taxa).

### 9.3 Limitações conhecidas
- [ ] **Super Sete e +Milionária** não estão disponíveis para bolões. Os trevos da +Milionária mudam
      o preço, e o Super Sete usa colunas.
- [ ] **Data do sorteio**: só é conhecida para o **próximo** concurso (`dataProximoConcurso` da
      Caixa). Bolões para concursos mais distantes ficam com o prazo "a definir" até a rotina diária
      preenchê-lo. Sem prazo, não há cancelamento automático.
- [ ] **Horário do sorteio** fixo em 20h de Brasília. Sorteios especiais (por exemplo, a Mega da
      Virada) ou em outro horário exigem ajuste manual do status pelo admin.
- [ ] **Concursos especiais** e Teimosinha não são tratados.
- [ ] **Limites oficiais de bolão da Caixa** (valor mínimo por cota e número máximo de cotas por
      modalidade) não são validados automaticamente. Hoje valem só os limites de cotas definidos
      pelo admin.
- [ ] **Comprovante no banco**: é guardado como `BYTEA` no Postgres, o que é suficiente para o
      volume inicial. Com muitos bolões, migrar para Supabase Storage ou Vercel Blob.
- [ ] **Aceite dos termos**: grava data e hora, mas não o IP nem a versão dos termos aceitos.
- [ ] **Página de bilhete**: é pública para quem tem o link (mostra só o primeiro nome do titular).
      Não há QR Code no bilhete.
- [ ] **Navegação**: não há link para "Minhas cotas" no menu principal (só pela vitrine). O atalho
      "Meus Bolões" aparece apenas para admin e organizador. O anúncio da Hero leva à vitrine.
- [ ] **Menu da landing (já existia antes)**: em telas de cerca de 1280px, o menu do topo não cabe e o botão
      "⚡ Análise por R$ 1,00" fica parcialmente cortado. Por isso, não foi adicionado um link "Bolões"
      ao menu; ajustar o menu antes de incluí-lo.
- [ ] **Hero**: o anúncio só aparece com o módulo ativo. Pré-visualizar com `/?preview=boloes` (admin).
- [ ] **Rotina diária**: roda uma vez por dia (23h). O cancelamento por falta de comprovante pode
      acontecer até cerca de 24h depois do prazo, porque o sorteio já ocorreu nesse intervalo. Para
      maior precisão, aumentar a frequência do cron (por exemplo, de hora em hora) ou rodar pelo botão
      do admin.
- [ ] **Testes**: 7 testes antigos do projeto (modelos canônicos, IA e importação) já falhavam antes
      do módulo de bolões e continuam falhando. Não têm relação com este módulo.

## 10. Testes do módulo

```bash
DATABASE_URL=postgresql://... python -m pytest -q test_bolao.py test_bolao_etapa2.py test_bolao_etapa3.py test_bolao_etapa4.py
```

São 49 testes: precificação, permissões, criação, vitrine, compra, concorrência, webhook, bilhete,
comprovante, rotina (prazo, alerta, cancelamento e conferência), reembolsos e rateio.
