"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import { Plus, Search } from "lucide-react";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    api.products.list().then(setProducts).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sku.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async (data: Partial<Product>) => {
    try {
      const created = await api.products.create(data);
      setProducts((prev) => [...prev, created]);
      setShowForm(false);
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Produtos</h1>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-500 transition">
          <Plus className="w-4 h-4" /> Novo Produto
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Buscar por nome ou SKU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-[var(--card)] border border-[var(--card-border)] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-[var(--card)] rounded-lg animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {products.length === 0 ? "Nenhum produto cadastrado" : "Nenhum produto encontrado"}
        </div>
      ) : (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--card-border)] text-gray-400">
                <th className="text-left px-4 py-3 font-medium">Produto</th>
                <th className="text-left px-4 py-3 font-medium">SKU</th>
                <th className="text-right px-4 py-3 font-medium">Custo</th>
                <th className="text-right px-4 py-3 font-medium">Preço</th>
                <th className="text-right px-4 py-3 font-medium">Margem Min</th>
                <th className="text-right px-4 py-3 font-medium">Margem Alvo</th>
                <th className="text-center px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const simpleMargin = ((p.current_price - p.cost) / p.current_price * 100);
                return (
                  <tr key={p.id} className="border-b border-[var(--card-border)] hover:bg-white/5 transition cursor-pointer" onClick={() => window.location.href = `/products/${p.id}`}>
                    <td className="px-4 py-3">
                      <span className="text-white font-medium">{p.name}</span>
                      {p.brand && <span className="text-xs text-gray-500 ml-2">{p.brand}</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{p.sku}</td>
                    <td className="px-4 py-3 text-right text-gray-400">R$ {p.cost.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">R$ {p.current_price.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-gray-400">{p.min_margin_pct}%</td>
                    <td className="px-4 py-3 text-right text-gray-400">{p.target_margin_pct}%</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded-full ${simpleMargin >= p.target_margin_pct ? "bg-green-500/20 text-green-400" : simpleMargin >= p.min_margin_pct ? "bg-yellow-500/20 text-yellow-400" : "bg-red-500/20 text-red-400"}`}>
                        {simpleMargin.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <ProductFormModal onClose={() => setShowForm(false)} onSubmit={handleCreate} />}
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
    onSubmit({
      name: form.name,
      sku: form.sku,
      cost: parseFloat(form.cost),
      current_price: parseFloat(form.current_price),
      min_price: parseFloat(form.min_price),
      min_margin_pct: parseFloat(form.min_margin_pct),
      target_margin_pct: parseFloat(form.target_margin_pct),
      category: form.category || null,
      brand: form.brand || null,
      keywords: form.keywords || null,
    } as any);
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
          <Input label="Palavras-chave (separadas por vírgula)" value={form.keywords} onChange={(v) => setForm({ ...form, keywords: v })} />
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
      <input
        type={type}
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full px-3 py-2 bg-white/5 border border-[var(--card-border)] rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
      />
    </div>
  );
}
