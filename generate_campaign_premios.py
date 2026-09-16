import os
import shutil

header = "Campaign,Campaign Daily Budget,Campaign Type,Campaign Status,Ad Group,Ad Group Status,Keyword,Criterion Type,Max CPC,Headline 1,Headline 2,Headline 3,Headline 4,Headline 5,Description 1,Description 2,Description 3,Final URL,Path 1,Path 2,Campaign Negative Keyword\n"

campaign_name = "[SEARCH] Loterias Acumuladas - Mega 102M e Milion\u00e1ria 95M"
budget = "40.00"
c_type = "Search"
c_status = "Paused"

rows = [
    # =========================================================================
    # GRUPO 1: Mega-Sena R$ 102 Milhões
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", '"mega sena 102 milhoes"', "Phrase", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", '"mega sena acumulada"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", '"palpites mega sena acumulada"', "Phrase", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", '"fechamento mega sena"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", '"estatisticas mega sena acumulada"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", "[mega sena 102 milhoes]", "Exact", "1.30", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", "[palpites mega sena]", "Exact", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Mega-Sena R$ 102 Milh\u00f5es", "Enabled", "", "", "",
     "Mega-Sena R$ 102 Milh\u00f5es", "Mega Acumulada: Palpites", "Fechamentos Mega-Sena", "Estat\u00edsticas da Mega-Sena", "C\u00e1lculo da Sorte Oficial",
     "Mega-Sena acumulou em R$ 102 Milh\u00f5es! Gere fechamentos e palpites com IA agora mesmo.",
     "N\u00e3o jogue no escuro. Analise padr\u00f5es e frequ\u00eancias hist\u00f3ricas da Mega-Sena acumulada.",
     "Fa\u00e7a seu jogo com combina\u00e7\u00f5es estruturadas pelo Modelo Can\u00f4nico. Teste gr\u00e1tis hoje!",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=mega_102m&utm_adgroup=mega_acumulada",
     "megasena", "102milhoes", ""],

    # =========================================================================
    # GRUPO 2: +Milionária R$ 95 Milhões
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", '"+milionaria 95 milhoes"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", '"mais milionaria acumulada"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", '"palpites mais milionaria"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", '"fechamento mais milionaria"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", '"gerador mais milionaria"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", "[mais milionaria 95 milhoes]", "Exact", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. +Milion\u00e1ria R$ 95 Milh\u00f5es", "Enabled", "", "", "",
     "+Milion\u00e1ria R$ 95 Milh\u00f5es", "Palpites +Milion\u00e1ria com IA", "Fechamento +Milion\u00e1ria", "Estat\u00edsticas +Milion\u00e1ria", "Simulador +Milion\u00e1ria",
     "+Milion\u00e1ria acumulada em R$ 95 Milh\u00f5es! Gere combina\u00e7\u00f5es com n\u00fameros e trevos pela IA.",
     "Aumente a efici\u00eancia dos seus bilhetes na +Milion\u00e1ria com fechamentos combinat\u00f3rios.",
     "Acesse an\u00e1lises detalhadas de recorr\u00eancia dos trevos e dezenas da +Milion\u00e1ria da Caixa.",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=milionaria_95m&utm_adgroup=milionaria_acumulada",
     "milionaria", "95milhoes", ""],

    # =========================================================================
    # GRUPO 3: 5 Loterias Acumuladas (Timemania 14M, Super Sete 8M, Dupla Sena 4M)
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", '"loterias acumuladas hoje"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", '"timemania acumulada"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", '"super sete acumulada"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", '"dupla sena acumulada"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", '"palpites loterias acumuladas"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", "[loterias acumuladas hoje]", "Exact", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Loterias Acumuladas Caixa", "Enabled", "", "", "",
     "5 Loterias Acumuladas Hoje", "Timemania R$ 14,3 Milh\u00f5es", "Super Sete R$ 8,1 Milh\u00f5es", "Dupla Sena R$ 4,1 Milh\u00f5es", "Palpites Inteligentes Caixa",
     "Mega 102M, Milion\u00e1ria 95M, Timemania 14M e Super Sete 8M acumuladas! Analise com IA.",
     "Mais de R$ 223 Milh\u00f5es em pr\u00eamios acumulados nas loterias da Caixa. Gere seus jogos!",
     "Pare de gastar \u00e0 toa. Utilize matrizes combinat\u00f3rias e economize nos seus volantes.",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=loterias_acumuladas&utm_adgroup=premios_acumulados",
     "loterias", "acumuladas", ""],

    # =========================================================================
    # Palavras-chave negativas
    # =========================================================================
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado de hoje"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado da mega sena de ontem"],
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
    formatted_row = []
    for cell in row:
        if "," in cell and not cell.startswith('"') and not cell.startswith('['):
            formatted_row.append(f'"{cell}"')
        else:
            formatted_row.append(cell)
    content_lines.append(",".join(formatted_row) + "\n")

full_content = "".join(content_lines)

# Salvar no projeto (UTF-8 com BOM e UTF-8 puro)
with open("google_ads_premios_acumulados.csv", "w", encoding="utf-8-sig", newline="\r\n") as f:
    f.write(full_content)

with open("google_ads_premios_acumulados_utf8.csv", "w", encoding="utf-8", newline="\n") as f:
    f.write(full_content)

# Copiar para Downloads
shutil.copyfile("google_ads_premios_acumulados.csv", r"C:\Users\sptox\Downloads\google_ads_premios_acumulados.csv")
shutil.copyfile("google_ads_premios_acumulados_utf8.csv", r"C:\Users\sptox\Downloads\google_ads_premios_acumulados_utf8.csv")

print("Nova campanha gerada com sucesso e salva em Downloads!")
