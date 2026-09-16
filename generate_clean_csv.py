import os
import shutil

# Dados da planilha estruturados com unicode escapes para garantir 100% de integridade dos acentos
header = "Campaign,Campaign Daily Budget,Campaign Type,Campaign Status,Ad Group,Ad Group Status,Keyword,Criterion Type,Max CPC,Headline 1,Headline 2,Headline 3,Headline 4,Headline 5,Description 1,Description 2,Description 3,Final URL,Path 1,Path 2,Campaign Negative Keyword\n"

campaign_name = "[SEARCH] Lotof\u00e1cil da Independ\u00eancia - C\u00e1lculo da Sorte"
budget = "35.00"
c_type = "Search"
c_status = "Paused"

rows = [
    # GRUPO 1: Fechamentos e Bolões
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", '"fechamento lotofacil da independencia"', "Phrase", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", '"desdobramento lotofacil da independencia"', "Phrase", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", '"bolao lotofacil da independencia"', "Phrase", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", '"como montar bolao lotofacil da independencia"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", "[fechamento lotofacil especial]", "Exact", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", "[fechamento lotofacil da independencia]", "Exact", "1.30", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Fechamentos e Bol\u00f5es", "Enabled", "", "", "",
     "Fechamento Lotof\u00e1cil Especial", "Monte Seu Bol\u00e3o com Dados", "Matrizes e Desdobramentos", "Otimize Jogos para Hoje", "C\u00e1lculo da Sorte Oficial",
     "N\u00e3o jogue n\u00fameros aleat\u00f3rios. Otimize seu bol\u00e3o com matrizes matem\u00e1ticas e estat\u00edsticas.",
     "Economize bilhetes com fechamentos inteligentes para a Lotof\u00e1cil da Independ\u00eancia. Acesse!",
     "O pr\u00eamio n\u00e3o acumula! Crie combina\u00e7\u00f5es balanceadas com base na ci\u00eancia combinat\u00f3ria.",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=lotofacil_independencia&utm_adgroup=fechamentos",
     "lotofacil", "especial", ""],

    # GRUPO 2: Palpites com IA e Gerador
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", '"palpites lotofacil da independencia"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", '"gerador lotofacil da independencia"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", '"palpite com inteligencia artificial"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", '"ia para lotofacil da independencia"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", "[gerador inteligente lotofacil]", "Exact", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", "[palpites lotofacil da independencia]", "Exact", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Palpites com IA e Gerador", "Enabled", "", "", "",
     "Palpites com IA: Independ\u00eancia", "Gerador Inteligente de Jogos", "IA para Lotof\u00e1cil Especial", "Palpites Estruturados Hoje", "Simulador Lotof\u00e1cil da Caixa",
     "Gere fechamentos combinat\u00f3rios e palpites com IA para o sorteio especial. Teste gr\u00e1tis!",
     "Tire d\u00favidas e consulte matrizes com nosso agente de Intelig\u00eancia Artificial treinado.",
     "Pare de apostar no escuro. Gere jogos equilibrados em paridade e moldura em segundos.",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=lotofacil_independencia&utm_adgroup=palpites_ia",
     "lotofacil", "palpites", ""],

    # GRUPO 3: Números Mais Sorteados e Estatísticas
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", '"numeros mais sorteados lotofacil da independencia"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", '"dezenas que mais saem lotofacil da independencia"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", '"estatisticas lotofacil da independencia"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", "[numeros que mais saem lotofacil independencia]", "Exact", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", "[estatisticas da lotofacil da independencia]", "Exact", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. N\u00fameros Mais Sorteados e Estat\u00edsticas", "Enabled", "", "", "",
     "Dezenas Mais Sorteadas", "Estat\u00edsticas da Independ\u00eancia", "Padr\u00f5es e Frequ\u00eancia 2026", "An\u00e1lise Estat\u00edstica Avan\u00e7ada", "Lotof\u00e1cil da Independ\u00eancia",
     "Descubra as dezenas mais sorteadas e padr\u00f5es hist\u00f3ricos da Lotof\u00e1cil da Independ\u00eancia.",
     "Analise frequ\u00eancia, moldura e paridade de todos os concursos da Independ\u00eancia. Confira!",
     "Estudo completo dos dados oficiais da Caixa pelo Modelo Can\u00f4nico. Fa\u00e7a sua simula\u00e7\u00e3o!",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=lotofacil_independencia&utm_adgroup=estatisticas",
     "lotofacil", "estatisticas", ""],

    # Palavras-chave negativas
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado de hoje"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "ganhadores"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "deu quem"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "premia\u00e7\u00e3o"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "ao vivo"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "transmiss\u00e3o"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "gabarito"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "download"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "pdf gratis"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "como burlar"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "esquema"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "hack"]
]

content_lines = [header]
for row in rows:
    # Se algum item contiver vírgula e não estiver entre aspas, adiciona aspas
    formatted_row = []
    for cell in row:
        if "," in cell and not cell.startswith('"') and not cell.startswith('['):
            formatted_row.append(f'"{cell}"')
        else:
            formatted_row.append(cell)
    content_lines.append(",".join(formatted_row) + "\n")

full_content = "".join(content_lines)

# 1. Salvar no projeto como UTF-8 com BOM (ideal para Windows / Excel / Google Ads Editor)
with open("google_ads_lotofacil_independencia.csv", "w", encoding="utf-8-sig", newline="\r\n") as f:
    f.write(full_content)

# 2. Salvar no projeto como UTF-8 puro (sem BOM)
with open("google_ads_lotofacil_independencia_utf8.csv", "w", encoding="utf-8", newline="\n") as f:
    f.write(full_content)

# 3. Salvar também na pasta Downloads
dl_path_sig = r"C:\Users\sptox\Downloads\google_ads_lotofacil_independencia.csv"
dl_path_utf8 = r"C:\Users\sptox\Downloads\google_ads_lotofacil_independencia_utf8.csv"

shutil.copyfile("google_ads_lotofacil_independencia.csv", dl_path_sig)
shutil.copyfile("google_ads_lotofacil_independencia_utf8.csv", dl_path_utf8)

print("Arquivos gerados com sucesso com codificacao UTF-8 garantida!")
