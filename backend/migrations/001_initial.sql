-- ============================================
-- IA E-COMMERCE: Migração Inicial
-- ============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Produtos
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    sku VARCHAR(100) UNIQUE NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2) NOT NULL,
    min_price DECIMAL(10,2) NOT NULL,
    max_price DECIMAL(10,2),
    min_margin_pct DECIMAL(5,2) NOT NULL DEFAULT 15.0,
    target_margin_pct DECIMAL(5,2) NOT NULL DEFAULT 25.0,
    category VARCHAR(200),
    brand VARCHAR(200),
    keywords TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Anúncios nos marketplaces
CREATE TABLE IF NOT EXISTS product_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    marketplace VARCHAR(50) NOT NULL,
    listing_id VARCHAR(200) NOT NULL,
    listing_url TEXT,
    current_price DECIMAL(10,2) NOT NULL,
    listing_type VARCHAR(50),
    free_shipping BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    marketplace_fee_pct DECIMAL(5,2),
    avg_shipping_cost DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(marketplace, listing_id)
);

-- Concorrentes monitorados
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    marketplace VARCHAR(50) NOT NULL,
    competitor_listing_id VARCHAR(200),
    competitor_seller VARCHAR(200),
    competitor_name VARCHAR(500),
    last_price DECIMAL(10,2),
    last_seen_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Histórico de preços dos concorrentes
CREATE TABLE IF NOT EXISTS competitor_price_history (
    id BIGSERIAL PRIMARY KEY,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    marketplace VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    free_shipping BOOLEAN,
    seller_name VARCHAR(200),
    position_in_search INTEGER,
    collected_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comp_price_hist_product ON competitor_price_history(product_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_comp_price_hist_competitor ON competitor_price_history(competitor_id, collected_at DESC);

-- Campanhas de ads
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    campaign_id VARCHAR(200) NOT NULL,
    campaign_name VARCHAR(500),
    campaign_type VARCHAR(50),
    daily_budget DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, campaign_id)
);

-- Performance de ads (métricas diárias)
CREATE TABLE IF NOT EXISTS ad_performance (
    id BIGSERIAL PRIMARY KEY,
    campaign_id UUID REFERENCES ad_campaigns(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    spend DECIMAL(10,2) DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue DECIMAL(10,2) DEFAULT 0,
    cpc DECIMAL(10,4),
    ctr DECIMAL(8,4),
    conversion_rate DECIMAL(8,4),
    acos DECIMAL(8,4),
    roas DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ad_perf_product_date ON ad_performance(product_id, date DESC);

-- Snapshots de margem
CREATE TABLE IF NOT EXISTS margin_snapshots (
    id BIGSERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    sale_price DECIMAL(10,2),
    cost DECIMAL(10,2),
    marketplace_fee DECIMAL(10,2),
    shipping_cost DECIMAL(10,2),
    ad_cost_per_sale DECIMAL(10,2),
    net_profit DECIMAL(10,2),
    margin_pct DECIMAL(8,4),
    health_status VARCHAR(20),
    calculated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_margin_snap_product ON margin_snapshots(product_id, calculated_at DESC);

-- Decisões da IA
CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    decision_type VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_value DECIMAL(10,2),
    new_value DECIMAL(10,2),
    reason TEXT,
    confidence DECIMAL(5,4),
    context JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_product ON ai_decisions(product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_status ON ai_decisions(status);

-- Configurações do sistema
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configurações padrão
INSERT INTO system_config (key, value, description) VALUES
    ('global_min_margin_pct', '10', 'Margem mínima absoluta (%)'),
    ('global_target_margin_pct', '25', 'Margem alvo (%)'),
    ('global_alert_margin_pct', '15', 'Margem de alerta (%)'),
    ('max_acos', '30', 'ACOS máximo antes de reduzir lance (%)'),
    ('monitoring_interval_minutes', '30', 'Intervalo entre ciclos de monitoramento'),
    ('auto_execute', 'false', 'Se true, executa decisões sem aprovação manual'),
    ('max_price_change_pct', '10', 'Máximo ajuste de preço por ciclo (%)')
ON CONFLICT (key) DO NOTHING;
