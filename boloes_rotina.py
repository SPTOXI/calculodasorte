"""
Rotina diária dos bolões (chamada pelo cron das 23h e pelo botão do admin):
1. define o prazo do comprovante quando a Caixa divulga a data do sorteio;
2. avisa o organizador por e-mail quando faltam menos de 24h para o prazo;
3. cancela bolões sem comprovante após o prazo e marca os pagamentos para reembolso;
4. confere o resultado dos bolões registrados depois do sorteio.
"""

from datetime import datetime, timedelta
from typing import Dict, List

import bolao
import conferencia
import database
import notificacoes
import updater

JANELA_ALERTA = timedelta(hours=24)


def _enviar(destino: str, assunto: str, texto: str) -> bool:
    if not destino or not notificacoes.email_configurado():
        return False
    html = '<p>' + texto.replace('\n', '<br>') + '</p>'
    return notificacoes.enviar_email(destino, assunto, html, texto)


def _email_organizador(b: Dict) -> str:
    org = database.get_user_by_id(b['organizador_id'])
    return (org or {}).get('email', '')


def definir_prazos(boloes: List[Dict], cfg: Dict) -> int:
    definidos = 0
    for b in boloes:
        if b.get('prazo_comprovante') or b['status'] == 'registrado':
            continue
        sorteio = bolao.data_do_sorteio(updater.carregar_ultimo_resultado_local(b['loteria_type']), b['concurso'])
        prazo = bolao.calcular_prazo_comprovante(sorteio, cfg['horas_comprovante'])
        if prazo:
            database.definir_prazo_bolao(b['id'], sorteio, prazo)
            b['data_sorteio'], b['prazo_comprovante'] = sorteio, prazo
            definidos += 1
    return definidos


def alertar_e_cancelar(boloes: List[Dict], agora: datetime) -> Dict[str, int]:
    alertas = cancelados = 0
    site = notificacoes._site_url()
    for b in boloes:
        prazo = b.get('prazo_comprovante')
        if b['status'] not in ('aberto', 'fechado') or not prazo:
            continue
        if agora >= prazo:
            afetados = database.cancelar_bolao(b['id'], 'Comprovante não enviado dentro do prazo.')
            cancelados += 1
            for comprador in afetados:
                _enviar(comprador['email'], f"Bolão cancelado: {b['titulo']}",
                        f"Olá, {comprador['name']}.\n\nO bolão \"{b['titulo']}\" foi cancelado porque o comprovante de "
                        f"registro não foi enviado no prazo. O valor da sua cota nº {comprador['numero']} será devolvido.\n\n"
                        f"{site}/minhas-cotas")
            _enviar(_email_organizador(b), f"Bolão cancelado: {b['titulo']}",
                    f"O bolão \"{b['titulo']}\" foi cancelado automaticamente por falta de comprovante no prazo. "
                    f"{len(afetados)} cota(s) paga(s) serão reembolsadas.")
        elif prazo - agora <= JANELA_ALERTA and not b.get('alerta_prazo_em'):
            enviado = _enviar(_email_organizador(b), f"Prazo do comprovante: {b['titulo']}",
                              f"Faltam menos de 24 horas para o prazo de envio do comprovante do bolão \"{b['titulo']}\" "
                              f"(prazo: {prazo.strftime('%d/%m/%Y %H:%M')} UTC).\n\nSem o comprovante, o bolão será "
                              f"cancelado e as cotas reembolsadas.\n\n{site}/organizador")
            if enviado:
                database.marcar_alerta_prazo(b['id'])
                alertas += 1
    return {'alertas': alertas, 'cancelados': cancelados}


def conferir_resultados(boloes: List[Dict]) -> int:
    conferidos = 0
    for b in boloes:
        if b['status'] != 'registrado':
            continue
        sorteio = conferencia.sorteio_do_concurso(b['loteria_type'], b['concurso'])
        if sorteio['status'] != 'conferido':
            continue
        detalhes = database.get_bolao(b['id'], com_jogos=True)
        jogos = [j['dezenas'] for j in detalhes['jogos']]
        complementos = [j['complemento'] for j in detalhes['jogos']]
        resultado_jogos, premiacoes = conferencia.conferir_jogos(
            b['loteria_type'], jogos, sorteio['dezenas'], sorteio['segundo_sorteio'],
            complemento_sorteio=sorteio.get('complemento'), complementos_jogos=complementos)
        premiado = any(j['rotulo_premio'] for j in resultado_jogos)
        database.salvar_resultado_bolao(b['id'], {
            'concurso': sorteio['concurso'],
            'data_apuracao': sorteio.get('data_apuracao'),
            'dezenas': sorteio['dezenas'],
            'segundo_sorteio': sorteio['segundo_sorteio'],
            'complemento': sorteio.get('complemento'),
            'jogos': [{k: j[k] for k in ('numero', 'jogo', 'acertos', 'qtd_acertos', 'rotulo_premio')} for j in resultado_jogos],
            'premiacoes': premiacoes,
        }, premiado)
        conferidos += 1
        if premiado:
            _enviar(_email_organizador(b), f"Bolão premiado: {b['titulo']}",
                    f"O bolão \"{b['titulo']}\" foi premiado no concurso {sorteio['concurso']}: "
                    f"{', '.join(f'{qtd}x {rotulo}' for rotulo, qtd in premiacoes.items())}.\n\n"
                    f"Depois de resgatar o prêmio, informe o valor líquido ao administrador para o rateio entre as cotas.")
    return conferidos


def executar(agora: datetime = None) -> Dict:
    """Roda todas as tarefas; cada uma é independente para que a falha de uma não impeça as demais."""
    agora = agora or datetime.utcnow()
    cfg = database.get_bolao_config()
    relatorio: Dict = {}
    try:
        boloes = database.boloes_em_andamento()
        relatorio['prazos_definidos'] = definir_prazos(boloes, cfg)
        relatorio.update(alertar_e_cancelar(boloes, agora))
        relatorio['conferidos'] = conferir_resultados(boloes)
    except Exception as e:
        print(f"[BOLOES] Erro na rotina diária: {e}")
        relatorio['erro'] = str(e)
    return relatorio
