"use client";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReport, getReportVersions, getVersionHtml, approveReport } from "@/lib/api";
import { fmtDate, STATUS_LABELS } from "@/lib/utils";
import toast from "react-hot-toast";
import { useState } from "react";
import Link from "next/link";

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const reportId = Number(id);
  const qc = useQueryClient();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  const { data: report } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => getReport(reportId),
  });

  const { data: versions = [] } = useQuery({
    queryKey: ["report-versions", reportId],
    queryFn: () => getReportVersions(reportId),
    onSuccess: (data: any[]) => {
      if (data.length && !selectedVersion) {
        const active = data.find((v: any) => v.is_active) || data[0];
        setSelectedVersion(active.id);
      }
    },
  });

  const { data: htmlContent } = useQuery({
    queryKey: ["version-html", reportId, selectedVersion],
    queryFn: () => getVersionHtml(reportId, selectedVersion!),
    enabled: !!selectedVersion,
  });

  const approveMut = useMutation({
    mutationFn: () => approveReport(reportId),
    onSuccess: () => {
      toast.success("승인됐습니다");
      qc.invalidateQueries({ queryKey: ["report", reportId] });
    },
  });

  if (!report) return <div className="p-6 text-gray-400">로딩 중...</div>;

  const statusMap: Record<string, string> = {
    draft: "badge-gray", ready: "badge-blue", approved: "badge-purple", sent: "badge-green"
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link href="/reports" className="text-gray-400 hover:text-gray-600">← 목록</Link>
        <h1 className="page-title">{report.report_date} 리포트</h1>
        <span className={`badge ${statusMap[report.status] || "badge-gray"}`}>
          {STATUS_LABELS[report.status] || report.status}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-xs text-gray-500">포함 기사</p>
          <p className="text-2xl font-bold text-blue-600">{report.included_article_count}</p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-500">버전 수</p>
          <p className="text-2xl font-bold">{report.version_count}</p>
        </div>
        <div className="card col-span-2 flex items-center gap-3">
          {report.status !== "approved" && report.status !== "sent" && (
            <button className="btn-primary" onClick={() => approveMut.mutate()}>
              ✅ 승인
            </button>
          )}
          <Link href={`/reports/${reportId}/send`} className="btn-secondary">
            📨 발송 설정
          </Link>
        </div>
      </div>

      {/* Version selector */}
      {versions.length > 0 && (
        <div className="card">
          <h2 className="section-title mb-3">버전 선택</h2>
          <div className="flex gap-2 flex-wrap">
            {versions.map((v: any) => (
              <button
                key={v.id}
                onClick={() => setSelectedVersion(v.id)}
                className={`btn btn-sm ${selectedVersion === v.id ? "btn-primary" : "btn-secondary"}`}
              >
                v{v.version_number} {v.is_active && "★"}{v.edited_by_operator ? " (편집됨)" : ""}
              </button>
            ))}
          </div>
          {versions.find((v: any) => v.id === selectedVersion) && (
            <div className="mt-3 text-xs text-gray-500">
              <span>생성: {fmtDate(versions.find((v: any) => v.id === selectedVersion)?.generated_at)}</span>
              <span className="ml-3">모델: {versions.find((v: any) => v.id === selectedVersion)?.llm_model}</span>
            </div>
          )}
        </div>
      )}

      {/* HTML Preview */}
      {htmlContent && (
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <h2 className="section-title">이메일 미리보기</h2>
            {selectedVersion && (
              <a
                href={`/api/v1/reports/${reportId}/versions/${selectedVersion}/html`}
                target="_blank"
                className="text-xs text-blue-600 hover:underline"
              >
                새 탭에서 열기 →
              </a>
            )}
          </div>
          <iframe
            srcDoc={htmlContent}
            className="w-full border-0"
            style={{ height: "600px" }}
            sandbox="allow-same-origin"
          />
        </div>
      )}
    </div>
  );
}
