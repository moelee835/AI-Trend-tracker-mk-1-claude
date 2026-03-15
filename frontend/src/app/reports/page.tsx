"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReports, approveReport, generateReport, runSend } from "@/lib/api";
import { fmtDateOnly, STATUS_LABELS } from "@/lib/utils";
import toast from "react-hot-toast";
import Link from "next/link";
import { format } from "date-fns";

export default function ReportsPage() {
  const qc = useQueryClient();
  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => getReports({ limit: 30 }),
  });

  const approveMut = useMutation({
    mutationFn: approveReport,
    onSuccess: () => {
      toast.success("리포트가 승인됐습니다");
      qc.invalidateQueries({ queryKey: ["reports"] });
    },
  });

  const genMut = useMutation({
    mutationFn: (date: string) => generateReport(date),
    onSuccess: () => toast.success("리포트 생성이 큐에 추가됐습니다"),
    onError: () => toast.error("실패"),
  });

  const sendMut = useMutation({
    mutationFn: runSend,
    onSuccess: () => toast.success("발송 작업이 큐에 추가됐습니다"),
    onError: () => toast.error("발송 실패"),
  });

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      draft: "badge-gray",
      ready: "badge-blue",
      approved: "badge-purple",
      sent: "badge-green",
    };
    return <span className={`badge ${map[status] || "badge-gray"}`}>{STATUS_LABELS[status] || status}</span>;
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="page-title">리포트 관리</h1>
        <button
          className="btn-primary"
          onClick={() => genMut.mutate(format(new Date(), "yyyy-MM-dd"))}
          disabled={genMut.isPending}
        >
          + 오늘 리포트 생성
        </button>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="table-header">날짜</th>
              <th className="table-header">상태</th>
              <th className="table-header">포함 기사</th>
              <th className="table-header">버전</th>
              <th className="table-header">생성일</th>
              <th className="table-header">액션</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="table-cell text-gray-400">로딩 중...</td></tr>}
            {reports.map((r: any) => (
              <tr key={r.id} className="table-row">
                <td className="table-cell font-medium">{fmtDateOnly(r.report_date)}</td>
                <td className="table-cell">{statusBadge(r.status)}</td>
                <td className="table-cell">{r.included_article_count}개</td>
                <td className="table-cell">v{r.version_count}</td>
                <td className="table-cell text-xs">{fmtDateOnly(r.created_at)}</td>
                <td className="table-cell">
                  <div className="flex gap-1 flex-wrap">
                    <Link href={`/reports/${r.id}`} className="btn btn-sm btn-secondary">상세</Link>
                    {(r.status === "ready" || r.status === "draft") && (
                      <button
                        className="btn btn-sm bg-purple-100 text-purple-700 hover:bg-purple-200"
                        onClick={() => approveMut.mutate(r.id)}
                      >
                        승인
                      </button>
                    )}
                    {(r.status === "ready" || r.status === "approved") && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => sendMut.mutate(r.id)}
                        disabled={sendMut.isPending}
                      >
                        발송
                      </button>
                    )}
                    {r.status === "sent" && (
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => sendMut.mutate(r.id)}
                      >
                        재발송
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
