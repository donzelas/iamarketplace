# IA E-commerce — Análise Competitiva & Gestão Automatizada

Sistema de inteligência artificial para monitoramento de concorrentes em múltiplos marketplaces, controle de margem e gestão automatizada de anúncios.

## O que o sistema faz

- **Monitora concorrentes** em tempo real (preços, posição, frete) em Mercado Livre, Shopee, Amazon e Magalu
- **Calcula margens** considerando todos os custos (produto, taxa, frete, ads)
- **Analisa performance de ads** em Google Ads, Meta Ads, TikTok Ads, Mercado Ads e Shopee Ads
- **Toma decisões inteligentes** com IA (GPT-4o/Claude): ajustar preço, alterar lance, pausar campanhas
- **Protege sua lucratividade** com 3 camadas de segurança (regras fixas → IA → validação)

## Arquitetura

```
Dashboard (Next.js) → API (FastAPI) → Módulos:
├── Collectors   → Coleta de dados dos marketplaces
├── Ads          → Integração com plataformas de ads
├── Analysis     → Análise de mercado e cálculo de margem
├── Engine       → Motor de decisão (Regras + LLM)
├── Executor     → Execução de ações nos marketplaces
└── Margin       → Controle e monitoramento de margem
```

## Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.12+ / FastAPI |
| Tarefas | Celery + Redis |
| Banco de Dados | PostgreSQL |
| IA | OpenAI GPT-4o / Anthropic Claude |
| Scraping | Playwright + httpx |
| Frontend | Next.js + Tailwind CSS |
| Deploy | Docker Compose |

## Início Rápido

### 1. Clone o repositório

```bash
git clone https://github.com/donzelas/iamarketplace.git
cd iamarketplace
```

### 2. Configure as credenciais

```bash
cp backend/.env.example backend/.env
# Edite backend/.env com suas credenciais
```

### 3. Suba com Docker

```bash
docker compose up -d
```

A API estará em `http://localhost:8000` e a documentação em `http://localhost:8000/docs`.

### 4. Sem Docker (desenvolvimento local)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
playwright install chromium

# Inicie o servidor
uvicorn app.main:app --reload

# Em outro terminal, inicie o Celery Worker
celery -A app.tasks.celery_app worker -l info

# Em outro terminal, inicie o Celery Beat (agendador)
celery -A app.tasks.celery_app beat -l info
```

## Estrutura do Projeto

```
iamarketplace/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configurações
│   │   ├── database.py          # Conexão DB
│   │   ├── collectors/          # Coletores de marketplace
│   │   │   ├── mercadolivre.py
│   │   │   ├── shopee.py
│   │   │   ├── amazon.py
│   │   │   ├── magalu.py
│   │   │   ├── scraper.py       # Scraping com Playwright
│   │   │   └── orchestrator.py  # Orquestrador unificado
│   │   ├── ads/                 # Plataformas de ads
│   │   │   ├── google_ads.py
│   │   │   ├── meta_ads.py
│   │   │   ├── tiktok_ads.py
│   │   │   ├── mercado_ads.py
│   │   │   └── shopee_ads.py
│   │   ├── analysis/            # Análise de mercado
│   │   │   ├── market_analyzer.py
│   │   │   └── margin_calculator.py
│   │   ├── engine/              # Motor de decisão IA
│   │   │   ├── decision_engine.py
│   │   │   ├── rules.py         # Regras de segurança
│   │   │   └── prompts.py       # Prompts do LLM
│   │   ├── executor/            # Execução de ações
│   │   │   └── action_executor.py
│   │   ├── margin/              # Controle de margem
│   │   │   └── margin_controller.py
│   │   ├── api/                 # Rotas da API
│   │   │   ├── products.py
│   │   │   ├── competitors.py
│   │   │   ├── ads.py
│   │   │   ├── decisions.py
│   │   │   └── dashboard.py
│   │   ├── models/              # Modelos SQLAlchemy
│   │   ├── schemas/             # Schemas Pydantic
│   │   └── tasks/               # Tarefas Celery
│   ├── migrations/              # SQL de migração
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                    # Dashboard (Next.js)
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Produtos
- `GET /api/products/` — Lista produtos
- `POST /api/products/` — Cria produto
- `GET /api/products/{id}` — Detalhes do produto
- `PATCH /api/products/{id}` — Atualiza produto
- `GET /api/products/{id}/listings` — Anúncios do produto

### Concorrentes
- `GET /api/competitors/{product_id}` — Lista concorrentes
- `GET /api/competitors/{product_id}/price-history` — Histórico de preços

### Ads
- `GET /api/ads/campaigns` — Lista campanhas
- `POST /api/ads/campaigns` — Cria campanha
- `GET /api/ads/performance/{product_id}` — Performance de ads

### Decisões da IA
- `GET /api/decisions/` — Lista decisões
- `GET /api/decisions/pending` — Decisões pendentes
- `POST /api/decisions/{id}/approve` — Aprovar decisão
- `POST /api/decisions/{id}/reject` — Rejeitar decisão

### Dashboard
- `GET /api/dashboard/overview` — Visão geral
- `GET /api/dashboard/product/{id}/analysis` — Análise completa
- `GET /api/dashboard/product/{id}/margin-history` — Histórico de margem

## Camadas de Segurança

O motor de decisão opera em **3 camadas**:

1. **Regras Fixas** — Verificações automáticas que NUNCA são violadas:
   - Margem negativa → emergência, subir preço imediatamente
   - Margem abaixo do mínimo → subir preço
   - ACOS extremo → pausar ads
   - ACOS alto → reduzir lance

2. **IA (LLM)** — Analisa todo o contexto e sugere ações inteligentes

3. **Validação** — Antes de executar, valida:
   - Preço dentro dos limites (min/max)
   - Ajuste máximo por ciclo (10%)
   - Margem simulada não fica abaixo do mínimo

## Credenciais Necessárias

| Plataforma | Como Obter |
|---|---|
| Mercado Livre | [developers.mercadolibre.com.ar](https://developers.mercadolibre.com.ar) |
| Shopee | [open.shopee.com](https://open.shopee.com) |
| Amazon | [sellercentral.amazon.com.br](https://sellercentral.amazon.com.br) (Developer) |
| Magalu | [dev.magalu.com](https://dev.magalu.com) |
| Google Ads | [ads.google.com/api](https://ads.google.com/api) |
| Meta Ads | [developers.facebook.com](https://developers.facebook.com) |
| TikTok Ads | [business-api.tiktok.com](https://business-api.tiktok.com) |
| OpenAI | [platform.openai.com](https://platform.openai.com) |

## Licença

Projeto privado. Todos os direitos reservados.
