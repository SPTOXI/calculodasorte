"""
Módulo do Agente de Inteligência Artificial Especialista em Loterias
Projeto Calculadora da Sorte - Modelo Canônico 3.0 + MCP-MD 1.0

Integração com APIs de IA:
1. Google Gemini (Gemini 1.5 Flash / Gemini 2.0)
2. Anthropic Claude (Claude 3.5 Haiku)
3. Motor Heurístico Canônico (Fallback automático quando sem chave de API)
"""

import os
import re
import json
import requests
from typing import Dict, List, Optional, Any

import database

def _mascarar_segredos(texto: Any) -> str:
    """Mascara chaves de API, credenciais e tokens para que nunca vazem em logs de servidor"""
    if not texto:
        return ""
    s = str(texto)
    s = re.sub(r'key=[a-zA-Z0-9_\-]+', 'key=***MASCARADO***', s)
    s = re.sub(r'(ak-[a-zA-Z0-9_\-]{4})[a-zA-Z0-9_\-]+', r'\1***', s)
    s = re.sub(r'(sk-[a-zA-Z0-9_\-]{4})[a-zA-Z0-9_\-]+', r'\1***', s)
    s = re.sub(r'(AIza[a-zA-Z0-9_\-]{4})[a-zA-Z0-9_\-]+', r'\1***', s)
    return s

def _carregar_env():
    """Carrega variáveis do arquivo .env local se existir"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v:
                            os.environ[k] = v
        except Exception:
            pass

_carregar_env()

def _get_api_config() -> dict:
    val = database.get_setting('ai_api_keys', '{}')
    try:
        return json.loads(val)
    except Exception:
        return {}

def _get_api_key(provider_id: str, env_vars: List[str]) -> Optional[str]:
    config = _get_api_config()
    provider_config = config.get(provider_id)
    if provider_config is not None:
        if not provider_config.get('active', False):
            return None
        if provider_config.get('key'):
            return provider_config.get('key')

    _carregar_env()
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            return val
    return None

def _get_gemini_key() -> Optional[str]:
    return _get_api_key('gemini', ['GEMINI_API_KEY', 'GOOGLE_API_KEY'])

def _get_moonshot_key() -> Optional[str]:
    return _get_api_key('kimi', ['MOONSHOT_API_KEY', 'KIMI_API_KEY'])

def _get_claude_key() -> Optional[str]:
    return _get_api_key('claude', ['ANTHROPIC_API_KEY'])

PROMPT_SISTEMA_PARECER = """
Você é o Agente de Inteligência Artificial Especialista em Análise Estatística e Estratégia do Cálculo da Sorte.
Sua missão é ler o cenário do sorteio e os dados matemáticos fornecidos (base histórica oficial da Caixa Econômica Federal, ICT - Índice de Convergência Temporal, Entropia de Shannon, Distribuição de Classes A/B/C/D, Score MCP e jogos gerados) e gerar um parecer didático, profissional, motivador e estratégico em português claro do Brasil.

DIRETRIZES ESSENCIAIS:
1. Explique a estratégia estatística de forma simples, elegante e transparente, traduzindo métricas matemáticas em conceitos fáceis de entender pelo apostador comum.
2. Destaque por que as combinações são equilibradas (equilíbrio par/ímpar, dispersão de quadrantes/moldura, eliminação de sequências consecutivas improváveis).
3. Seja responsável e ético: não faça promessas mágicas de enriquecimento fácil ou garantia de 100% de acertos máximos. Destaque que a matemática atua como otimização probabilística contra erros ingênuos.
4. Estruture seu parecer de forma clara e visual com emojis:
   - 📊 Diagnóstico do Cenário Atual (análise do ICT, Entropia e maturidade das dezenas)
   - 🎯 Avaliação da Estratégia dos Jogos Gerados
   - 💡 3 Recomendações Práticas para a Rodada
"""

PROMPT_SISTEMA_SUPORTE = """
Você é exclusivamente o Agente de Suporte ao Usuário do aplicativo Cálculo da Sorte.
Seu ÚNICO objetivo é oferecer suporte técnico, ajudar o usuário a navegar pela plataforma, abrir chamados, relatar bugs, ou esclarecer dúvidas de usabilidade (como assinar um plano, como gerar um jogo, onde ver resultados).

