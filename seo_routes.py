from flask import Blueprint, render_template, request, jsonify
from math import comb
import json
import datetime
from core import LOTERIAS_CONFIG
import updater

seo_bp = Blueprint('seo', __name__)

# Helpers
def _calcula_probabilidade(loteria_key, apostadas, acertos_desejados):
    cfg = LOTERIAS_CONFIG[loteria_key]
    N = cfg.universo
    k = cfg.sorteados
    if cfg.colunas:
        # Simplificação para exibição da chance
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
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG:
        return "Not found", 404
        
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    # Gerar tabela
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
            
    resposta_direta = f"A probabilidade de ganhar o prêmio principal da {cfg.nome} com uma aposta simples de {cfg.minimo_aposta} números é de 1 em {round(1/_calcula_probabilidade(loteria_key, cfg.minimo_aposta, cfg.sorteados)):,}."
    resposta_direta = resposta_direta.replace(',', '.')

    faq_items = [
        (f"Qual a chance de ganhar na {cfg.nome}?", f"Com a aposta mínima ({cfg.minimo_aposta} dezenas), a chance é de 1 em {round(1/_calcula_probabilidade(loteria_key, cfg.minimo_aposta, cfg.sorteados)):,}.".replace(',', '.')),
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
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    resposta_direta = f"O fechamento da {cfg.nome} é uma estratégia matemática que permite apostar com mais dezenas pagando menos. Se as {cfg.sorteados} dezenas sorteadas estiverem no seu grupo escolhido, o sistema garante uma faixa mínima de premiação (ex: {cfg.sorteados - 1} pontos)."
    
    faq_items = [
        (f"Qual a diferença entre fechamento e desdobramento na {cfg.nome}?", "O desdobramento joga todas as combinações possíveis de um grupo de números, o que pode ser caro. O fechamento elimina combinações redundantes, garantindo uma premiação menor (ex: quadra) e reduzindo drasticamente o custo da aposta."),
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
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
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
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    mes_ano = datetime.datetime.now().strftime('%B/%Y').replace('September', 'Setembro') # rudimentar, mas serve pro proposito local
    
    h1 = f"Números que Mais Saem na {cfg.nome} (Atualizado {mes_ano})"
    resposta_direta = f"Aqui estão as dezenas mais sorteadas na história da {cfg.nome}. Lembre-se: no paradoxo do jogador, a frequência passada de um número não altera sua probabilidade futura, pois os sorteios são independentes."
    
    historico = updater.carregar_historico_local(loteria_key)
    
    # Process frequency
    from collections import Counter
    todas_dezenas = []
    for c in historico:
        if 'dezenas' in c:
            todas_dezenas.extend(c['dezenas'])
            
    contagem = Counter(todas_dezenas)
    top_5 = contagem.most_common(5)
    bottom_5 = contagem.most_common()[-5:] if len(contagem) >= 5 else []
    
    resposta_direta = f"As 5 dezenas que mais saíram na {cfg.nome} até hoje foram {', '.join(str(d) for d, v in top_5)}. " + resposta_direta
    
    return render_template('seo_estatisticas.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=h1,
                           resposta_direta=resposta_direta,
                           cfg=cfg,
                           top_5=top_5,
                           bottom_5=bottom_5)

@seo_bp.route('/<loteria_slug>/concurso/<int:numero>')
def concurso(loteria_slug, numero):
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    historico = updater.carregar_historico_local(loteria_key)
    concurso_data = next((c for c in historico if c.get('concurso') == numero), None)
    if not concurso_data:
        return "Concurso não encontrado.", 404
        
    dezenas = concurso_data.get('dezenas', [])
    data_str = concurso_data.get('data', '')
    
    h1 = f"Resultado {cfg.nome} Concurso {numero} — {data_str}"
    
    return render_template('seo_concurso.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=h1,
                           concurso=concurso_data,
                           dezenas=dezenas,
                           cfg=cfg)

@seo_bp.route('/<loteria_slug>')
def hub(loteria_slug):
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    historico = updater.carregar_historico_local(loteria_key)
    ultimo = historico[0] if historico else None
    
    return render_template('seo_hub_loteria.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           ultimo=ultimo)


@seo_bp.route('/embed/<loteria_slug>/<ferramenta>')
def embed(loteria_slug, ferramenta):
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    return render_template('seo_embed.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           ferramenta_tipo=ferramenta)


@seo_bp.route('/lotofacil/fechamento-<int:dezenas>-dezenas')
def lotofacil_fechamento_especifico(dezenas):
    cfg = LOTERIAS_CONFIG['lotofacil']
    faq_items = [
        ("Vale a pena fazer esse fechamento?", "Sim, reduz bastante o custo comparado ao desdobramento completo."),
    ]
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug='lotofacil',
                           h1_title=f"Fechamento Lotofácil {dezenas} Dezenas",
                           resposta_direta=f"Fechamento otimizado para jogar {dezenas} dezenas na Lotofácil garantindo prêmios menores com custo reduzido.",
                           cfg=cfg,
                           ferramenta_tipo='fechamento',
                           faq_items=faq_items)

@seo_bp.route('/lotofacil/desdobramento')
def lotofacil_desdobramento():
    cfg = LOTERIAS_CONFIG['lotofacil']
    faq_items = [
        ("Como fazer o desdobramento da Lotofácil?", "Escolha mais de 15 dezenas no volante e o sistema gera todas as combinações possíveis."),
    ]
    return render_template('seo_ferramenta_form.html',
                           loteria_nome=cfg.nome,
                           loteria_slug='lotofacil',
                           h1_title="Como Fazer Desdobramento da Lotofácil",
                           resposta_direta="O desdobramento da Lotofácil consiste em gerar absolutamente todas as combinações de 15 números possíveis dentro de um grupo maior de dezenas.",
                           cfg=cfg,
                           ferramenta_tipo='simulador',
                           faq_items=faq_items)

@seo_bp.route('/<loteria_slug>/numeros-atrasados')
def numeros_atrasados(loteria_slug):
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    return render_template('seo_estatisticas.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           h1_title=f"Números mais Atrasados na {cfg.nome}",
                           resposta_direta=f"Aqui estão as dezenas que não saem há mais tempo na {cfg.nome}. Lembre-se: no paradoxo do jogador, a frequência passada não altera a probabilidade futura.",
                           cfg=cfg,
                           top_5=[],
                           bottom_5=[])


@seo_bp.route('/resultados/<loteria_slug>')
@seo_bp.route('/resultados/<loteria_slug>/pagina/<int:page>')
def resultados_lista(loteria_slug, page=1):
    loteria_key = loteria_slug.replace('-', '_')
    if loteria_key not in LOTERIAS_CONFIG: return "Not found", 404
    cfg = LOTERIAS_CONFIG[loteria_key]
    
    historico = updater.carregar_historico_local(loteria_key)
    per_page = 20
    total = len(historico)
    total_pages = (total + per_page - 1) // per_page
    
    if page < 1 or (page > total_pages and total > 0):
        return "Not found", 404
        
    start = (page - 1) * per_page
    end = start + per_page
    itens_pagina = historico[start:end]
    
    return render_template('seo_resultados_lista.html',
                           loteria_nome=cfg.nome,
                           loteria_slug=loteria_slug,
                           cfg=cfg,
                           itens=itens_pagina,
                           page=page,
                           total_pages=total_pages)

def register_seo_routes(app):
    app.register_blueprint(seo_bp)

