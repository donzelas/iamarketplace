"use client";

import { useEffect, useState } from "react";
import { api, Product, AdPerformance, Campaign } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function AdsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [performance, setPerformance] = useState<AdPerformance[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.products.list().then((p) => {
      setProducts(p);
      if (p.length > 0) setSelectedProduct(p[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedProduct) return;
    setLoading(true);
    Promise.all([
      api.ads.performance(selectedProduct, 14),
      api.ads.campaigns(selectedProduct),
    ])
      .then(([perf, camp]) => { setPerformance(perf); setCampaigns(camp); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  const totals = performance.reduce(
    (acc, p) => ({
      impressions: acc.impressions + p.impressions,
      clicks: acc.clicks + p.clicks,
      spend: acc.spend + p.spend,
      orders: acc.orders + p.orders,
      revenue: acc.revenue + p.revenue,
    }),
    { impressions: 0, clicks: 0, spend: 0, orders: 0, revenue: 0 }
  );

  const avgCPC = totals.clicks > 0 ? totals.spend / totals.clicks : 0;
  const avgCTR = totals.impressions > 0 ? (totals.clicks / totals.impressions) * 100 : 0;
  const avgACOS = totals.revenue > 0 ? (totals.spend / totals.revenue) * 100 : 0;
  const avgROAS = totals.spend > 0 ? totals.revenue / totals.spend : 0;

  const chartData = performance
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((p) => ({
      date: new Date(p.date).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      Gasto: p.spend,
      Receita: p.revenue,
    }));

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Performance de Ads</h1>

      <select
        value={selectedProduct}
        onChange={(e) => setSelectedProduct(e.target.value)}
        className="w-full max-w-md px-4 py-2.5 bg-[var(--card)] border border-[var(--card-border)] rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
      >
        <option value="">Selecione um produto</option>
        {products.map((p) => (
          <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
        ))}
      </select>

      {loading ? (
        <div className="h-64 bg-[var(--card)] rounded-xl animate-pulse" />
      ) : selectedProduct && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <MiniStat label="Impressões" value={totals.impressions.toLocaleString("pt-BR")} />
            <MiniStat label="Cliques" value={totals.clicks.toLocaleString("pt-BR")} />
            <MiniStat label="Gasto" value={`R$ ${totals.spend.toFixed(2)}`} />
            <MiniStat label="Pedidos" value={totals.orders.toString()} />
            <MiniStat label="CPC" value={`R$ ${avgCPC.toFixed(2)}`} />
            <MiniStat label="CTR" value={`${avgCTR.toFixed(2)}%`} />
            <MiniStat label="ACOS" value={`${avgACOS.toFixed(1)}%`} color={avgACOS > 30 ? "text-red-400" : avgACOS > 20 ? "text-yellow-400" : "text-green-400"} />
            <MiniStat label="ROAS" value={`${avgROAS.toFixed(2)}x`} color={avgROAS >= 3 ? "text-green-400" : avgROAS >= 1 ? "text-yellow-400" : "text-red-400"} />
          </div>

          {chartData.length > 0 && (
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4">Gasto vs Receita (14 dias)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                  <XAxis dataKey="date" stroke="#6b7280" fontSize={11} />
                  <YAxis stroke="#6b7280" fontSize={11} tickFormatter={(v) => `R$${v}`} />
                  <Tooltip contentStyle={{ background: "#111119", border: "1px solid #1e1e2e", borderRadius: "8px", fontSize: "12px" }} />
                  <Legend />
                  <Bar dataKey="Gasto" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Receita" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Campanhas ({campaigns.length})</h2>
            {campaigns.length === 0 ? (
              <p className="text-gray-500 text-sm">Nenhuma campanha cadastrada</p>
            ) : (
              <div className="space-y-2">
                {campaigns.map((c) => (
                  <div key={c.id} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div>
                      <p className="text-sm text-white font-medium">{c.campaign_name ?? c.campaign_id}</p>
                      <p className="text-xs text-gray-500">{c.platform} · {c.campaign_id}</p>
                    </div>
                    <div className="text-right">
                      {c.daily_budget && <p className="text-sm text-gray-400">R$ {c.daily_budget.toFixed(2)}/dia</p>}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "active" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
                        {c.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color ?? "text-white"}`}>{value}</p>
    </div>
  );
}
