"""
Aplicação Web Flask para Análise Estatística de Loterias
Baseada no Modelo Canônico 3.0 + MCP-MD 1.0
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
from core import (
    ModeloCanonico30, 
    ValidaçãoCamada7, 
    gerar_jogo_sugerido,
    LoteriaType, 
    LOTERIAS_CONFIG
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'loteria-canonical-key-2024'

# Diretório para armazenar dados
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)


def carregar_historico(loteria_type: str) -> list:
    """Carregar histórico de concursos do arquivo JSON"""
    arquivo = os.path.join(DATA_DIR, f'{loteria_type}_historico.json')
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def salvar_historico(loteria_type: str, historico: list):
    """Salvar histórico de concursos no arquivo JSON"""
    arquivo = os.path.join(DATA_DIR, f'{loteria_type}_historico.json')
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


@app.route('/')
def index():
    """Página inicial com seleção de loteria"""
    loterias = [
        {
            'id': loteria.value,
            'nome': loteria.value.replace('_', ' ').title(),
            'config': config
        }
        for loteria, config in LOTERIAS_CONFIG.items()
    ]
    return render_template('index.html', loterias=loterias)


@app.route('/analise/<loteria_type>')
def analise_page(loteria_type: str):
    """Página de análise para uma loteria específica"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return redirect(url_for('index'))
    
    return render_template('analise.html', loteria=loteria, config=config)


@app.route('/api/analise/<loteria_type>', methods=['POST'])
def api_analise(loteria_type: str):
    """API para realizar análise estatística completa"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    # Obter dados do request
    dados = request.get_json() or {}
    historico_input = dados.get('historico', [])
    
    # Se não houver histórico no input, carregar do arquivo
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({
            'erro': 'Histórico insuficiente. Mínimo de 10 concursos necessários.',
            'concursos_atuais': len(historico_input)
        }), 400
    
    # Criar modelo e realizar análise
    modelo = ModeloCanonico30(historico_input, loteria)
    resumo = modelo.obter_resumo_analise()
    
    # Realizar validações da Camada 7
    validacao = ValidaçãoCamada7(modelo)
    resumo['validacao_camada7'] = validacao.validacao_completa()
    
    # Gerar sugestões de jogos
    config = LOTERIAS_CONFIG[loteria]
    resumo['sugestoes'] = {
        'jogo_simples': gerar_jogo_sugerido(modelo, config.minimo_aposta),
        'jogo_medio': gerar_jogo_sugerido(modelo, min(config.minimo_aposta + 2, config.maximo_aposta)),
    }
    
    return jsonify(resumo)


@app.route('/api/salvar-historico/<loteria_type>', methods=['POST'])
def api_salvar_historico(loteria_type: str):
    """API para salvar histórico de concursos"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json()
    historico = dados.get('historico', [])
    
    if not historico:
        return jsonify({'erro': 'Histórico vazio'}), 400
    
    # Validar formato do histórico
    for concurso in historico:
        if not isinstance(concurso, list) or len(concurso) == 0:
            return jsonify({'erro': 'Formato de concurso inválido'}), 400
    
    salvar_historico(loteria_type, historico)
    
    return jsonify({
        'sucesso': True,
        'concursos_salvos': len(historico)
    })


@app.route('/api/carregar-historico/<loteria_type>', methods=['GET'])
def api_carregar_historico(loteria_type: str):
    """API para carregar histórico salvo"""
    historico = carregar_historico(loteria_type)
    return jsonify({
        'historico': historico,
        'concursos_count': len(historico)
    })


@app.route('/gerar-jogo/<loteria_type>', methods=['POST'])
def gerar_jogo(loteria_type: str):
    """Gerar sugestão de jogo baseado na análise"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json() or {}
    historico_input = dados.get('historico', [])
    quantidade = dados.get('quantidade', LOTERIAS_CONFIG[loteria].minimo_aposta)
    
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({'erro': 'Histórico insuficiente para análise'}), 400
    
    modelo = ModeloCanonico30(historico_input, loteria)
    jogo = gerar_jogo_sugerido(modelo, quantidade)
    
    return jsonify({
        'jogo': jogo,
        'quantidade': len(jogo),
        'analise_resumo': {
            'ict_medio': modelo.obter_resumo_analise()['estatisticas_gerais']['ict_medio'],
            'entropia': modelo.obter_resumo_analise()['camada_informacional']['entropia']
        }
    })


@app.route('/comparar-concursos/<loteria_type>', methods=['POST'])
def comparar_concursos(loteria_type: str):
    """Comparar concurso atual com padrões históricos"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json()
    concurso_atual = dados.get('concurso', [])
    historico_input = dados.get('historico', [])
    
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({'erro': 'Histórico insuficiente'}), 400
    
    modelo = ModeloCanonico30(historico_input, loteria)
    analises = modelo.analisar_todos_elementos()
    
    # Calcular score médio do concurso atual
    scores_concurso = []
    numeros_analisados = []
    
    for numero in concurso_atual:
        if 1 <= numero <= modelo.N:
            analise = next((a for a in analises if a.numero == numero), None)
            if analise:
                scores_concurso.append(analise.score_mcp)
                numeros_analisados.append({
                    'numero': numero,
                    'score_mcp': round(analise.score_mcp, 4),
                    'classe': analise.classe,
                    'maturidade': analise.maturidade
                })
    
    score_medio_concurso = sum(scores_concurso) / len(scores_concurso) if scores_concurso else 0
    score_medio_geral = sum(a.score_mcp for a in analises) / len(analises)
    
    return jsonify({
        'concurso': concurso_atual,
        'numeros_analisados': numeros_analisados,
        'score_medio_concurso': round(score_medio_concurso, 4),
        'score_medio_geral': round(score_medio_geral, 4),
        'performance_relativa': round(score_medio_concurso / score_medio_geral, 4) if score_medio_geral > 0 else 0,
        'interpretacao': 'Acima da média' if score_medio_concurso > score_medio_geral else 'Abaixo da média'
    })


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
