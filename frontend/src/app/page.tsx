"use client";

import { useEffect, useState } from "react";
import { api, DashboardOverview, Decision } from "@/lib/api";
import { TrendingUp, TrendingDown, Package, AlertTriangle, DollarSign, BarChart3, Brain } from "lucide-react";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [pending, setPending] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.dashboard.overview(), api.decisions.pending()])
      .then(([ov, pd]) => { setOverview(ov); setPending(pd); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Package className="w-5 h-5" />}
          label="Produtos Ativos"
          value={overview?.products.total ?? 0}
          color="accent"
        />
        <StatCard
          icon={<DollarSign className="w-5 h-5" />}
          label="Gasto Ads Hoje"
          value={`R$ ${(overview?.today.ad_spend ?? 0).toFixed(2)}`}
          color="warning"
        />
        <StatCard
          icon={<BarChart3 className="w-5 h-5" />}
          label="ROAS Hoje"
          value={`${(overview?.today.roas ?? 0).toFixed(2)}x`}
          color="success"
        />
        <StatCard
          icon={<Brain className="w-5 h-5" />}
          label="Decisões Pendentes"
          value={overview?.pending_decisions ?? 0}
          color={overview?.pending_decisions ? "danger" : "success"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Receita vs Gasto de Ads (Hoje)">
          <div className="flex items-center justify-between py-8">
            <div className="text-center">
              <p className="text-sm text-gray-400">Receita</p>
              <p className="text-3xl font-bold text-green-400">
                R$ {(overview?.today.revenue ?? 0).toFixed(2)}
              </p>
            </div>
            <div className="text-4xl text-gray-600">vs</div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Gasto Ads</p>
              <p className="text-3xl font-bold text-yellow-400">
                R$ {(overview?.today.ad_spend ?? 0).toFixed(2)}
              </p>
            </div>
          </div>
          <div className="text-center">
            <span className={`text-lg font-semibold ${(overview?.today.roas ?? 0) >= 3 ? "text-green-400" : (overview?.today.roas ?? 0) >= 1 ? "text-yellow-400" : "text-red-400"}`}>
              ROAS: {(overview?.today.roas ?? 0).toFixed(2)}x
            </span>
          </div>
        </Card>

        <Card title="Decisões Pendentes da IA">
          {pending.length === 0 ? (
            <div className="py-8 text-center text-gray-500">Nenhuma decisão pendente</div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {pending.map((d) => (
                <PendingDecisionRow key={d.id} decision={d} onAction={() => {
                  api.decisions.pending().then(setPending).catch(() => {});
                }} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color: string }) {
  const colors: Record<string, string> = {
    accent: "text-indigo-400 bg-indigo-400/10",
    success: "text-green-400 bg-green-400/10",
    warning: "text-yellow-400 bg-yellow-400/10",
    danger: "text-red-400 bg-red-400/10",
  };

  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg ${colors[color]}`}>{icon}</div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
      <h2 className="text-lg font-semibold text-white mb-4">{title}</h2>
      {children}
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
            <span className={`text-xs px-2 py-0.5 rounded-full ${urgencyColors[decision.urgency] ?? urgencyColors.low}`}>
              {decision.urgency}
            </span>
          )}
        </div>
        <p className="text-xs text-gray-400 truncate">{decision.reason}</p>
        {decision.new_value && (
          <p className="text-xs text-gray-500 mt-1">
            R$ {decision.old_value?.toFixed(2)} → <span className="text-white">R$ {decision.new_value.toFixed(2)}</span>
          </p>
        )}
      </div>
      <div className="flex gap-2 ml-3">
        <button onClick={handleApprove} disabled={acting} className="px-3 py-1.5 text-xs font-medium bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 disabled:opacity-50">
          Aprovar
        </button>
        <button onClick={handleReject} disabled={acting} className="px-3 py-1.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50">
          Rejeitar
        </button>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="h-8 w-48 bg-white/5 rounded animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5 h-28 animate-pulse" />
        ))}
      </div>
    </div>
  );
}
