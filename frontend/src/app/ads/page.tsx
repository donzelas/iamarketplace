"use client";

import { useEffect, useState } from "react";
import { api, MLListing, MLSummary } from "@/lib/api";
import { Search, TrendingUp, ShoppingCart, Eye, Package, DollarSign, BarChart3, RefreshCw } from "lucide-react";

type SortKey = "revenue" | "sold" | "visits" | "conversion" | "price";

const PERIOD_OPTIONS = [
  { value: 7, label: "7d" },
  { value: 15, label: "15d" },
  { value: 30, label: "30d" },
  { value: 60, label: "60d" },
  { value: 90, label: "90d" },
];

interface EnrichedListing extends MLListing {
  conversion: number;
}

export default function AdsPage() {
  const [listings, setListings] = useState<MLListing[]>([]);
  const [summary, setSummary] = useState<MLSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "paused">("all");
  const [sortBy, setSortBy] = useState<SortKey>("revenue");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [period, setPeriod] = useState(30);

  const fetchData = (status: "all" | "active" | "paused", days: number) => {
    setLoading(true);
    setError(null);
    Promise.all([api.ml.listings(status, days), api.ml.summary(days)])
      .then(([l, s]) => { setListings(l); setSummary(s); })
      .catch((e) => { setError(`Erro ao carregar: ${e.message}`); })
      .finally(() => { setLoading(false); setSyncing(false); });
  };

  useEffect(() => { fetchData(statusFilter, period); }, [statusFilter]);

  const handlePeriodChange = (days: number) => {
    setPeriod(days);
    setSyncing(true);
    fetchData(statusFilter, days);
  };

  const filtered: EnrichedListing[] = listings
    .filter(
      (l) =>
        l.product_name.toLowerCase().includes(search.toLowerCase()) ||
        l.listing_id.toLowerCase().includes(search.toLowerCase()) ||
        l.product_sku.toLowerCase().includes(search.toLowerCase())
    )
    .map((l) => ({
      ...l,
      conversion: l.visits_total > 0 && l.sold_period > 0
        ? Math.min((l.sold_period / l.visits_total) * 100, 100)
        : 0,
    }))
    .sort((a, b) => {
      const keyMap: Record<SortKey, (e: EnrichedListing) => number> = {
        revenue: (e) => e.revenue_period,
        sold: (e) => e.sold_period,
        visits: (e) => e.visits_total,
        conversion: (e) => e.conversion,
        price: (e) => e.current_price,
      };
      return sortDir === "desc" ? keyMap[sortBy](b) - keyMap[sortBy](a) : keyMap[sortBy](a) - keyMap[sortBy](b);
    });

  const totalVisits = filtered.reduce((s, l) => s + l.visits_total, 0);
  const totalSoldPeriod = filtered.reduce((s, l) => s + l.sold_period, 0);
  const totalRevenuePeriod = filtered.reduce((s, l) => s + l.revenue_period, 0);
  const avgConversion = totalVisits > 0 ? (totalSoldPeriod / totalVisits) * 100 : 0;

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) setSortDir(sortDir === "desc" ? "asc" : "desc");
    else { setSortBy(key); setSortDir("desc"); }
  };
  const sortIcon = (key: SortKey) => sortBy === key ? (sortDir === "desc" ? " ↓" : " ↑") : "";

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Performance de Anúncios</h1>
          <p className="text-sm text-gray-500 mt-1">{filtered.length} anúncios · Período: {period} dias</p>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard icon={<DollarSign className="w-4 h-4" />} label={`Vendas Brutas (${period}d)`} value={`R$ ${totalRevenuePeriod.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} color="text-green-400" />
          <SummaryCard icon={<ShoppingCart className="w-4 h-4" />} label={`Unidades Vendidas (${period}d)`} value={totalSoldPeriod.toLocaleString("pt-BR")} color="text-blue-400" />
          <SummaryCard icon={<Eye className="w-4 h-4" />} label={`Visitas (${period}d)`} value={totalVisits.toLocaleString("pt-BR")} color="text-purple-400" />
          <SummaryCard icon={<BarChart3 className="w-4 h-4" />} label={`Conversão (${period}d)`} value={`${avgConversion.toFixed(1)}%`} color="text-yellow-400" />
          <SummaryCard icon={<TrendingUp className="w-4 h-4" />} label="Preço Médio" value={`R$ ${Number(summary.avg_price || 0).toFixed(2)}`} color="text-cyan-400" />
          <SummaryCard icon={<DollarSign className="w-4 h-4" />} label={`Ticket Médio (${period}d)`} value={`R$ ${Number(summary.avg_price_per_sale || 0).toFixed(2)}`} color="text-indigo-400" />
          <SummaryCard icon={<Package className="w-4 h-4" />} label="Anúncios Ativos" value={`${summary.active_listings}`} sub={`${summary.paused_listings} pausados`} color="text-green-400" />
          <SummaryCard icon={<Package className="w-4 h-4" />} label="Estoque Disponível" value={summary.total_available.toLocaleString("pt-BR")} color="text-orange-400" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input type="text" placeholder="Buscar anúncio, SKU ou ID..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-[var(--card)] border border-[var(--card-border)] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500" />
        </div>

        <div className="flex gap-1 bg-[var(--card)] border border-[var(--card-border)] rounded-lg p-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button key={opt.value} onClick={() => handlePeriodChange(opt.value)}
              className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition ${period === opt.value ? "bg-purple-600 text-white" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              {opt.label}
            </button>
          ))}
          {syncing && <RefreshCw className="w-4 h-4 text-purple-400 animate-spin self-center ml-1" />}
        </div>

        <div className="flex gap-1 bg-[var(--card)] border border-[var(--card-border)] rounded-lg p-1">
          {(["all", "active", "paused"] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${statusFilter === s ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              {s === "all" ? "Todos" : s === "active" ? "Ativos" : "Pausados"}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">{error}</div>
      )}
      {syncing && !loading && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg px-4 py-3 text-sm text-purple-300 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" /> Buscando dados do ML para {period} dias...
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[...Array(8)].map((_, i) => <div key={i} className="h-16 bg-[var(--card)] rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--card-border)] text-gray-400">
                  <th className="text-left px-4 py-3 font-medium">Anúncio</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("revenue")}>
                    Vendas ({period}d){sortIcon("revenue")}
                  </th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("sold")}>
                    Vendidos ({period}d){sortIcon("sold")}
                  </th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("visits")}>
                    Visitas ({period}d){sortIcon("visits")}
                  </th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("conversion")}>
                    Conversão{sortIcon("conversion")}
                  </th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("price")}>
                    Preço{sortIcon("price")}
                  </th>
                  <th className="text-center px-3 py-3 font-medium">Frete</th>
                  <th className="text-center px-3 py-3 font-medium">Tipo</th>
                  <th className="text-center px-3 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id} className="border-b border-[var(--card-border)] hover:bg-white/5 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {l.thumbnail && (
                          <img src={l.thumbnail.replace("http://", "https://")} alt="" className="w-10 h-10 rounded object-cover bg-white/5 flex-shrink-0" />
                        )}
                        <div className="min-w-0">
                          {l.listing_url ? (
                            <a href={l.listing_url} target="_blank" rel="noopener noreferrer" className="text-white hover:text-indigo-400 font-medium text-xs truncate max-w-[220px] block transition">
                              {l.product_name}
                            </a>
                          ) : (
                            <p className="text-white font-medium text-xs truncate max-w-[220px]">{l.product_name}</p>
                          )}
                          <span className="text-[10px] text-gray-500 font-mono mt-0.5 block">#{l.listing_id}</span>
                          {l.sold_quantity > 0 && <span className="text-[10px] text-gray-600">+{l.sold_quantity} vendidos (total)</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-medium ${l.revenue_period > 0 ? "text-green-400" : "text-gray-500"}`}>
                        R$ {l.revenue_period.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-semibold ${l.sold_period > 0 ? "text-white" : "text-gray-500"}`}>{l.sold_period}</span>
                    </td>
                    <td className="px-3 py-3 text-right text-gray-300">{l.visits_total.toLocaleString("pt-BR")}</td>
                    <td className="px-3 py-3 text-right">
                      {l.conversion > 0 ? (
                        <div>
                          <span className={`font-medium ${l.conversion >= 10 ? "text-green-400" : l.conversion >= 5 ? "text-yellow-400" : l.conversion > 0 ? "text-orange-400" : "text-gray-500"}`}>
                            {l.conversion.toFixed(1)}%
                          </span>
                          <span className="text-[10px] text-gray-600 block">{l.sold_period}v / {l.visits_total.toLocaleString("pt-BR")}vis</span>
                        </div>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right text-white font-medium">R$ {Number(l.current_price).toFixed(2)}</td>
                    <td className="px-3 py-3 text-center">
                      <span className={`text-xs ${l.free_shipping ? "text-green-400" : "text-gray-500"}`}>
                        {l.free_shipping ? "Grátis" : "Pago"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${(l.listing_type || "").includes("gold") ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400"}`}>
                        {(l.listing_type || "").includes("gold_pro") ? "Premium" : (l.listing_type || "").includes("gold") ? "Clássico" : "Grátis"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${l.status === "active" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
                        {l.status === "active" ? "Ativo" : "Pausado"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, sub, color }: { icon: React.ReactNode; label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}
