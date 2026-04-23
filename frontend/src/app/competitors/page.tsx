"use client";

import { useEffect, useState } from "react";
import { api, Product, Competitor, PriceRecord } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

export default function CompetitorsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [priceHistory, setPriceHistory] = useState<PriceRecord[]>([]);
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
      api.competitors.list(selectedProduct),
      api.competitors.priceHistory(selectedProduct, 72),
    ])
      .then(([c, ph]) => { setCompetitors(c); setPriceHistory(ph); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  const product = products.find((p) => p.id === selectedProduct);

  const chartData = priceHistory
    .sort((a, b) => new Date(a.collected_at).getTime() - new Date(b.collected_at).getTime())
    .map((p) => ({
      time: new Date(p.collected_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }),
      price: p.price,
      marketplace: p.marketplace,
    }));

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Concorrentes</h1>

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
          {chartData.length > 0 && (
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4">Histórico de Preços (72h)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={11} />
                  <YAxis stroke="#6b7280" fontSize={11} tickFormatter={(v) => `R$${v}`} />
                  <Tooltip
                    contentStyle={{ background: "#111119", border: "1px solid #1e1e2e", borderRadius: "8px", fontSize: "12px" }}
                    labelStyle={{ color: "#9ca3af" }}
                    formatter={(value: number) => [`R$ ${value.toFixed(2)}`, "Preço"]}
                  />
                  {product && (
                    <ReferenceLine y={product.current_price} stroke="#6366f1" strokeDasharray="5 5" label={{ value: `Meu: R$${product.current_price}`, fill: "#6366f1", fontSize: 11 }} />
                  )}
                  <Line type="monotone" dataKey="price" stroke="#22c55e" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
            <h2 className="text-lg font-semibold text-white p-5 pb-3">
              Concorrentes ({competitors.length})
            </h2>
            {competitors.length === 0 ? (
              <div className="px-5 pb-5 text-gray-500 text-sm">Nenhum concorrente encontrado. Execute o monitoramento primeiro.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--card-border)] text-gray-400">
                    <th className="text-left px-4 py-3 font-medium">Marketplace</th>
                    <th className="text-left px-4 py-3 font-medium">Vendedor</th>
                    <th className="text-left px-4 py-3 font-medium">Produto</th>
                    <th className="text-right px-4 py-3 font-medium">Preço</th>
                    <th className="text-right px-4 py-3 font-medium">vs Meu</th>
                    <th className="text-right px-4 py-3 font-medium">Visto em</th>
                  </tr>
                </thead>
                <tbody>
                  {competitors.sort((a, b) => (Number(a.last_price) || 0) - (Number(b.last_price) || 0)).map((c) => {
                    const lastPrice = Number(c.last_price) || 0;
                    const myPrice = Number(product?.current_price) || 0;
                    const diff = myPrice > 0 && lastPrice > 0 ? ((lastPrice - myPrice) / myPrice * 100) : 0;
                    return (
                      <tr key={c.id} className="border-b border-[var(--card-border)] hover:bg-white/5">
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 text-xs rounded-full bg-white/10 text-gray-300">{c.marketplace}</span>
                        </td>
                        <td className="px-4 py-3 text-gray-400">{c.seller ?? "—"}</td>
                        <td className="px-4 py-3 text-white max-w-xs truncate">{c.name ?? "—"}</td>
                        <td className="px-4 py-3 text-right text-white font-medium">
                          {lastPrice > 0 ? `R$ ${lastPrice.toFixed(2)}` : "—"}
                        </td>
                        <td className={`px-4 py-3 text-right font-medium ${diff < 0 ? "text-red-400" : diff > 0 ? "text-green-400" : "text-gray-400"}`}>
                          {diff !== 0 ? `${diff > 0 ? "+" : ""}${diff.toFixed(1)}%` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500 text-xs">
                          {c.last_seen_at ? new Date(c.last_seen_at).toLocaleString("pt-BR") : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
