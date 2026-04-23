"use client";

import { useEffect, useState } from "react";
import { api, Decision } from "@/lib/api";
import { Brain, Check, X, Clock, AlertTriangle, Zap } from "lucide-react";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const loadDecisions = () => {
    setLoading(true);
    const fetcher = filter === "all" ? api.decisions.list() : api.decisions.list(filter);
    fetcher.then(setDecisions).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(loadDecisions, [filter]);

  const handleApprove = async (id: string) => {
    await api.decisions.approve(id).catch(() => {});
    loadDecisions();
  };

  const handleReject = async (id: string) => {
    await api.decisions.reject(id).catch(() => {});
    loadDecisions();
  };

  const statusConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
    pending: { icon: <Clock className="w-4 h-4" />, color: "text-yellow-400 bg-yellow-400/10", label: "Pendente" },
    approved: { icon: <Check className="w-4 h-4" />, color: "text-blue-400 bg-blue-400/10", label: "Aprovado" },
    executed: { icon: <Zap className="w-4 h-4" />, color: "text-green-400 bg-green-400/10", label: "Executado" },
    rejected: { icon: <X className="w-4 h-4" />, color: "text-gray-400 bg-gray-400/10", label: "Rejeitado" },
    error: { icon: <AlertTriangle className="w-4 h-4" />, color: "text-red-400 bg-red-400/10", label: "Erro" },
  };

  const urgencyColors: Record<string, string> = {
    critical: "text-red-400 bg-red-400/10",
    high: "text-orange-400 bg-orange-400/10",
    medium: "text-yellow-400 bg-yellow-400/10",
    low: "text-gray-400 bg-gray-400/10",
  };

  const actionLabels: Record<string, string> = {
    ADJUST_PRICE: "Ajustar Preço",
    RAISE_PRICE: "Subir Preço",
    INCREASE_BID: "Aumentar Lance",
    REDUCE_BID: "Reduzir Lance",
    PAUSE_AD: "Pausar Anúncio",
    INCREASE_BUDGET: "Aumentar Budget",
    REDUCE_BUDGET: "Reduzir Budget",
    HOLD: "Manter",
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Brain className="w-7 h-7 text-indigo-400" /> Decisões da IA
        </h1>
      </div>

      <div className="flex gap-2">
        {["all", "pending", "executed", "approved", "rejected"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm rounded-lg transition ${filter === f ? "bg-indigo-600 text-white" : "bg-white/5 text-gray-400 hover:bg-white/10"}`}
          >
            {f === "all" ? "Todas" : statusConfig[f]?.label ?? f}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="h-20 bg-[var(--card)] rounded-xl animate-pulse" />)}
        </div>
      ) : decisions.length === 0 ? (
        <div className="text-center py-16 text-gray-500">Nenhuma decisão encontrada</div>
      ) : (
        <div className="space-y-3">
          {decisions.map((d) => {
            const st = statusConfig[d.status] ?? statusConfig.pending;
            return (
              <div key={d.id} className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-white font-semibold">{actionLabels[d.action] ?? d.action}</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${st.color}`}>
                        {st.icon} {st.label}
                      </span>
                      {d.urgency && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${urgencyColors[d.urgency] ?? urgencyColors.low}`}>
                          {d.urgency}
                        </span>
                      )}
                      <span className="text-xs text-gray-600">({d.decision_type})</span>
                    </div>

                    <p className="text-sm text-gray-400 mb-2">{d.reason}</p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {d.old_value != null && d.new_value != null && (
                        <span>
                          R$ {d.old_value.toFixed(2)} → <span className="text-white font-medium">R$ {d.new_value.toFixed(2)}</span>
                        </span>
                      )}
                      {d.confidence != null && (
                        <span>Confiança: {(d.confidence * 100).toFixed(0)}%</span>
                      )}
                      <span>{new Date(d.created_at).toLocaleString("pt-BR")}</span>
                      {d.executed_at && (
                        <span className="text-green-500">Executado: {new Date(d.executed_at).toLocaleString("pt-BR")}</span>
                      )}
                    </div>
                  </div>

                  {d.status === "pending" && (
                    <div className="flex gap-2 ml-4">
                      <button onClick={() => handleApprove(d.id)} className="px-4 py-2 text-sm font-medium bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition">
                        Aprovar
                      </button>
                      <button onClick={() => handleReject(d.id)} className="px-4 py-2 text-sm font-medium bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition">
                        Rejeitar
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
