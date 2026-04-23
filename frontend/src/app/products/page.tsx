"use client";

import { useEffect, useState } from "react";
import { api, Product, MLListing } from "@/lib/api";
import { Plus, Search, Package, TrendingUp, TrendingDown, Minus, Truck, RefreshCw } from "lucide-react";

type StatusFilter = "active" | "paused" | "all";
type SortKey = "revenue" | "sold" | "visits" | "conversion" | "margin" | "price" | "stock";

interface EnrichedProduct {
  product: Product;
  listings: MLListing[];
  soldPeriod: number;
  soldLifetime: number;
  totalVisits: number;
  revenuePeriod: number;
  totalStock: number;
  conversion: number;
  avgPrice: number;
  thumbnail: string | null;
  listingUrl: string | null;
  freeShipping: boolean;
  listingType: string;
  feePct: number;
  estimatedMargin: number;
  estimatedProfit: number;
  trend: "up" | "down" | "stable" | "none";
}

const PERIOD_OPTIONS = [
  { value: 7, label: "7d" },
  { value: 15, label: "15d" },
  { value: 30, label: "30d" },
  { value: 60, label: "60d" },
  { value: 90, label: "90d" },
];

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [mlListings, setMlListings] = useState<MLListing[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [sortBy, setSortBy] = useState<SortKey>("revenue");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [period, setPeriod] = useState(30);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = (status: StatusFilter, days: number) => {
    setLoading(true);
    setError(null);
    Promise.all([api.products.list(status), api.ml.listings("all", days)])
      .then(([prods, mls]) => { setProducts(prods); setMlListings(mls); })
      .catch((e) => { setError(`Erro ao carregar: ${e.message}`); })
      .finally(() => { setLoading(false); setSyncing(false); });
  };

  useEffect(() => { fetchData(statusFilter, period); }, [statusFilter]);

  const handlePeriodChange = (days: number) => {
    setPeriod(days);
    setSyncing(true);
    fetchData(statusFilter, days);
  };

  const enriched: EnrichedProduct[] = products.map((p) => {
    const listings = mlListings.filter((l) => l.product_id === p.id);
    const soldPeriod = listings.reduce((s, l) => s + (l.sold_period || 0), 0);
    const soldLifetime = listings.reduce((s, l) => s + (l.sold_quantity || 0), 0);
    const totalVisits = listings.reduce((s, l) => s + (l.visits_total || 0), 0);
    const revenuePeriod = listings.reduce((s, l) => s + (l.revenue_period || 0), 0);
    const totalStock = listings.reduce((s, l) => s + (l.available_quantity || 0), 0);

    const avgPrice = listings.length > 0 ? Number(listings[0].current_price) : Number(p.current_price) || 0;
    const cost = Number(p.cost) || 0;
    const thumbnail = listings[0]?.thumbnail || null;
    const listingUrl = listings[0]?.listing_url || null;
    const freeShipping = listings.some((l) => l.free_shipping);
    const lt = listings[0]?.listing_type || "";
    const listingType = lt.includes("gold_pro") ? "Premium" : lt.includes("gold") ? "Clássico" : "Grátis";
    const feePct = listings[0]?.marketplace_fee_pct || 16;

    const conversion = totalVisits > 0 && soldPeriod > 0
      ? Math.min((soldPeriod / totalVisits) * 100, 100)
      : 0;

    const mlFee = avgPrice * (feePct / 100);
    const shippingCost = freeShipping ? 0 : 15;
    const estimatedProfit = avgPrice - cost - mlFee - shippingCost;
    const estimatedMargin = avgPrice > 0 ? (estimatedProfit / avgPrice) * 100 : 0;

    let trend: "up" | "down" | "stable" | "none" = "none";
    if (soldPeriod > 0 && totalVisits > 0) {
      const ratio = soldPeriod / totalVisits;
      if (ratio >= 0.08) trend = "up";
      else if (ratio >= 0.03) trend = "stable";
      else trend = "down";
    }

    return {
      product: p, listings, soldPeriod, soldLifetime, totalVisits, revenuePeriod, totalStock,
      conversion, avgPrice, thumbnail, listingUrl, freeShipping, listingType,
      feePct, estimatedMargin, estimatedProfit, trend,
    };
  });

  const filtered = enriched
    .filter((e) =>
      e.product.name.toLowerCase().includes(search.toLowerCase()) ||
      e.product.sku.toLowerCase().includes(search.toLowerCase()) ||
      (e.product.category || "").toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const keyMap: Record<SortKey, (e: EnrichedProduct) => number> = {
        revenue: (e) => e.revenuePeriod, sold: (e) => e.soldPeriod, visits: (e) => e.totalVisits,
        conversion: (e) => e.conversion, margin: (e) => e.estimatedMargin,
        price: (e) => e.avgPrice, stock: (e) => e.totalStock,
      };
      return sortDir === "desc" ? keyMap[sortBy](b) - keyMap[sortBy](a) : keyMap[sortBy](a) - keyMap[sortBy](b);
    });

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) setSortDir(sortDir === "desc" ? "asc" : "desc");
    else { setSortBy(key); setSortDir("desc"); }
  };
  const si = (key: SortKey) => sortBy === key ? (sortDir === "desc" ? " ↓" : " ↑") : "";

  const totals = {
    revenue: filtered.reduce((s, e) => s + e.revenuePeriod, 0),
    sold: filtered.reduce((s, e) => s + e.soldPeriod, 0),
    visits: filtered.reduce((s, e) => s + e.totalVisits, 0),
  };
  const totalConversion = totals.visits > 0 ? (totals.sold / totals.visits * 100) : 0;

  return (
    <div className="max-w-[1400px] mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Produtos</h1>
          <p className="text-sm text-gray-500 mt-1">
            {filtered.length} produtos · R$ {totals.revenue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} vendas ({period}d) · {totals.sold.toLocaleString("pt-BR")} un. ({period}d) · {totals.visits.toLocaleString("pt-BR")} visitas ({period}d) · {totalConversion.toFixed(1)}% conversão
          </p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-500 transition">
          <Plus className="w-4 h-4" /> Novo Produto
        </button>
      </div>

      {/* Filters Row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input type="text" placeholder="Buscar por nome, SKU ou categoria..." value={search} onChange={(e) => setSearch(e.target.value)}
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
          {(["active", "paused", "all"] as StatusFilter[]).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${statusFilter === s ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              {s === "active" ? "Ativos" : s === "paused" ? "Pausados" : "Todos"}
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
        <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="h-20 bg-[var(--card)] rounded-lg animate-pulse" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12"><Package className="w-12 h-12 mx-auto mb-3 text-gray-600" /><p className="text-gray-500">Nenhum produto encontrado</p></div>
      ) : (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--card-border)] text-gray-400 text-xs">
                  <th className="text-left px-4 py-3 font-medium w-[320px]">Anúncio</th>
                  <th className="text-center px-3 py-3 font-medium">Trend</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("price")}>Preço{si("price")}</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("revenue")}>Vendas ({period}d){si("revenue")}</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("sold")}>Vendidos ({period}d){si("sold")}</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("visits")}>Visitas ({period}d){si("visits")}</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("conversion")}>Conversão{si("conversion")}</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("margin")}>Margem{si("margin")}</th>
                  <th className="text-right px-3 py-3 font-medium">Taxa ML</th>
                  <th className="text-right px-3 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort("stock")}>Estoque{si("stock")}</th>
                  <th className="text-center px-3 py-3 font-medium">Frete</th>
                  <th className="text-center px-3 py-3 font-medium">Tipo</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr key={e.product.id} className="border-b border-[var(--card-border)] hover:bg-white/5 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {e.thumbnail ? (
                          <img src={e.thumbnail.replace("http://", "https://")} alt="" className="w-14 h-14 rounded-lg object-cover bg-white/5 flex-shrink-0" />
                        ) : (
                          <div className="w-14 h-14 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0"><Package className="w-6 h-6 text-gray-600" /></div>
                        )}
                        <div className="min-w-0">
                          {e.listingUrl ? (
                            <a href={e.listingUrl} target="_blank" rel="noopener noreferrer" className="text-white hover:text-indigo-400 font-medium text-sm leading-snug block truncate max-w-[230px] transition">
                              {e.product.name}
                            </a>
                          ) : (
                            <p className="text-white font-medium text-sm leading-snug truncate max-w-[230px]">{e.product.name}</p>
                          )}
                          <span className="text-[11px] text-gray-500 font-mono">{e.product.sku}</span>
                          {e.soldLifetime > 0 && <span className="text-[10px] text-gray-600 block">+{e.soldLifetime} vendidos (total)</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-center"><TrendBadge trend={e.trend} /></td>
                    <td className="px-3 py-3 text-right">
                      <span className="text-white font-semibold">R$ {e.avgPrice.toFixed(2)}</span>
                      {e.listings[0]?.original_price && e.listings[0].original_price > e.avgPrice && (
                        <span className="text-[11px] text-gray-500 line-through block">R$ {Number(e.listings[0].original_price).toFixed(2)}</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-bold ${e.revenuePeriod > 0 ? "text-green-400" : "text-gray-500"}`}>
                        R$ {e.revenuePeriod.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-semibold ${e.soldPeriod > 0 ? "text-white" : "text-gray-500"}`}>{e.soldPeriod.toLocaleString("pt-BR")}</span>
                    </td>
                    <td className="px-3 py-3 text-right text-gray-300">{e.totalVisits.toLocaleString("pt-BR")}</td>
                    <td className="px-3 py-3 text-right">
                      {e.totalVisits > 0 && e.soldPeriod > 0 ? (
                        <div>
                          <span className={`font-semibold ${e.conversion >= 10 ? "text-green-400" : e.conversion >= 5 ? "text-yellow-400" : e.conversion > 0 ? "text-orange-400" : "text-gray-500"}`}>
                            {e.conversion.toFixed(1)}%
                          </span>
                          <span className="text-[10px] text-gray-600 block">{e.soldPeriod}v / {e.totalVisits.toLocaleString("pt-BR")}vis</span>
                        </div>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-semibold ${e.estimatedMargin >= 25 ? "text-green-400" : e.estimatedMargin >= 10 ? "text-yellow-400" : e.estimatedMargin >= 0 ? "text-orange-400" : "text-red-400"}`}>
                        {e.estimatedMargin.toFixed(1)}%
                      </span>
                      <span className={`text-[11px] block ${e.estimatedProfit >= 0 ? "text-gray-500" : "text-red-400"}`}>R$ {e.estimatedProfit.toFixed(2)}/un</span>
                    </td>
                    <td className="px-3 py-3 text-right text-gray-400">{e.feePct}%</td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-semibold ${e.totalStock === 0 ? "text-red-400" : e.totalStock < 10 ? "text-yellow-400" : "text-gray-300"}`}>
                        {e.totalStock}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      {e.freeShipping ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-green-400"><Truck className="w-3.5 h-3.5" /> Full</span>
                      ) : (
                        <span className="text-[11px] text-gray-500">Pago</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`text-[11px] px-2 py-0.5 rounded ${e.listingType === "Premium" ? "bg-yellow-500/20 text-yellow-400" : e.listingType === "Clássico" ? "bg-blue-500/20 text-blue-400" : "bg-gray-500/20 text-gray-400"}`}>
                        {e.listingType}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showForm && <ProductFormModal onClose={() => setShowForm(false)} onSubmit={async (data) => {
        try { const c = await api.products.create(data); setProducts((prev) => [...prev, c]); setShowForm(false); } catch (e: any) { alert(e.message); }
      }} />}
    </div>
  );
}

function TrendBadge({ trend }: { trend: string }) {
  if (trend === "none") return <span className="text-gray-600">-</span>;
  if (trend === "up") return (
    <div className="flex flex-col items-center">
      <TrendingUp className="w-4 h-4 text-green-400" />
      <span className="text-[10px] text-green-400 mt-0.5">Vendendo</span>
    </div>
  );
  if (trend === "stable") return (
    <div className="flex flex-col items-center">
      <Minus className="w-4 h-4 text-yellow-400" />
      <span className="text-[10px] text-yellow-400 mt-0.5">Estável</span>
    </div>
  );
  return (
    <div className="flex flex-col items-center">
      <TrendingDown className="w-4 h-4 text-red-400" />
      <span className="text-[10px] text-red-400 mt-0.5">Caindo</span>
    </div>
  );
}

function ProductFormModal({ onClose, onSubmit }: { onClose: () => void; onSubmit: (data: Partial<Product>) => void }) {
  const [form, setForm] = useState({
    name: "", sku: "", cost: "", current_price: "", min_price: "",
    min_margin_pct: "15", target_margin_pct: "25", category: "", brand: "", keywords: "",
  });
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name: form.name, sku: form.sku, cost: parseFloat(form.cost), current_price: parseFloat(form.current_price), min_price: parseFloat(form.min_price), min_margin_pct: parseFloat(form.min_margin_pct), target_margin_pct: parseFloat(form.target_margin_pct), category: form.category || null, brand: form.brand || null, keywords: form.keywords || null } as any);
  };
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-white mb-4">Novo Produto</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Input label="Nome" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
          <Input label="SKU" value={form.sku} onChange={(v) => setForm({ ...form, sku: v })} required />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Custo (R$)" type="number" value={form.cost} onChange={(v) => setForm({ ...form, cost: v })} required />
            <Input label="Preço (R$)" type="number" value={form.current_price} onChange={(v) => setForm({ ...form, current_price: v })} required />
            <Input label="Preço Min (R$)" type="number" value={form.min_price} onChange={(v) => setForm({ ...form, min_price: v })} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Margem Mín (%)" type="number" value={form.min_margin_pct} onChange={(v) => setForm({ ...form, min_margin_pct: v })} />
            <Input label="Margem Alvo (%)" type="number" value={form.target_margin_pct} onChange={(v) => setForm({ ...form, target_margin_pct: v })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Categoria" value={form.category} onChange={(v) => setForm({ ...form, category: v })} />
            <Input label="Marca" value={form.brand} onChange={(v) => setForm({ ...form, brand: v })} />
          </div>
          <Input label="Palavras-chave" value={form.keywords} onChange={(v) => setForm({ ...form, keywords: v })} />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 text-sm text-gray-400 bg-white/5 rounded-lg hover:bg-white/10">Cancelar</button>
            <button type="submit" className="flex-1 py-2 text-sm text-white bg-indigo-600 rounded-lg hover:bg-indigo-500">Criar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  return (
    <div>
      <label className="text-xs text-gray-400 mb-1 block">{label}</label>
      <input type={type} step={type === "number" ? "0.01" : undefined} value={value} onChange={(e) => onChange(e.target.value)} required={required}
        className="w-full px-3 py-2 bg-white/5 border border-[var(--card-border)] rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500" />
    </div>
  );
}
