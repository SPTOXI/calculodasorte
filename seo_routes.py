from flask import Blueprint, render_template, request, jsonify
from math import comb
import json
import datetime
from collections import Counter
from core import LOTERIAS_CONFIG, LoteriaType
import updater

seo_bp = Blueprint('seo', __name__)

def get_config(loteria_slug):
    loteria_key = str(loteria_slug).replace('-', '_').lower()
    for k, v in LOTERIAS_CONFIG.items():
        if k.value == loteria_key:
            return k.value, v
    return None, None

def _calcula_probabilidade(loteria_key, apostadas, acertos_desejados):
    _, cfg = get_config(loteria_key)
    if not cfg:
        return 0
    N = cfg.universo
    k = cfg.sorteados
    if cfg.colunas:
        return 0
    try:
        if apostadas < k or acertos_desejados > k:
            return 0
        total_comb = comb(N, k)
        chance = comb(apostadas, acertos_desejados) * comb(N - apostadas, k - acertos_desejados) / total_comb
        return chance
    except:
        return 0

@seo_bp.route('/<loteria_slug>/probabilidade')
def probabilidade(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg:
        return "Not found", 404
        
    tabela = []
    if not cfg.colunas:
        for qtde in range(cfg.minimo_aposta, cfg.maximo_aposta + 1):
            apostas = comb(qtde, cfg.minimo_aposta)
            custo = apostas * cfg.custo_minimo
            
            linha = {
                'quantidade': qtde,
                'apostas': apostas,
                'custo': f"R$ {custo:,.2f}".replace('.',','),
                'faixas': []
            }
            for faixa in cfg.faixas_premiacao:
                chance = _calcula_probabilidade(loteria_key, qtde, faixa)
                um_em = round(1 / chance) if chance > 0 else 0
                linha['faixas'].append({'acertos': faixa, 'um_em': f"1 em {um_em:,}".replace(',','.') if um_em > 0 else '-'})
            tabela.append(linha)
            
    prob_min = _calcula_probabilidade(loteria_key, cfg.minimo_aposta, cfg.sorteados)
    chance_principal = f"1 em {round(1/prob_min):,}".replace(',', '.') if prob_min > 0 else "N/A"
    resposta_direta = f"A probabilidade de ganhar o prêmio principal da {cfg.nome} com uma aposta simples de {cfg.minimo_aposta} números é de {chance_principal}."

    faq_items = [
        (f"Qual a chance de ganhar na {cfg.nome}?", f"Com a aposta mínima ({cfg.minimo_aposta} dezenas), a chance é de {chance_principal}."),
        (f"Vale a pena jogar mais dezenas na {cfg.nome}?", f"Sim, a chance aumenta proporcionalmente, mas o custo da aposta também sobe. Verifique a tabela completa abaixo.")
    ]

    return render_template('seo_probabilidade.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Tabela de Probabilidade da {cfg.nome}",
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           tabela=tabela,
                           faq_items=faq_items)

@seo_bp.route('/<loteria_slug>/fechamento')
def fechamento_geral(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    resposta_direta = f"O fechamento da {cfg.nome} é uma estratégia matemática que permite apostar com mais dezenas pagando menos. Se as {cfg.sorteados} dezenas sorteadas estiverem no seu grupo escolhido, o sistema garante uma faixa mínima de premiação (ex: {cfg.sorteados - 1} pontos)."
    
    faq_items = [
        (f"Qual a diferença entre fechamento e desdobramento na {cfg.nome}?", f"O desdobramento joga todas as combinações possíveis de um grupo de números, o que pode ser caro. O fechamento elimina combinações redundantes, garantindo uma premiação menor e reduzindo drasticamente o custo da aposta."),
        ("O fechamento garante prêmio?", "A garantia matemática está condicionada ao acerto das dezenas sorteadas dentro do grupo de dezenas que você escolheu. Sem acertar as dezenas no grupo, não há garantia.")
    ]
    
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Fechamento da {cfg.nome} Grátis",
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           ferramenta_tipo='fechamento',
                           faq_items=faq_items)

@seo_bp.route('/<loteria_slug>/simulador')
def simulador(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    resposta_direta = f"O Simulador da {cfg.nome} analisa suas dezenas em relação a todos os concursos já realizados. Ele mostra se os seus números já foram sorteados antes e qual a chance real deles saírem no próximo sorteio."
    
    faq_items = [
        (f"O simulador da {cfg.nome} aumenta minhas chances?", "Não. Todas as combinações têm a mesma probabilidade de serem sorteadas. O simulador ajuda a evitar padrões viciados que, se sorteados, dividiriam o prêmio com muitas pessoas.")
    ]
    
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Simulador da {cfg.nome} Grátis",
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           ferramenta_tipo='simulador',
                           faq_items=faq_items)

@seo_bp.route('/<loteria_slug>/numeros-mais-sorteados')
def numeros_mais_sorteados(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    mes_ano = datetime.datetime.now().strftime('%m/%Y')
    
    h1 = f"Números que Mais Saem na {cfg.nome} (Atualizado {mes_ano})"
    resposta_direta = f"Aqui estão as dezenas mais sorteadas na história da {cfg.nome}. Lembre-se: no paradoxo do jogador, a frequência passada de um número não altera sua probabilidade futura, pois os sorteios são independentes."
    
    historico = updater.carregar_historico_local(loteria_key)
    
    todas_dezenas = []
    for dezenas in historico:
        todas_dezenas.extend(dezenas)
            
    contagem = Counter(todas_dezenas)
    top_5 = contagem.most_common(5)
    bottom_5 = contagem.most_common()[-5:] if len(contagem) >= 5 else []
    
    if top_5:
        resposta_direta = f"As 5 dezenas que mais saíram na {cfg.nome} até hoje foram {', '.join(str(d) for d, v in top_5)}. " + resposta_direta
    
    return render_template('seo_estatisticas.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=h1,
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           modo='sorteadas',
                           top_5=top_5,
                           bottom_5=bottom_5)

@seo_bp.route('/<loteria_slug>/concurso/<int:numero>')
def concurso(loteria_slug, numero):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    meta = updater.carregar_meta(loteria_key)
    ultimo_local = meta.get('ultimo_concurso') or 0
    historico = updater.carregar_historico_local(loteria_key)
    
    dezenas = None
    data_str = ""
    
    # 1. Checa se é o último concurso salvo completo
    ultimo_resultado = updater.carregar_ultimo_resultado_local(loteria_key)
    if ultimo_resultado and str(ultimo_resultado.get('numero', '')) == str(numero):
        data_str = ultimo_resultado.get('dataApuracao', '')
        lista_dez = ultimo_resultado.get('listaDezenas', [])
        dezenas = [int(d) for d in lista_dez] if lista_dez else None
        
    # 2. Checa se está no histórico local em disco
    if not dezenas and historico and ultimo_local:
        primeiro_local = ultimo_local - len(historico) + 1
        if primeiro_local <= numero <= ultimo_local:
            idx = numero - primeiro_local
            dezenas = historico[idx]
            
    # 3. Se for mais antigo, busca na API oficial da Caixa
    if not dezenas:
        slug_caixa = updater.LOTERIAS_SLUGS.get(loteria_key)
        if slug_caixa:
            try:
                dados_caixa = updater.consultar_caixa(slug_caixa, concurso=numero)
                if dados_caixa and dados_caixa.get('numero'):
                    dezenas = updater.extrair_dezenas(dados_caixa, slug_caixa)
                    data_str = dados_caixa.get('dataApuracao', '')
            except Exception as e:
                print(f"[CONCURSO] Erro ao consultar Caixa concurso {numero}: {e}")
                
    if not dezenas:
        return "Concurso não encontrado.", 404
        
    h1 = f"Resultado {cfg.nome} Concurso {numero}"
    if data_str:
        h1 += f" - {data_str}"
        
    concurso_data = {'concurso': numero, 'data': data_str, 'dezenas': dezenas}
    
    return render_template('seo_concurso.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=h1,
                           concurso=concurso_data,
                           dezenas=dezenas,
                           cfg=cfg)

@seo_bp.route('/<loteria_slug>')
def hub(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    ultimo_resultado = updater.carregar_ultimo_resultado_local(loteria_key)
    ultimo = None
    if ultimo_resultado:
        lista_dez = ultimo_resultado.get('listaDezenas', [])
        ultimo = {
            'concurso': ultimo_resultado.get('numero'),
            'data': ultimo_resultado.get('dataApuracao', ''),
            'dezenas': [int(d) for d in lista_dez] if lista_dez else []
        }
    
    return render_template('seo_hub_loteria.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           ultimo=ultimo)

@seo_bp.route('/embed/<loteria_slug>/<ferramenta>')
def embed(loteria_slug, ferramenta):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    return render_template('seo_embed.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           ferramenta_tipo=ferramenta)

@seo_bp.route('/lotofacil/fechamento-<int:dezenas>-dezenas')
@seo_bp.route('/<loteria_slug>/fechamento-<int:dezenas>-dezenas')
def fechamento_especifico(dezenas, loteria_slug='lotofacil'):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    faq_items = [
        ("Vale a pena fazer esse fechamento?", "Sim, reduz bastante o custo comparado ao desdobramento completo."),
    ]
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Fechamento {cfg.nome} {dezenas} Dezenas",
                           resposta_direta=f"Fechamento otimizado para jogar {dezenas} dezenas na {cfg.nome} garantindo prêmios menores com custo reduzido.",
                           cfg=cfg,
                           ferramenta_tipo='fechamento',
                           faq_items=faq_items)

@seo_bp.route('/lotofacil/desdobramento')
@seo_bp.route('/<loteria_slug>/desdobramento')
def desdobramento(loteria_slug='lotofacil'):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    faq_items = [
        (f"Como fazer o desdobramento da {cfg.nome}?", f"Escolha mais de {cfg.minimo_aposta} dezenas no volante e o sistema gera todas as combinações possíveis."),
    ]
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Como Fazer Desdobramento da {cfg.nome}",
                           resposta_direta=f"O desdobramento da {cfg.nome} consiste em gerar absolutamente todas as combinações de {cfg.minimo_aposta} números possíveis dentro de um grupo maior de dezenas.",
                           cfg=cfg,
                           ferramenta_tipo='simulador',
                           faq_items=faq_items)

@seo_bp.route('/<loteria_slug>/numeros-atrasados')
def numeros_atrasados(loteria_slug):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404

    historico = updater.carregar_historico_local(loteria_key)
    universo_numeros = cfg.numeros
    ultima_aparicao = {n: None for n in universo_numeros}
    for idx, dezenas in enumerate(historico):
        for n in dezenas:
            if n in ultima_aparicao:
                ultima_aparicao[n] = idx

    total = len(historico)

    def atraso(n):
        return total if ultima_aparicao[n] is None else total - 1 - ultima_aparicao[n]

    ranking = sorted(universo_numeros, key=lambda n: (-atraso(n), n))
    top_5 = [(n, atraso(n)) for n in ranking[:5]]
    bottom_5 = [(n, atraso(n)) for n in ranking[-5:]] if len(ranking) >= 5 else []

    resposta_direta = f"Aqui estão as dezenas que não saem há mais tempo na {cfg.nome}. Lembre-se: no paradoxo do jogador, a frequência passada não altera a probabilidade futura."
    if top_5:
        resposta_direta = f"As dezenas mais atrasadas da {cfg.nome} são {', '.join(str(d) for d, v in top_5)}. " + resposta_direta

    return render_template('seo_estatisticas.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Números mais Atrasados na {cfg.nome}",
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           modo='atrasadas',
                           top_5=top_5,
                           bottom_5=bottom_5)

@seo_bp.route('/resultados/<loteria_slug>')
@seo_bp.route('/resultados/<loteria_slug>/pagina/<int:page>')
def resultados_lista(loteria_slug, page=1):
    loteria_key, cfg = get_config(loteria_slug)
    if not cfg: return "Not found", 404
    
    meta = updater.carregar_meta(loteria_key)
    ultimo_local = meta.get('ultimo_concurso') or 0
    historico = updater.carregar_historico_local(loteria_key)
    total = len(historico)
    
    per_page = 20
    total_pages = max(1, (total + per_page - 1) // per_page)
    
    if page < 1 or page > total_pages:
        return "Not found", 404
        
    start_offset = (page - 1) * per_page
    end_offset = min(total, start_offset + per_page)
    
    itens_pagina = []
    # Most recent first
    for i in range(start_offset, end_offset):
        idx_in_historico = total - 1 - i
        num_concurso = ultimo_local - i if ultimo_local else (total - i)
        itens_pagina.append({
            'concurso': num_concurso,
            'data': '',
            'dezenas': historico[idx_in_historico]
        })
    
    return render_template('seo_resultados_lista.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           itens=itens_pagina,
                           page=page,
                           total_pages=total_pages)

def register_seo_routes(app):
    app.register_blueprint(seo_bp)
