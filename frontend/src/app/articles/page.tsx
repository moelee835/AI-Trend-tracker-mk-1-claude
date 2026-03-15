"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getArticles } from "@/lib/api";
import { fmtDate, CATEGORY_LABELS } from "@/lib/utils";

const CATEGORIES = Object.entries(CATEGORY_LABELS);

export default function ArticlesPage() {
  const [filters, setFilters] = useState({
    category: "",
    min_score: "",
    is_duplicate: "",
    limit: 50,
    offset: 0,
  });

  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== "" && v !== undefined)
  );

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ["articles", filters],
    queryFn: () => getArticles(params),
  });

  const scoreColor = (score: number | null) => {
    if (!score) return "text-gray-400";
    if (score >= 0.7) return "text-green-600 font-semibold";
    if (score >= 0.4) return "text-yellow-600";
    return "text-gray-500";
  };

  return (
    <div className="space-y-5">
      <h1 className="page-title">기사 목록</h1>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-end">
        <div>
          <label className="label">카테고리</label>
          <select
            className="input w-40"
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value, offset: 0 })}
          >
            <option value="">전체</option>
            {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="label">최소 점수</label>
          <select
            className="input w-32"
            value={filters.min_score}
            onChange={(e) => setFilters({ ...filters, min_score: e.target.value, offset: 0 })}
          >
            <option value="">전체</option>
            <option value="0.7">0.7 이상 (High)</option>
            <option value="0.4">0.4 이상 (Medium)</option>
          </select>
        </div>
        <div>
          <label className="label">중복 여부</label>
          <select
            className="input w-32"
            value={filters.is_duplicate}
            onChange={(e) => setFilters({ ...filters, is_duplicate: e.target.value, offset: 0 })}
          >
            <option value="">전체</option>
            <option value="false">원본만</option>
            <option value="true">중복만</option>
          </select>
        </div>
        <div>
          <label className="label">표시 수</label>
          <select
            className="input w-24"
            value={filters.limit}
            onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value), offset: 0 })}
          >
            {[20, 50, 100, 200].map((n) => <option key={n} value={n}>{n}개</option>)}
          </select>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs text-gray-500">
          {articles.length}개 표시
        </div>
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="table-header">제목</th>
              <th className="table-header">카테고리</th>
              <th className="table-header">점수</th>
              <th className="table-header">수집일</th>
              <th className="table-header">상태</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={5} className="table-cell text-gray-400">로딩 중...</td></tr>
            )}
            {articles.map((a: any) => (
              <tr key={a.id} className="table-row">
                <td className="table-cell max-w-sm">
                  <a
                    href={a.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-gray-900 hover:text-blue-600 line-clamp-2"
                  >
                    {a.title}
                  </a>
                  {a.summary_excerpt && (
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{a.summary_excerpt}</p>
                  )}
                </td>
                <td className="table-cell whitespace-nowrap">
                  {a.category ? (
                    <span className="badge badge-blue">{CATEGORY_LABELS[a.category] || a.category}</span>
                  ) : "-"}
                </td>
                <td className={`table-cell font-mono ${scoreColor(a.composite_score)}`}>
                  {a.composite_score != null ? a.composite_score.toFixed(3) : "-"}
                </td>
                <td className="table-cell text-xs whitespace-nowrap">{fmtDate(a.collected_at)}</td>
                <td className="table-cell">
                  {a.is_duplicate ? (
                    <span className="badge badge-gray">중복</span>
                  ) : (
                    <span className="badge badge-green">원본</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
