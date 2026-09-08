# Guia de Testes e Deploy - Loteria Canônica

## 🚀 Como Testar Localmente

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Rodar o Servidor
```bash
python app.py
```

### 3. Acessar no Navegador
- **URL:** http://localhost:5000
- **API:** http://localhost:5000/api/loterias

---

## 📡 Testar API com cURL

### Listar todas as loterias
```bash
curl http://localhost:5000/api/loterias
```

### Carregar histórico (se existir)
```bash
curl http://localhost:5000/api/carregar-historico/mega-sena
```

### Realizar análise estatística completa
```bash
curl -X POST http://localhost:5000/api/analise/mega-sena \
  -H "Content-Type: application/json" \
  -d '{"historico": [[1,2,3,4,5,6], [7,8,9,10,11,12], ...]}'
```

### Gerar sugestão de jogo
```bash
curl -X POST http://localhost:5000/gerar-jogo/mega-sena \
  -H "Content-Type: application/json" \
  -d '{"quantidade": 6}'
```

### Comparar concurso com padrões históricos
```bash
curl -X POST http://localhost:5000/comparar-concursos/mega-sena \
  -H "Content-Type: application/json" \
  -d '{"concurso": [1,2,3,4,5,6], "historico": [...]}'
```

---

## 🌐 Deploy na Vercel

### Pré-requisitos
1. Conta na Vercel (https://vercel.com)
2. Vercel CLI instalada: `npm i -g vercel`

### Passo a Passo

#### 1. Login na Vercel
```bash
vercel login
```

#### 2. Deploy
```bash
cd /workspace
vercel --prod
```

#### 3. Configurações Adicionais (se necessário)
- No dashboard da Vercel, adicione variáveis de ambiente se precisar
- O arquivo `vercel.json` já está configurado para Flask

### Estrutura do Deploy
```
/workspace/
├── app.py              # Aplicação Flask (entry point)
├── core.py             # Núcleo matemático
├── requirements.txt    # Dependências Python
├── vercel.json         # Configuração Vercel
├── templates/          # Templates HTML
│   ├── index.html
│   └── analise.html
└── data/               # Dados persistentes (JSON)
```

---

## 🧪 Testes Automatizados

### Teste Unitário do Core
```bash
python -c "from core import *; print('Core OK')"
```

### Teste de Importação Flask
```bash
python -c "from app import app; print('Flask OK')"
```

### Teste de Todas as Loterias
```bash
python -c "
from core import LOTERIAS_CONFIG, ModeloCanonico30
for loteria, config in LOTERIAS_CONFIG.items():
    print(f'✓ {loteria.value}: {config.minimo_aposta}-{config.maximo_aposta} números')
print('Todas as 9 loterias carregadas com sucesso!')
"
```

---

## 📊 Exemplo de Dados para Teste

### Mega-Sena (6 números, 1-60)
```json
{
  "historico": [
    [5, 18, 23, 31, 42, 55],
    [10, 15, 28, 33, 47, 59],
    [3, 12, 25, 38, 44, 51],
    [8, 19, 27, 35, 49, 58],
    [1, 14, 22, 36, 41, 53],
    [7, 16, 29, 32, 45, 56],
    [11, 20, 24, 39, 48, 54],
    [2, 13, 26, 34, 43, 52],
    [6, 17, 21, 37, 46, 57],
    [4, 9, 30, 40, 50, 60]
  ]
}
```

### Lotofácil (15 números, 1-25)
```json
{
  "historico": [
    [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
    [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],
    [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],
    [4,5,6,7,8,9,10,11,12,13,14,15,16,17,18],
    [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],
    [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
    [7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
    [8,9,10,11,12,13,14,15,16,17,18,19,20,21,22],
    [9,10,11,12,13,14,15,16,17,18,19,20,21,22,23],
    [10,11,12,13,14,15,16,17,18,19,20,21,22,23,24]
  ]
}
```

---

## 🔍 Endpoints da API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Página inicial |
| `/analise/<loteria>` | GET | Página de análise |
| `/api/loterias` | GET | Lista todas as loterias |
| `/api/analise/<loteria>` | POST | Análise estatística completa |
| `/api/salvar-historico/<loteria>` | POST | Salvar histórico |
| `/api/carregar-historico/<loteria>` | GET | Carregar histórico |
| `/gerar-jogo/<loteria>` | POST | Gerar sugestão de jogo |
| `/comparar-concursos/<loteria>` | POST | Comparar concurso |

---

## ⚠️ Importante

- **Mínimo de 10 concursos** necessários para análise
- Dados são salvos em `data/<loteria>_historico.json`
- Sistema não promete resultados - segue rigor científico do Modelo Canônico
- Ausência de padrão detectável é um resultado válido

---

## 🎯 Próximos Passos

1. **Importar dados reais** das loterias (site da Caixa)
2. **Configurar domínio customizado** na Vercel
3. **Adicionar autenticação** para usuários premium
4. **Implementar cache** para análises frequentes
5. **Adicionar gráficos** com Chart.js ou D3.js
