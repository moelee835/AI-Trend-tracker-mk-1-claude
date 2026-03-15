"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTrends, getLast7Trends } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Legend, PieChart, Pie, Cell,
} from "recharts";
import { format, subDays } from "date-fns";

const PRESET_RANGES = [
  { label: "최근 7일", days: 7 },
  { label: "최근 14일", days: 14 },
  { label: "최근 30일", days: 30 },
];

const COLORS = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2", "#65a30d", "#c026d3"];

export default function AnalyticsPage() {
  const today = format(new Date(), "yyyy-MM-dd");
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 6), "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(today);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["trends", startDate, endDate],
    queryFn: () => getTrends({ start_date: startDate, end_date: endDate }),
    enabled: false,
  });

  const { data: quick7 } = useQuery({
    queryKey: ["trends-7"],
    queryFn: getLast7Trends,
  });

  const handlePreset = (days: number) => {
    const newStart = format(subDays(new Date(), days - 1), "yyyy-MM-dd");
    setStartDate(newStart);
    setEndDate(today);
  };

  const trends = data || quick7;
  const keywordChartData = (trends?.top_keywords || []).slice(0, 15).map(([kw, cnt]: [string, number]) => ({
    name: kw,
    count: cnt,
  }));

  return (
    <div className="space-y-6">
      <h1 className="page-title">트렌드 분석</h1>

      {/* Period selector */}
      <div className="card">
        <h2 className="section-title mb-3">분석 기간 선택</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex gap-2">
            {PRESET_RANGES.map((r) => (
              <button
                key={r.days}
                className="btn btn-sm btn-secondary"
                onClick={() => handlePreset(r.days)}
              >
                {r.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              className="input w-36"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <span className="text-gray-400">~</span>
            <input
              type="date"
              className="input w-36"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <button className="btn-primary" onClick={() => refetch()} disabled={isLoading}>
            {isLoading ? "분석 중..." : "분석"}
          </button>
        </div>
      </div>

      {trends && (
        <>
          {/* Summary */}
          <div className="card">
            <h2 className="section-title mb-2">📝 AI 분석 요약</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              {trends.llm_summary || "분석 데이터를 불러오는 중..."}
            </p>
            {trends.key_observations?.length > 0 && (
              <ul className="mt-3 space-y-1">
                {trends.key_observations.map((obs: string, i: number) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-600">
                    <span className="text-blue-500 mt-0.5">•</span>
                    {obs}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Keyword Chart */}
          {keywordChartData.length > 0 && (
            <div className="card">
              <h2 className="section-title mb-4">🔑 자주 등장한 키워드 Top 15</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={keywordChartData} layout="vertical" barSize={18}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Rising / Declining */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <h2 className="section-title mb-3">📈 새롭게 부상한 키워드</h2>
              <div className="flex flex-wrap gap-2">
                {(trends.rising_keywords || []).map((kw: string) => (
                  <span key={kw} className="badge badge-green">{kw}</span>
                ))}
                {!trends.rising_keywords?.length && (
                  <p className="text-xs text-gray-400">데이터 없음</p>
                )}
              </div>
            </div>
            <div className="card">
              <h2 className="section-title mb-3">📉 사라진 키워드</h2>
              <div className="flex flex-wrap gap-2">
                {(trends.declining_keywords || []).map((kw: string) => (
                  <span key={kw} className="badge badge-gray">{kw}</span>
                ))}
                {!trends.declining_keywords?.length && (
                  <p className="text-xs text-gray-400">데이터 없음</p>
                )}
              </div>
            </div>
          </div>

          {/* Vendor mentions */}
          {Object.keys(trends.vendor_mentions || {}).length > 0 && (
            <div className="card">
              <h2 className="section-title mb-4">🏢 벤더/서비스 언급량</h2>
              <div className="flex flex-wrap gap-3">
                {Object.entries(trends.vendor_mentions)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 10)
                  .map(([vendor, count], i) => (
                    <div key={vendor} className="text-center">
                      <div className="text-xs text-gray-500">{vendor}</div>
                      <div
                        className="text-lg font-bold"
                        style={{ color: COLORS[i % COLORS.length] }}
                      >
                        {count as number}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          <div className="card">
            <p className="text-xs text-gray-400">
              분석 기간: {trends.period?.start} ~ {trends.period?.end} · 총 {trends.total_reports}개 리포트
            </p>
          </div>
        </>
      )}
    </div>
  );
}
