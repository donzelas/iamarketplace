"use client";

import { useEffect, useState, useCallback } from "react";
import { api, DashboardOverview, Decision, Marketplace } from "@/lib/api";
import { Package, DollarSign, TrendingUp, Brain, Layers, ShoppingCart, Users, Megaphone } from "lucide-react";

const MARKETPLACE_ICONS: Record<string, string> = {
  mercadolivre: "/ml.svg",
  shopee: "/shopee.svg",
  amazon: "/amazon.svg",
  magalu: "/magalu.svg",
};

const MARKETPLACE_COLORS: Record<string, { bg: string; border: string; text: string; activeBg: string }> = {
  mercadolivre: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "text-yellow-400", activeBg: "bg-yellow-500/20" },
  shopee: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", activeBg: "bg-orange-500/20" },
  amazon: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", activeBg: "bg-blue-500/20" },
  magalu: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", activeBg: "bg-purple-500/20" },
};

export default function DashboardPage() {
  const [marketplaces, setMarketplaces] = useState<Marketplace[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [pending, setPending] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.dashboard.marketplaces().then(setMarketplaces).catch(() => {});
  }, []);

  const loadDashboard = useCallback((marketplace?: string) => {
    setLoading(true);
    Promise.all([
      api.dashboard.overview(marketplace || undefined),
      api.decisions.pending(),
    ])
      .then(([ov, pd]) => { setOverview(ov); setPending(pd); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadDashboard(selected || undefined);
  }, [selected, loadDashboard]);

  const handleSelect = (id: string) => {
    setSelected(selected === id ? null : id);
  };

  const allMarketplaces: Marketplace[] = [
    ...marketplaces,
    ...["shopee", "amazon", "magalu"]
      .filter((id) => !marketplaces.find((m) => m.id === id))
      .map((id) => ({
        id,
        name: id === "shopee" ? "Shopee" : id === "amazon" ? "Amazon" : "Magalu",
        listings: 0,
        products: 0,
        connected: false,
      })),
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Platform Selector */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {allMarketplaces.map((mp) => {
          const isActive = selected === mp.id;
          const colors = MARKETPLACE_COLORS[mp.id] || MARKETPLACE_COLORS.mercadolivre;
          return (
            <button
              key={mp.id}
              onClick={() => mp.connected && handleSelect(mp.id)}
              disabled={!mp.connected}
              className={`relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${
                isActive
                  ? `${colors.activeBg} ${colors.border} ring-2 ring-offset-0 ring-${mp.id === "mercadolivre" ? "yellow" : mp.id === "shopee" ? "orange" : mp.id === "amazon" ? "blue" : "purple"}-500/40`
                  : mp.connected
                    ? `${colors.bg} ${colors.border} hover:scale-[1.02] cursor-pointer`
                    : "bg-white/5 border-white/10 opacity-50 cursor-not-allowed"
              }`}
            >
              {mp.connected && (
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-green-400" />
              )}
              {!mp.connected && (
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-gray-500" />
              )}
              <span className={`text-lg font-bold ${mp.connected ? colors.text : "text-gray-500"}`}>
                {mp.name}
              </span>
              {mp.connected ? (
                <div className="flex gap-3 text-xs text-gray-400">
                  <span>{mp.products} produtos</span>
                  <span>{mp.listings} anúncios</span>
                </div>
              ) : (
                <span className="text-xs text-gray-500">Não conectado</span>
              )}
              {isActive && (
                <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Selecionado</span>
              )}
            </button>
          );
        })}
      </div>

      {selected === null && (
        <p className="text-sm text-gray-500 text-center">Mostrando dados de todas as plataformas. Clique em uma para filtrar.</p>
      )}

      {loading ? (
        <LoadingSkeleton />
      ) : overview ? (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <MiniStat icon={<Package className="w-4 h-4" />} label="Produtos" value={overview.products?.active ?? 0} sub={`${overview.products?.paused ?? 0} pausados`} color="text-indigo-400" />
            <MiniStat icon={<ShoppingCart className="w-4 h-4" />} label="Anúncios" value={overview.listings?.active ?? 0} sub={`${overview.listings?.paused ?? 0} inativos`} color="text-cyan-400" />
            <MiniStat icon={<DollarSign className="w-4 h-4" />} label="Valor Ativo" value={`R$ ${((overview.financials?.total_value ?? 0) / 1000).toFixed(1)}k`} sub={`Custo: R$ ${((overview.financials?.total_cost ?? 0) / 1000).toFixed(1)}k`} color="text-yellow-400" />
            <MiniStat icon={<TrendingUp className="w-4 h-4" />} label="Margem Média" value={`${(overview.financials?.avg_margin ?? 0).toFixed(1)}%`} sub="sobre preço" color={(overview.financials?.avg_margin ?? 0) >= 25 ? "text-green-400" : (overview.financials?.avg_margin ?? 0) >= 15 ? "text-yellow-400" : "text-red-400"} />
            <MiniStat icon={<Users className="w-4 h-4" />} label="Concorrentes" value={overview.competitors_count ?? 0} sub="monitorados" color="text-orange-400" />
            <MiniStat icon={<Brain className="w-4 h-4" />} label="Decisões IA" value={overview.pending_decisions ?? 0} sub="pendentes" color={(overview.pending_decisions ?? 0) > 0 ? "text-red-400" : "text-green-400"} />
          </div>

          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Margin Health */}
            <Card title="Saúde das Margens">
              <div className="space-y-4 py-2">
                <MarginBar label="Saudável" count={overview.margin_health?.healthy ?? 0} total={overview.products?.active ?? 0} color="bg-green-500" textColor="text-green-400" />
                <MarginBar label="Atenção" count={overview.margin_health?.warning ?? 0} total={overview.products?.active ?? 0} color="bg-yellow-500" textColor="text-yellow-400" />
                <MarginBar label="Crítico" count={overview.margin_health?.critical ?? 0} total={overview.products?.active ?? 0} color="bg-red-500" textColor="text-red-400" />
              </div>
              <p className="text-xs text-gray-600 mt-3">Custo estimado em 40% do preço. Ajuste para precisão.</p>
            </Card>

            {/* Top Products */}
            <Card title="Top Produtos por Preço" className="lg:col-span-2">
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {overview.top_products.map((p) => (
                  <div key={p.id} className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 hover:bg-white/10 transition cursor-pointer" onClick={() => window.location.href = `/products/${p.id}`}>
                    <div className="flex-1 min-w-0 mr-4">
                      <p className="text-sm text-white truncate">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.sku}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-bold text-white">R$ {p.price.toFixed(2)}</p>
                      <span className={`text-xs ${p.margin >= 25 ? "text-green-400" : p.margin >= 12 ? "text-yellow-400" : "text-red-400"}`}>
                        {p.margin.toFixed(0)}% margem
                      </span>
                    </div>
                  </div>
                ))}
                {overview.top_products.length === 0 && (
                  <p className="text-center text-gray-500 py-6">Nenhum produto ativo</p>
                )}
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Categories */}
            <Card title="Categorias">
              <div className="space-y-3">
                {overview.categories.map((cat) => (
                  <div key={cat.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Layers className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span className="text-sm text-gray-300 truncate">{cat.name}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="w-20 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(cat.count / (overview.products?.active || 1)) * 100}%` }} />
                      </div>
                      <span className="text-xs text-gray-400 w-6 text-right">{cat.count}</span>
                    </div>
                  </div>
                ))}
                {overview.categories.length === 0 && (
                  <p className="text-center text-gray-500 py-4">Sem dados de categorias</p>
                )}
              </div>
            </Card>

            {/* Pending Decisions */}
            <Card title="Decisões Pendentes da IA">
              {pending.length === 0 ? (
                <div className="py-6 text-center text-gray-500">
                  <Brain className="w-10 h-10 mx-auto mb-3 text-gray-600" />
                  <p>Nenhuma decisão pendente</p>
                  <p className="text-xs text-gray-600 mt-1">Execute o ciclo de análise para gerar decisões</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-72 overflow-y-auto">
                  {pending.map((d) => (
                    <PendingDecisionRow key={d.id} decision={d} onAction={() => {
                      api.decisions.pending().then(setPending).catch(() => {});
                    }} />
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Ads summary */}
          <Card title="Ads Hoje">
            <div className="flex items-center justify-between py-4">
              <div className="text-center flex-1">
                <p className="text-sm text-gray-400">Receita</p>
                <p className="text-2xl font-bold text-green-400">R$ {(overview.today?.revenue ?? 0).toFixed(2)}</p>
              </div>
              <div className="text-3xl text-gray-700">vs</div>
              <div className="text-center flex-1">
                <p className="text-sm text-gray-400">Gasto Ads</p>
                <p className="text-2xl font-bold text-yellow-400">R$ {(overview.today?.ad_spend ?? 0).toFixed(2)}</p>
              </div>
              <div className="text-center flex-1">
                <p className="text-sm text-gray-400">ROAS</p>
                <p className={`text-2xl font-bold ${(overview.today?.roas ?? 0) >= 3 ? "text-green-400" : (overview.today?.roas ?? 0) >= 1 ? "text-yellow-400" : "text-red-400"}`}>
                  {(overview.today?.roas ?? 0).toFixed(2)}x
                </p>
              </div>
              <div className="text-center flex-1">
                <p className="text-sm text-gray-400">Campanhas</p>
                <p className="text-2xl font-bold text-cyan-400">{overview.campaigns_count ?? 0}</p>
              </div>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function MiniStat({ icon, label, value, sub, color }: { icon: React.ReactNode; label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-[11px] text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5 ${className}`}>
      <h2 className="text-lg font-semibold text-white mb-4">{title}</h2>
      {children}
    </div>
  );
}

function MarginBar({ label, count, total, color, textColor }: { label: string; count: number; total: number; color: string; textColor: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className={`text-sm ${textColor}`}>{label}</span>
        <span className="text-sm text-gray-400">{count} ({pct.toFixed(0)}%)</span>
      </div>
      <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function PendingDecisionRow({ decision, onAction }: { decision: Decision; onAction: () => void }) {
  const [acting, setActing] = useState(false);
  const urgencyColors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400",
    high: "bg-orange-500/20 text-orange-400",
    medium: "bg-yellow-500/20 text-yellow-400",
    low: "bg-gray-500/20 text-gray-400",
  };

  const handleApprove = async () => {
    setActing(true);
    await api.decisions.approve(decision.id).catch(() => {});
    onAction();
    setActing(false);
  };

  const handleReject = async () => {
    setActing(true);
    await api.decisions.reject(decision.id).catch(() => {});
    onAction();
    setActing(false);
  };

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-white">{decision.action}</span>
          {decision.urgency && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${urgencyColors[decision.urgency] ?? urgencyColors.low}`}>{decision.urgency}</span>
          )}
        </div>
        <p className="text-xs text-gray-400 truncate">{decision.reason}</p>
        {decision.new_value && (
          <p className="text-xs text-gray-500 mt-1">
            R$ {Number(decision.old_value ?? 0).toFixed(2)} → <span className="text-white">R$ {Number(decision.new_value).toFixed(2)}</span>
          </p>
        )}
      </div>
      <div className="flex gap-2 ml-3">
        <button onClick={handleApprove} disabled={acting} className="px-3 py-1.5 text-xs font-medium bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 disabled:opacity-50">Aprovar</button>
        <button onClick={handleReject} disabled={acting} className="px-3 py-1.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50">Rejeitar</button>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4 h-24 animate-pulse" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-[var(--card)] rounded-xl h-48 animate-pulse" />
        <div className="bg-[var(--card)] rounded-xl h-48 animate-pulse lg:col-span-2" />
      </div>
    </div>
  );
}
