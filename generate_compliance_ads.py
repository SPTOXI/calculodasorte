import os
import shutil

header = "Campaign,Campaign Daily Budget,Campaign Type,Campaign Status,Ad Group,Ad Group Status,Keyword,Criterion Type,Max CPC,Headline 1,Headline 2,Headline 3,Headline 4,Headline 5,Description 1,Description 2,Description 3,Final URL,Path 1,Path 2,Campaign Negative Keyword\n"

campaign_name = "[SEARCH] C\u00e1lculo da Sorte - An\u00e1lise Estat\u00edstica e IA"
budget = "35.00"
c_type = "Search"
c_status = "Paused"

rows = [
    # =========================================================================
    # ANÚNCIO 1: Inteligência Artificial & Ciência de Dados (Compliance Total)
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", '"inteligencia artificial loterias"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", '"ia para loterias"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", '"analise estatistica loterias"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", '"software de analise loterica"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", "[ia para lotofacil]", "Exact", "1.20", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", "[simulador estatistico loterias]", "Exact", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "1. Inteligencia Artificial Loterias", "Enabled", "", "", "",
     "IA para An\u00e1lise Lot\u00e9rica", "Intelig\u00eancia Artificial Caixa", "C\u00e1lculo da Sorte Oficial", "An\u00e1lise de Dados com IA", "Simulador Estat\u00edstico 2026",
     "Analise os padr\u00f5es hist\u00f3ricos das 9 loterias oficiais com Intelig\u00eancia Artificial. Acesse!",
     "Descubra tend\u00eancias num\u00e9ricas e frequ\u00eancias reais com nosso algoritmo avan\u00e7ado. Teste j\u00e1!",
     "Software de ci\u00eancia de dados e an\u00e1lise combinat\u00f3ria para confer\u00eancia de n\u00fameros. Conhe\u00e7a!",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=compliance_ia&utm_adgroup=inteligencia_artificial",
     "software", "inteligencia", ""],

    # =========================================================================
    # ANÚNCIO 2: Estatísticas & Frequência de Dezenas (Compliance Total)
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", '"dezenas mais sorteadas"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", '"numeros mais sorteados da mega sena"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", '"dezenas que mais saem na lotofacil"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", '"estatisticas loterias caixa"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", "[numeros mais sorteados lotofacil]", "Exact", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "2. Estatisticas e Frequencia de Numeros", "Enabled", "", "", "",
     "Dezenas Mais Sorteadas", "Estat\u00edsticas da Mega-Sena", "Frequ\u00eancia de N\u00fameros Caixa", "Padr\u00f5es e M\u00e9dias Hist\u00f3ricas", "Dados Oficiais Atualizados",
     "Acesse o hist\u00f3rico completo de sorteios da Caixa com gr\u00e1ficos de frequ\u00eancia e paridade.",
     "Descubra quais dezenas possuem maior recorr\u00eancia hist\u00f3rica pelo Modelo Can\u00f4nico. Confira!",
     "Base de dados sincronizada diariamente com os resultados oficiais da Caixa. Simule gr\u00e1tis!",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=compliance_stats&utm_adgroup=estatisticas_frequencia",
     "estatisticas", "frequencia", ""],

    # =========================================================================
    # ANÚNCIO 3: Fechamentos Combinatórios & Redução Matemática (Compliance Total)
    # =========================================================================
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", '"fechamentos combinatorios"', "Phrase", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", '"desdobramento matematico"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", '"matrizes combinatorias"', "Phrase", "0.90", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", '"simulador de combinacoes"', "Phrase", "1.00", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", "[fechamento combinatorio matematico]", "Exact", "1.10", "", "", "", "", "", "", "", "", "", "", "", ""],
    [campaign_name, budget, c_type, c_status, "3. Fechamentos Combinatorios", "Enabled", "", "", "",
     "Fechamentos Combinat\u00f3rios", "Matrizes e Desdobramentos", "Simulador de Combina\u00e7\u00f5es", "Economia Combinat\u00f3ria Real", "Modelagem Matem\u00e1tica Caixa",
     "Gere matrizes matem\u00e1ticas balanceadas e reduza combina\u00e7\u00f5es repetidas em segundos. Teste!",
     "Organize suas dezenas favoritas com sistemas de fechamento ortogonal e filtros l\u00f3gicos.",
     "Elimine sequ\u00eancias improv\u00e1veis com an\u00e1lise combinat\u00f3ria avan\u00e7ada. Acesse a plataforma!",
     "https://calculodasorte.com.br/?utm_source=google&utm_medium=cpc&utm_campaign=compliance_fechamentos&utm_adgroup=matrizes_combinatorias",
     "matrizes", "fechamentos", ""],

    # =========================================================================
    # Palavras-chave negativas
    # =========================================================================
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "aposta online"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "cassino"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "bet"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "resultado de ontem"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "ganhadores"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "ao vivo"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "download"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "hack"],
    [campaign_name, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "como burlar"]
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
with open("google_ads_compliance_sem_aposta.csv", "w", encoding="utf-8-sig", newline="\r\n") as f:
    f.write(full_content)

with open("google_ads_compliance_sem_aposta_utf8.csv", "w", encoding="utf-8", newline="\n") as f:
    f.write(full_content)

# Copiar para Downloads
shutil.copyfile("google_ads_compliance_sem_aposta.csv", r"C:\Users\sptox\Downloads\google_ads_compliance_sem_aposta.csv")
shutil.copyfile("google_ads_compliance_sem_aposta_utf8.csv", r"C:\Users\sptox\Downloads\google_ads_compliance_sem_aposta_utf8.csv")

print("Campanha 100% compliant gerada com sucesso e salva em Downloads!")
