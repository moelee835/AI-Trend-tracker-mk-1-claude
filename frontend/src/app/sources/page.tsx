"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSources, createSource, toggleSource, deleteSource } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import toast from "react-hot-toast";

const SOURCE_TYPES = [
  { value: "vendor_blog", label: "벤더 블로그" },
  { value: "research", label: "연구 소스" },
  { value: "opensource", label: "오픈소스" },
  { value: "news_api", label: "뉴스 API" },
  { value: "rss", label: "RSS" },
  { value: "html_scrape", label: "HTML 크롤링" },
];

const STRATEGIES = [
  { value: "rss", label: "RSS" },
  { value: "api", label: "API" },
  { value: "html", label: "HTML" },
  { value: "playwright", label: "Playwright" },
];

function AddSourceModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    source_type: "rss",
    base_url: "",
    feed_url: "",
    poll_strategy: "rss",
    enabled: true,
  });

  const mut = useMutation({
    mutationFn: createSource,
    onSuccess: () => {
      toast.success("소스가 추가됐습니다");
      qc.invalidateQueries({ queryKey: ["sources"] });
      onClose();
    },
    onError: () => toast.error("추가 실패"),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="section-title mb-4">새 소스 추가</h2>
        <div className="space-y-3">
          <div>
            <label className="label">이름</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">소스 유형</label>
              <select className="input" value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
                {SOURCE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="label">수집 전략</label>
              <select className="input" value={form.poll_strategy} onChange={(e) => setForm({ ...form, poll_strategy: e.target.value })}>
                {STRATEGIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Base URL</label>
            <input className="input" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="https://example.com" />
          </div>
          <div>
            <label className="label">Feed URL (RSS/API)</label>
            <input className="input" value={form.feed_url} onChange={(e) => setForm({ ...form, feed_url: e.target.value })} placeholder="https://example.com/rss.xml" />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-5">
          <button className="btn-secondary" onClick={onClose}>취소</button>
          <button
            className="btn-primary"
            onClick={() => mut.mutate(form)}
            disabled={mut.isPending || !form.name || !form.base_url}
          >
            {mut.isPending ? "추가 중..." : "추가"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SourcesPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const { data: sources = [], isLoading } = useQuery({
    queryKey: ["sources"],
    queryFn: getSources,
  });

  const toggleMut = useMutation({
    mutationFn: toggleSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
    onError: () => toast.error("변경 실패"),
  });

  const deleteMut = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => {
      toast.success("삭제됐습니다");
      qc.invalidateQueries({ queryKey: ["sources"] });
    },
    onError: () => toast.error("삭제 실패"),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="page-title">뉴스 소스 관리</h1>
        <button className="btn-primary" onClick={() => setShowAdd(true)}>+ 소스 추가</button>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="table-header">이름</th>
              <th className="table-header">유형</th>
              <th className="table-header">전략</th>
              <th className="table-header">마지막 수집</th>
              <th className="table-header">실패</th>
              <th className="table-header">상태</th>
              <th className="table-header">액션</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="table-cell text-gray-400">로딩 중...</td></tr>
            )}
            {sources.map((s: any) => (
              <tr key={s.id} className="table-row">
                <td className="table-cell font-medium">
                  <div>{s.name}</div>
                  <div className="text-xs text-gray-400 truncate max-w-[200px]">{s.feed_url || s.base_url}</div>
                </td>
                <td className="table-cell">{s.source_type}</td>
                <td className="table-cell">{s.poll_strategy}</td>
                <td className="table-cell text-xs">{fmtDate(s.last_collected_at)}</td>
                <td className="table-cell">
                  {s.failure_count > 0 ? (
                    <span className="badge-red badge">{s.failure_count}</span>
                  ) : (
                    <span className="text-gray-400">0</span>
                  )}
                </td>
                <td className="table-cell">
                  <span className={`badge ${s.enabled ? "badge-green" : "badge-gray"}`}>
                    {s.enabled ? "활성" : "비활성"}
                  </span>
                </td>
                <td className="table-cell">
                  <div className="flex gap-1">
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => toggleMut.mutate(s.id)}
                    >
                      {s.enabled ? "비활성화" : "활성화"}
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => {
                        if (confirm(`"${s.name}" 소스를 삭제하시겠습니까?`)) {
                          deleteMut.mutate(s.id);
                        }
                      }}
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAdd && <AddSourceModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}
