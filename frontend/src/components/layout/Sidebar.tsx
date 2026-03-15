"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "대시보드", icon: "📊" },
  { href: "/sources", label: "뉴스 소스", icon: "📡" },
  { href: "/articles", label: "기사 목록", icon: "📰" },
  { href: "/reports", label: "리포트 관리", icon: "📋" },
  { href: "/recipients", label: "수신자 관리", icon: "👥" },
  { href: "/analytics", label: "트렌드 분석", icon: "📈" },
  { href: "/jobs", label: "작업 로그", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-brand-900 text-white flex flex-col z-10">
      <div className="px-5 py-5 border-b border-white/10">
        <div className="text-base font-bold leading-tight">📡 AI Trend</div>
        <div className="text-xs text-blue-300 mt-0.5">Newsletter Admin</div>
      </div>

      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-white/15 text-white"
                  : "text-blue-200 hover:bg-white/10 hover:text-white"
              )}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-white/10 text-xs text-blue-300">
        v0.1.0 · AI Newsletter
      </div>
    </aside>
  );
}
