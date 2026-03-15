"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getJobLogs, runCollect, runReport, runSend } from "@/lib/api";
import { fmtDate, STATUS_LABELS } from "@/lib/utils";
import toast from "react-hot-toast";

export default function JobsPage() {
  const qc = useQueryClient();
  const { data: logs = [], isLoading, refetch } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => getJobLogs({ limit: 100 }),
    refetchInterval: 10_000,
  });

  const collectMut = useMutation({
    mutationFn: runCollect,
    onSuccess: () => { toast.success("수집 시작됨"); refetch(); },
    onError: () => toast.error("실패"),
  });
  const reportMut = useMutation({
    mutationFn: () => runReport(),
    onSuccess: () => { toast.success("리포트 생성 시작됨"); refetch(); },
    onError: () => toast.error("실패"),
  });

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      running: "badge-yellow", success: "badge-green",
      failed: "badge-red", partial: "badge-yellow",
    };
    return <span className={`badge ${map[status] || "badge-gray"}`}>{STATUS_LABELS[status] || status}</span>;
  };

  const typeLabel: Record<string, string> = {
    collect: "📡 기사 수집",
    generate_report: "📋 리포트 생성",
    send_email: "📧 이메일 발송",
    manual_resend: "🔄 재발송",
    analyze: "🔍 분석",
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="page-title">작업 로그</h1>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => collectMut.mutate()} disabled={collectMut.isPending}>
            📡 수집 실행
          </button>
          <button className="btn-secondary" onClick={() => reportMut.mutate()} disabled={reportMut.isPending}>
            📋 리포트 생성
          </button>
          <button className="btn-secondary" onClick={() => refetch()}>🔄 새로고침</button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="table-header">ID</th>
              <th className="table-header">작업 유형</th>
              <th className="table-header">상태</th>
              <th className="table-header">트리거</th>
              <th className="table-header">시작 시각</th>
              <th className="table-header">소요 시간</th>
              <th className="table-header">결과 요약</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={7} className="table-cell text-gray-400">로딩 중...</td></tr>}
            {logs.map((log: any) => (
              <tr key={log.id} className="table-row">
                <td className="table-cell text-gray-400 font-mono text-xs">#{log.id}</td>
                <td className="table-cell font-medium">{typeLabel[log.job_type] || log.job_type}</td>
                <td className="table-cell">{statusBadge(log.status)}</td>
                <td className="table-cell text-xs">{log.triggered_by}</td>
                <td className="table-cell text-xs">{fmtDate(log.started_at)}</td>
                <td className="table-cell text-xs">
                  {log.duration_seconds != null ? `${log.duration_seconds.toFixed(1)}s` : "-"}
                </td>
                <td className="table-cell text-xs">
                  {log.error_detail ? (
                    <span className="text-red-500 truncate max-w-[200px] block">{log.error_detail}</span>
                  ) : (
                    <span className="text-gray-500">
                      {Object.entries(log.result_summary || {})
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(", ")}
                    </span>
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
