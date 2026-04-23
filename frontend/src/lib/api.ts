const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Erro na API");
  }
  return res.json();
}

export const api = {
  dashboard: {
    overview: () => request<DashboardOverview>("/api/dashboard/overview"),
    productAnalysis: (id: string) => request<MarketAnalysis>(`/api/dashboard/product/${id}/analysis`),
    marginHistory: (id: string, days = 30) => request<MarginSnapshot[]>(`/api/dashboard/product/${id}/margin-history?days=${days}`),
  },
  products: {
    list: (status = "active") => request<Product[]>(`/api/products/?status=${status}`),
    get: (id: string) => request<Product>(`/api/products/${id}`),
    create: (data: Partial<Product>) => request<Product>("/api/products/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Product>) => request<Product>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  },
  competitors: {
    list: (productId: string) => request<Competitor[]>(`/api/competitors/${productId}`),
    priceHistory: (productId: string, hours = 72) => request<PriceRecord[]>(`/api/competitors/${productId}/price-history?hours=${hours}`),
  },
  ads: {
    campaigns: (productId?: string) => request<Campaign[]>(`/api/ads/campaigns${productId ? `?product_id=${productId}` : ""}`),
    performance: (productId: string, days = 7) => request<AdPerformance[]>(`/api/ads/performance/${productId}?days=${days}`),
  },
  decisions: {
    list: (status?: string) => request<Decision[]>(`/api/decisions/${status ? `?status=${status}` : ""}`),
    pending: () => request<Decision[]>("/api/decisions/pending"),
    approve: (id: string) => request<{ status: string }>(`/api/decisions/${id}/approve`, { method: "POST" }),
    reject: (id: string) => request<{ status: string }>(`/api/decisions/${id}/reject`, { method: "POST" }),
  },
};

export interface DashboardOverview {
  products: { total: number; active: number };
  today: { ad_spend: number; revenue: number; roas: number };
  pending_decisions: number;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  cost: number;
  current_price: number;
  min_price: number;
  max_price: number | null;
  min_margin_pct: number;
  target_margin_pct: number;
  category: string | null;
  brand: string | null;
  keywords: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Competitor {
  id: string;
  marketplace: string;
  seller: string | null;
  name: string | null;
  last_price: number | null;
  last_seen_at: string | null;
}

export interface PriceRecord {
  id: number;
  competitor_id: string;
  marketplace: string;
  price: number;
  original_price: number | null;
  free_shipping: boolean;
  seller: string | null;
  position: number | null;
  collected_at: string;
}

export interface Campaign {
  id: string;
  product_id: string;
  platform: string;
  campaign_id: string;
  campaign_name: string | null;
  daily_budget: number | null;
  status: string;
}

export interface AdPerformance {
  platform: string;
  date: string;
  impressions: number;
  clicks: number;
  spend: number;
  orders: number;
  revenue: number;
  cpc: number | null;
  ctr: number | null;
  conversion_rate: number | null;
  acos: number | null;
  roas: number | null;
}

export interface Decision {
  id: string;
  product_id: string;
  decision_type: string;
  action: string;
  old_value: number | null;
  new_value: number | null;
  reason: string | null;
  confidence: number | null;
  status: string;
  urgency: string | null;
  created_at: string;
  executed_at: string | null;
}

export interface MarketAnalysis {
  product_id: string;
  product_name: string;
  my_price: number;
  competitor_count: number;
  price_stats: { min: number; max: number; avg: number; median: number; stdev: number };
  my_position: { rank: number; total: number; percentile: number };
  price_gap: { vs_min: number; vs_min_pct: number; vs_avg: number; vs_avg_pct: number };
  free_shipping_competitors: number;
  trend: { direction: string; change_pct_72h: number };
  marketplaces: Record<string, { count: number; min: number; avg: number; max: number }>;
  analyzed_at: string;
}

export interface MarginSnapshot {
  sale_price: number | null;
  net_profit: number | null;
  margin_pct: number | null;
  health_status: string | null;
  calculated_at: string;
}
