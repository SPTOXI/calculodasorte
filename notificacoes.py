"""
Aviso por e-mail de apostas premiadas, enviado depois da sincronização dos resultados.

Configuração (variáveis de ambiente), uma das opções:
- RESEND_API_KEY: envio pela API do Resend (https://resend.com)
- SMTP_HOST, SMTP_PORT (587 ou 465), SMTP_USER, SMTP_PASSWORD: envio por SMTP
EMAIL_FROM define o remetente e SITE_URL o endereço usado nos links.
"""

import html
import os
import smtplib
from email.message import EmailMessage
from typing import Dict, List

import requests

import conferencia
import database
import updater
from core import LOTERIAS_CONFIG, LoteriaType

# Só avisa apostas de concursos recentes (evita e-mails de prêmios antigos ao ligar o recurso)
JANELA_CONCURSOS = 10


def _site_url() -> str:
    return os.environ.get('SITE_URL', 'https://www.calculodasorte.com.br').rstrip('/')


def email_configurado() -> bool:
    return bool(os.environ.get('RESEND_API_KEY') or os.environ.get('SMTP_HOST'))


def enviar_email(destino: str, assunto: str, corpo_html: str, corpo_texto: str) -> bool:
    remetente = os.environ.get('EMAIL_FROM', 'Cálculo da Sorte <avisos@calculodasorte.com.br>')
    try:
        if os.environ.get('RESEND_API_KEY'):
            resposta = requests.post(
                'https://api.resend.com/emails',
                headers={'Authorization': f"Bearer {os.environ['RESEND_API_KEY']}"},
                json={'from': remetente, 'to': [destino], 'subject': assunto, 'html': corpo_html, 'text': corpo_texto},
                timeout=10,
            )
            if resposta.status_code >= 300:
                print(f"[EMAIL] Resend recusou envio para {destino}: {resposta.status_code} {resposta.text[:200]}")
                return False
            return True

        if os.environ.get('SMTP_HOST'):
            msg = EmailMessage()
            msg['From'] = remetente
            msg['To'] = destino
            msg['Subject'] = assunto
            msg.set_content(corpo_texto)
            msg.add_alternative(corpo_html, subtype='html')
            porta = int(os.environ.get('SMTP_PORT', '587'))
            classe = smtplib.SMTP_SSL if porta == 465 else smtplib.SMTP
            with classe(os.environ['SMTP_HOST'], porta, timeout=15) as servidor:
                if porta != 465:
                    servidor.starttls()
                if os.environ.get('SMTP_USER'):
                    servidor.login(os.environ['SMTP_USER'], os.environ.get('SMTP_PASSWORD', ''))
                servidor.send_message(msg)
            return True
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar para {destino}: {e}")
    return False


def _montar_email(nome: str, loteria_type: str, premiadas: List[Dict]) -> Dict[str, str]:
    loteria_nome = LOTERIAS_CONFIG[LoteriaType(loteria_type)].nome
    link = f"{_site_url()}/analise/{loteria_type}"
    link_conta = f"{_site_url()}/minha-conta"
    total = sum(a['resumo']['jogos_premiados'] for a in premiadas)

    itens_html, itens_texto = [], []
    for a in premiadas:
        premios = ', '.join(f"{html.escape(k)}: {v} jogo(s)" for k, v in a['resumo']['premiacoes'].items())
        titulo = html.escape(a.get('titulo') or f'Aposta {loteria_nome}')
        itens_html.append(f"<li><strong>{titulo}</strong> — concurso {a['resumo']['concurso']}: {premios}</li>")
        itens_texto.append(f"- {a.get('titulo') or 'Aposta'} (concurso {a['resumo']['concurso']}): "
                           + ', '.join(f"{k}: {v}" for k, v in a['resumo']['premiacoes'].items()))

    assunto = f"🎉 Você tem {total} jogo(s) premiado(s) na {loteria_nome}!"
    saudacao = html.escape(nome or 'Apostador')
    corpo_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #0A1A3F;">
  <h2 style="color: #209869;">🎉 Parabéns, {saudacao}!</h2>
  <p>A conferência automática encontrou <strong>{total} jogo(s) premiado(s)</strong> entre as apostas que você salvou na {html.escape(loteria_nome)}:</p>
  <ul>{''.join(itens_html)}</ul>
  <p><a href="{link}" style="display: inline-block; background: #0046AD; color: #fff; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold;">Ver meus jogos premiados</a></p>
  <p style="font-size: 13px; color: #5B6B82;">O prêmio só vale se o jogo foi registrado em uma lotérica ou nos canais oficiais da Caixa. Confira o seu bilhete: prêmios prescrevem em 90 dias após o sorteio.</p>
  <hr style="border: none; border-top: 1px solid #e5e7eb;">
  <p style="font-size: 12px; color: #5B6B82;">Você recebe este aviso porque salvou apostas no Cálculo da Sorte. Para não receber mais, desative os avisos em <a href="{link_conta}">Minha Conta</a>. O Cálculo da Sorte não vende apostas.</p>
</div>"""
    corpo_texto = (
        f"Parabéns, {nome or 'Apostador'}!\n\n"
        f"A conferência automática encontrou {total} jogo(s) premiado(s) na {loteria_nome}:\n"
        + "\n".join(itens_texto)
        + f"\n\nVer meus jogos: {link}\n\n"
        "O prêmio só vale se o jogo foi registrado em uma lotérica ou nos canais oficiais da Caixa. "
        "Prêmios prescrevem em 90 dias após o sorteio.\n"
        f"Para não receber mais estes avisos: {link_conta}\n"
    )
    return {'assunto': assunto, 'html': corpo_html, 'texto': corpo_texto}


def notificar_premios(loterias: List[str] = None) -> Dict:
    """Confere apostas já sorteadas e envia um e-mail por usuário com as premiadas.
    Apostas só são marcadas como processadas depois do envio, para nova tentativa se falhar."""
    if not email_configurado():
        return {'enviados': 0, 'motivo': 'envio de e-mail não configurado'}

    enviados, falhas = 0, 0
    for loteria_type in loterias or [l.value for l in LoteriaType]:
        ultimo = updater.carregar_meta(loteria_type).get('ultimo_concurso')
        if not ultimo:
            continue
        apostas = database.apostas_para_notificar(loteria_type, ultimo - JANELA_CONCURSOS, ultimo)
        cache: Dict = {}
        por_usuario: Dict[int, Dict] = {}
        processadas: List[int] = []

        for aposta in apostas:
            resumo = conferencia.resumo_aposta(aposta, cache)
            if resumo['status'] != 'conferido':
                continue
            if resumo['jogos_premiados'] > 0 and aposta['avisos_email'] and aposta.get('email'):
                grupo = por_usuario.setdefault(aposta['user_id'], {'email': aposta['email'], 'nome': aposta['name'], 'apostas': []})
                grupo['apostas'].append({**aposta, 'resumo': resumo})
            else:
                processadas.append(aposta['id'])

        for usuario in por_usuario.values():
            email = _montar_email(usuario['nome'], loteria_type, usuario['apostas'])
            if enviar_email(usuario['email'], email['assunto'], email['html'], email['texto']):
                enviados += 1
                processadas.extend(a['id'] for a in usuario['apostas'])
            else:
                falhas += 1

        database.marcar_apostas_notificadas(processadas)

    return {'enviados': enviados, 'falhas': falhas}