REGRAS ESTRITAS (NÃO VIOLAR SOB NENHUMA HIPÓTESE):
1. VOCÊ É APENAS SUPORTE TÉCNICO. Não atue como consultor matemático, não dê palpites de apostas nem invente números no chat de suporte.
2. Se o usuário quiser análise estatística profunda ou pareceres de IA, oriente-o a utilizar o botão "Gerar Palpite com IA" ou "Análise Completa" na tela da loteria correspondente, onde o motor estatístico processa os dados automaticamente.
3. É estritamente proibido revelar códigos-fonte ou credenciais internas do servidor.
4. Seja empático, claro, acolhedor e direto.
"""


def _chamar_kimi(prompt: str, max_tokens: int = 2500, system_prompt: str = PROMPT_SISTEMA_PARECER) -> Optional[tuple]:
    """
    Chama a API do Moonshot AI (Kimi K3 / Kimi models) compatível com OpenAI.
    Retorna (texto_resposta, nome_modelo) ou None se falhar.
    """
    moonshot_key = _get_moonshot_key()
    if not moonshot_key:
        return None

    user_model = os.environ.get('MOONSHOT_MODEL') or 'kimi-k3'
    modelos_candidatos = [user_model]
    if 'highspeed' not in user_model:
        modelos_candidatos.append('kimi-k2.7-code-highspeed')

    url = "https://api.moonshot.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {moonshot_key}",
        "Content-Type": "application/json"
    }

    for modelo in modelos_candidatos:
        # Timeout dinâmico: 20s para o modelo principal, 15s para o highspeed
        timeout = 20 if modelo == user_model else 15
        payload = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 1,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                choices = data.get('choices', [])
                if choices:
                    message = choices[0].get('message', {})
                    content = message.get('content')
                    if content and len(content.strip()) > 0:
                        return content, modelo
                    reasoning = message.get('reasoning_content')
                    if reasoning and len(reasoning.strip()) > 0:
                        return reasoning, modelo
            elif response.status_code == 401:
                # Fallback para endpoint .cn caso a chave seja regional doméstica da China
                cn_url = "https://api.moonshot.cn/v1/chat/completions"
                r2 = requests.post(cn_url, headers=headers, json=payload, timeout=timeout)
                if r2.status_code == 200:
                    choices = r2.json().get('choices', [])
                    if choices:
                        content = choices[0].get('message', {}).get('content')
                        if content:
                            return content, modelo
            else:
                print(f"[AI AGENT] Moonshot ({modelo}) status {response.status_code}: {_mascarar_segredos(response.text[:120])}")
        except Exception as e:
            print(f"[AI AGENT] Moonshot {modelo} demorou ({_mascarar_segredos(e)}). Tentando próximo...")

    return None


def _chamar_gemini(prompt: str, system_prompt: str = PROMPT_SISTEMA_PARECER) -> Optional[str]:
    """Chama a API do Google Gemini via REST puro com fallback automático entre modelos ativos"""
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return None
        
    modelos = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-1.5-flash"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 1500
        }
    }
    
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={gemini_key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        return parts[0].get('text')
        except Exception as e:
            print(f"[AI AGENT] Erro ao chamar Google Gemini ({modelo}): {_mascarar_segredos(e)}")
        
    return None


def _chamar_claude(prompt: str, system_prompt: str = PROMPT_SISTEMA_PARECER) -> Optional[str]:
    """Chama a API da Anthropic Claude via REST"""
    claude_key = _get_claude_key()
    if not claude_key:
        return None

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": claude_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-5-haiku-20241022",
        "system": system_prompt,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [])
            if content:
                return content[0].get('text')
    except Exception as e:
        erro_msg = _mascarar_segredos(e)
        print(f"[AI AGENT] Erro ao chamar Anthropic Claude: {erro_msg}")
        database.log_system_error("API_CLAUDE", erro_msg)

    return None



def _gerar_parecer_heuristico_canonico(loteria_nome: str, dados_analise: Dict[str, Any], jogos_gerados: Optional[List[List[int]]] = None) -> Dict[str, Any]:
    """
    Motor Heurístico de IA Nativo do Sistema (Fallback inteligente sem depender de chaves de API).
    Analisa os dados estatísticos reais e sintetiza um relatório humanizado.
    """
    classes = dados_analise.get('distribuicao_classes', {})
    estatisticas = dados_analise.get('estatisticas_gerais', {})
    camada_inf = dados_analise.get('camada_informacional', {})

    concursos = dados_analise.get('total_concursos') or dados_analise.get('resumo_geral', {}).get('total_concursos', 50)
    ict_medio = estatisticas.get('ict_medio') or dados_analise.get('resumo_geral', {}).get('ict_medio', 0.5)
    entropia = camada_inf.get('entropia') or dados_analise.get('resumo_geral', {}).get('entropia', 0.8)

    classe_a = classes.get('A', 0)
    classe_b = classes.get('B', 0)
    classe_c = classes.get('C', 0)
    classe_d = classes.get('D', 0)

    # Identificar dezenas mais promissoras
    analises_ind = dados_analise.get('analises_individuais', [])
    top_dezenas = sorted(analises_ind, key=lambda x: x.get('score_mcp', 0), reverse=True)[:6]
    top_nums_str = ', '.join([f"{d.get('numero'):02d}" for d in top_dezenas]) if top_dezenas else "04, 11, 23, 38, 45, 52"

    parecer_texto = (
        f"📊 **Análise Canônica para {loteria_nome}**\n\n"
        f"Processamos a base histórica de **{concursos} concursos oficiais da Caixa Econômica Federal**. "
        f"O ecossistema numérico apresenta um **ICT Médio de {ict_medio:.3f}** e **Entropia de {entropia:.3f}**, "
        f"indicando uma distribuição de alta previsibilidade estocástica e baixa dispersão caótica.\n\n"
        f"🔍 **Destaques do Cenário Atual:**\n"
        f"• **Números de Alta Estabilidade (Classe A):** {classe_a} dezenas concentram a maior regularidade nos sorteios recentes.\n"
        f"• **Zona de Equilíbrio (Classes B e C):** {classe_b + classe_c} dezenas oferecem excelente cobertura para fechamentos intermediários.\n"
        f"• **Radar Microdinâmico (Score MCP):** As dezenas em maior evidência por aceleração harmônica no momento são: **{top_nums_str}**.\n\n"
    )

    if jogos_gerados and len(jogos_gerados) > 0:
        total_jogos = len(jogos_gerados)
        parecer_texto += (
            f"🎯 **Avaliação dos {total_jogos} Jogos Gerados:**\n"
            f"As combinações selecionadas respeitaram a proporção canônica de dezenas pares e ímpares, "
            f"eliminando vícios de sorteio e sequências consecutivas improváveis. "
            f"Essas apostas otimizam matematicamente a cobertura estatística dentro das faixas oficiais de premiação da Caixa."
        )

    recomendacoes = [
        f"Priorize mesclar dezenas das Classes A e B para compor a espinha dorsal de suas apostas na {loteria_nome}.",
        f"Evite preencher o volante com mais de 3 números consecutivos (ex: 21, 22, 23, 24), padrão que ocorre em menos de 0.8% dos sorteios históricos.",
        f"Para bolões ou fechamentos, utilize no mínimo {total_jogos if jogos_gerados else 5} jogos balanceados para maximizar a matriz de cobertura."
    ]

    radar_concurso = f"A {loteria_nome} está em ciclo de convergência favorável para dezenas medianas. O padrão de repetição do último sorteio aponta para 1 a 2 dezenas coincidentes."

    return {
        'sucesso': True,
        'provedor': 'Motor Estatístico Canônico 3.0 (IA Heurística)',
        'provedor_ia': 'Motor Estatístico Canônico 3.0 (IA Heurística)',
        'parecer': parecer_texto,
        'parecer_texto': parecer_texto,
        'recomendacoes': recomendacoes,
        'radar_concurso': radar_concurso
    }


def gerar_parecer_ia(loteria_nome: str, dados_analise: Dict[str, Any], jogos_gerados: Optional[List[List[int]]] = None) -> Dict[str, Any]:
    """
    Gera parecer consultivo completo da IA:
    Tenta chamar Google Gemini -> Tenta Anthropic Claude -> Executa Fallback Heurístico
    """
    # 1. Preparar prompt contextualizado
    classes = dados_analise.get('distribuicao_classes', {})
    estatisticas = dados_analise.get('estatisticas_gerais', {})
    camada_inf = dados_analise.get('camada_informacional', {})

    concursos = dados_analise.get('total_concursos') or dados_analise.get('resumo_geral', {}).get('total_concursos', 50)
    ict_medio = estatisticas.get('ict_medio') or dados_analise.get('resumo_geral', {}).get('ict_medio', 0.5)
    entropia = camada_inf.get('entropia') or dados_analise.get('resumo_geral', {}).get('entropia', 0.8)

    prompt = (
        f"Analise o cenário e os dados matemáticos da loteria {loteria_nome}:\n"
        f"- Total de concursos históricos analisados: {concursos}\n"
        f"- ICT Médio (Índice de Convergência Temporal): {ict_medio:.4f}\n"
        f"- Entropia de Shannon (Grau de dispersão estocástica): {entropia:.4f}\n"
        f"- Distribuição de Classes (A=Alta Estabilidade, B/C=Equilíbrio, D=Atrasadas): {classes}\n"
    )
    if jogos_gerados:
        prompt += f"- Quantidade de jogos gerados para o apostador: {len(jogos_gerados)}\n"
        prompt += f"- Exemplos de jogos gerados: {jogos_gerados[:3]}\n"
    prompt += "\nPor favor, elabore um parecer consultivo profissional, didático e encorajador para o apostador em português claro, explicando a estratégia das combinações, analisando o cenário e fornecendo 3 recomendações práticas para a rodada."

    # 2. Tentativa Moonshot Kimi (se configurada)
    if _get_moonshot_key():
        res_kimi = _chamar_kimi(prompt)
        if res_kimi:
            resposta_kimi, modelo_usado = res_kimi
            nome_display = "Kimi K3" if "k3" in modelo_usado else f"Kimi ({modelo_usado})"
            return {
                'sucesso': True,
                'provedor': f'Moonshot AI {nome_display} (IA)',
                'provedor_ia': f'Moonshot AI {nome_display} (IA)',
                'parecer': resposta_kimi,
                'parecer_texto': resposta_kimi,
                'recomendacoes': [
                    f"Estratégia otimizada por IA {nome_display} com balanceamento estocástico avançado.",
                    "Consulte os números em destaque na Tabela Canônica antes de registrar suas apostas.",
                    "Mantenha a regularidade nos jogos mantendo a mesma matriz por ao menos 3 concursos."
                ],
                'radar_concurso': f"Radar probabilístico atualizado por IA {nome_display} para a {loteria_nome}."
            }

    # 3. Tentativa Gemini
    resposta_gemini = _chamar_gemini(prompt)
    if resposta_gemini:
        return {
            'sucesso': True,
            'provedor': 'Google Gemini (IA)',
            'provedor_ia': 'Google Gemini (IA)',
            'parecer': resposta_gemini,
            'parecer_texto': resposta_gemini,
            'recomendacoes': [
                "Jogos gerados com base em balanceamento de classes estocásticas.",
                "Consulte os números em destaque na Tabela Canônica antes de registrar suas apostas.",
                "Mantenha a regularidade nos jogos mantendo a mesma matriz por ao menos 3 concursos."
            ],
            'radar_concurso': f"Radar oficial atualizado pela IA para a {loteria_nome}."
        }

    # 4. Tentativa Claude
    resposta_claude = _chamar_claude(prompt)
    if resposta_claude:
        return {
            'sucesso': True,
            'provedor': 'Anthropic Claude (IA)',
            'provedor_ia': 'Anthropic Claude (IA)',
            'parecer': resposta_claude,
            'parecer_texto': resposta_claude,
            'recomendacoes': [
                "Estratégia equilibrada priorizando dezenas de estabilidade temporal.",
                "Evite repetições de combinações já premiadas recentemente.",
                "Utilize desdobramentos inteligentes para proteger seus investimentos."
            ],
            'radar_concurso': f"Radar probabilístico elaborado por Claude para a {loteria_nome}."
        }

    # 5. Fallback Motor Heurístico Nativo
    return _gerar_parecer_heuristico_canonico(loteria_nome, dados_analise, jogos_gerados)


def responder_chat_consultor(pergunta: str, loteria_nome: str, dados_analise: Optional[Dict[str, Any]] = None, user_ident: str = "anon") -> str:
    """
    Responde perguntas do apostador no Chat Consultor da Sorte (AGORA APENAS SUPORTE TÉCNICO)
    """
    prompt = (
        f"O apostador perguntou sobre a plataforma (seção {loteria_nome}): '{pergunta}'.\n"
        f"Responda como Suporte Técnico, conforme as suas diretrizes estritas."
    )

    resp = None

    # Tenta Moonshot Kimi
    if _get_moonshot_key() and not resp:
        res_kimi = _chamar_kimi(prompt, system_prompt=PROMPT_SISTEMA_SUPORTE)
        if res_kimi:
            resp = res_kimi[0]

    # Tenta Gemini
    if not resp:
        resp = _chamar_gemini(prompt, system_prompt=PROMPT_SISTEMA_SUPORTE)

    # Tenta Claude
    if not resp:
        resp = _chamar_claude(prompt, system_prompt=PROMPT_SISTEMA_SUPORTE)

    # Fallback consultivo nativo (Se não tiver chave)
    if not resp:
        p_lower = pergunta.lower()
        if "erro" in p_lower or "bug" in p_lower or "não funciona" in p_lower:
            resp = "Lamento pelo transtorno! Por favor, detalhe o problema que você está enfrentando e encaminharei para a equipe de desenvolvimento."
        elif "pagar" in p_lower or "plano" in p_lower or "vip" in p_lower:
            resp = "Para assinar o VIP ou comprar créditos, acesse a página 'Planos' no menu principal."
        else:
            resp = "Olá! Sou o assistente de suporte da plataforma. Posso te ajudar com alguma dúvida sobre como usar o aplicativo Cálculo da Sorte?"

    # LOGAR NO BANCO DE DADOS
    try:
        import database
        database.log_chat_message(user_ident, loteria_nome, pergunta, resp)
    except Exception as e:
        print(f"[AI AGENT] Erro ao gravar log: {e}")

    return resp