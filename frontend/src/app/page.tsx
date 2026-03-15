"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDashboardSummary, runCollect, runReport } from "@/lib/api";
import { fmtDate, STATUS_LABELS } from "@/lib/utils";
import toast from "react-hot-toast";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

function StatCard({
  label,
  value,
  color = "blue",
  sub,
}: {
  label: string;
  value: string | number | null | undefined;
  color?: string;
  sub?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-600",
    green: "text-green-600",
    red: "text-red-600",
    gray: "text-gray-600",
  };
  return (
    <div className="card">
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${colorMap[color] || "text-gray-900"}`}>
        {value ?? "-"}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSummary,
    refetchInterval: 30_000,
  });

  const collectMut = useMutation({
    mutationFn: runCollect,
    onSuccess: () => {
      toast.success("수집 작업이 큐에 추가됐습니다");
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("작업 시작 실패"),
  });

  const reportMut = useMutation({
    mutationFn: () => runReport(),
    onSuccess: () => toast.success("리포트 생성 작업이 큐에 추가됐습니다"),
    onError: () => toast.error("작업 시작 실패"),
  });

  if (isLoading) return <div className="p-6 text-gray-400">로딩 중...</div>;

  const statusBadge = (status: string | null | undefined) => {
    const map: Record<string, string> = {
      draft: "badge-gray",
      ready: "badge-blue",
      approved: "badge-purple",
      sent: "badge-green",
    };
    return (
      <span className={`badge ${map[status || ""] || "badge-gray"}`}>
        {STATUS_LABELS[status || ""] || status || "없음"}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">대시보드</h1>
        <div className="text-xs text-gray-400">{data?.today}</div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="오늘 수집 기사" value={data?.articles_today} color="blue" />
        <StatCard label="이메일 발송 성공" value={data?.emails_sent_today} color="green" />
        <StatCard label="발송 실패" value={data?.emails_failed_today} color="red" />
        <div className="card">
          <p className="text-xs text-gray-500 font-medium">오늘 리포트 상태</p>
          <div className="mt-2">{statusBadge(data?.report_status)}</div>
          {data?.report_id && (
            <Link
              href={`/reports/${data.report_id}`}
              className="text-xs text-blue-600 hover:underline mt-1 block"
            >
              보기 →
            </Link>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="card">
        <h2 className="section-title mb-4">최근 7일 기사 수집량</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data?.article_trend_7d || []} barSize={28}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick actions */}
        <div className="card">
          <h2 className="section-title mb-4">빠른 실행</h2>
          <div className="space-y-3">
            <button
              onClick={() => collectMut.mutate()}
              disabled={collectMut.isPending}
              className="btn-primary w-full justify-center"
            >
              {collectMut.isPending ? "⏳ 실행 중..." : "📡 기사 수집 지금 실행"}
            </button>
            <button
              onClick={() => reportMut.mutate()}
              disabled={reportMut.isPending}
              className="btn-secondary w-full justify-center"
            >
              {reportMut.isPending ? "⏳ 실행 중..." : "📋 오늘 리포트 생성"}
            </button>
            <Link href="/reports" className="btn-secondary w-full justify-center">
              📨 리포트 발송하기
            </Link>
          </div>
        </div>

        {/* Recent jobs */}
        <div className="card">
          <h2 className="section-title mb-3">최근 작업 로그</h2>
          <div className="space-y-1">
            {(data?.recent_jobs || []).map((job: any) => (
              <div key={job.id} className="flex items-center justify-between py-1.5 border-b border-gray-50">
                <div>
                  <span className="font-medium text-xs">{job.job_type}</span>
                  <span className="text-gray-400 text-xs ml-2">{fmtDate(job.started_at)}</span>
                </div>
                <span
                  className={`badge ${
                    job.status === "success"
                      ? "badge-green"
                      : job.status === "failed"
                      ? "badge-red"
                      : "badge-yellow"
                  }`}
                >
                  {STATUS_LABELS[job.status] || job.status}
                </span>
              </div>
            ))}
            {(!data?.recent_jobs || data.recent_jobs.length === 0) && (
              <p className="text-xs text-gray-400">실행 로그가 없습니다</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
