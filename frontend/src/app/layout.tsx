import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IA E-commerce — Dashboard",
  description: "Análise competitiva e gestão automatizada de e-commerce",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 p-6 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

function Sidebar() {
  const links = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/products", label: "Produtos", icon: "📦" },
    { href: "/competitors", label: "Concorrentes", icon: "🔍" },
    { href: "/ads", label: "Ads", icon: "📢" },
    { href: "/decisions", label: "Decisões IA", icon: "🤖" },
  ];

  return (
    <aside className="w-56 bg-[var(--card)] border-r border-[var(--card-border)] p-4 flex flex-col gap-1">
      <div className="text-xl font-bold text-white mb-6 px-3">🧠 IA Market</div>
      {links.map((link) => (
        <a
          key={link.href}
          href={link.href}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <span>{link.icon}</span>
          {link.label}
        </a>
      ))}
    </aside>
  );
}
