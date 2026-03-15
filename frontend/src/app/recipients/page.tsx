"use client";
import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRecipients, createRecipient, updateRecipient, deleteRecipient, importCsv } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import toast from "react-hot-toast";
import { useDropzone } from "react-dropzone";

function CsvImport({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    setFile(accepted[0] || null);
  }, []);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    maxFiles: 1,
  });

  const mut = useMutation({
    mutationFn: () => importCsv(file!),
    onSuccess: (data) => {
      toast.success(`${data.created}명 등록, ${data.skipped}명 스킵`);
      qc.invalidateQueries({ queryKey: ["recipients"] });
      onClose();
    },
    onError: () => toast.error("가져오기 실패"),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="section-title mb-4">CSV 가져오기</h2>
        <p className="text-xs text-gray-500 mb-3">형식: email, name, tags (tags는 세미콜론으로 구분)</p>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <input {...getInputProps()} />
          {file ? (
            <p className="text-sm font-medium text-green-600">✅ {file.name}</p>
          ) : (
            <p className="text-sm text-gray-500">CSV 파일을 드래그하거나 클릭하여 선택</p>
          )}
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button className="btn-secondary" onClick={onClose}>취소</button>
          <button
            className="btn-primary"
            disabled={!file || mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "가져오는 중..." : "가져오기"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RecipientsPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [showCsv, setShowCsv] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");

  const { data: recipients = [], isLoading } = useQuery({
    queryKey: ["recipients"],
    queryFn: () => getRecipients(),
  });

  const createMut = useMutation({
    mutationFn: createRecipient,
    onSuccess: () => {
      toast.success("추가됐습니다");
      qc.invalidateQueries({ queryKey: ["recipients"] });
      setShowAdd(false);
      setNewEmail("");
      setNewName("");
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, subscribed }: { id: number; subscribed: boolean }) =>
      updateRecipient(id, { subscribed }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recipients"] }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteRecipient,
    onSuccess: () => {
      toast.success("삭제됐습니다");
      qc.invalidateQueries({ queryKey: ["recipients"] });
    },
  });

  const subscribedCount = recipients.filter((r: any) => r.subscribed).length;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">수신자 관리</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            총 {recipients.length}명 · 구독 중 {subscribedCount}명
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setShowCsv(true)}>📂 CSV 가져오기</button>
          <button className="btn-primary" onClick={() => setShowAdd(true)}>+ 수신자 추가</button>
        </div>
      </div>

      {showAdd && (
        <div className="card">
          <h2 className="section-title mb-3">새 수신자 추가</h2>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="label">이메일 *</label>
              <input
                className="input"
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="user@example.com"
              />
            </div>
            <div className="flex-1">
              <label className="label">이름</label>
              <input
                className="input"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="홍길동"
              />
            </div>
            <button
              className="btn-primary"
              disabled={!newEmail || createMut.isPending}
              onClick={() => createMut.mutate({ email: newEmail, name: newName || undefined })}
            >
              추가
            </button>
            <button className="btn-secondary" onClick={() => setShowAdd(false)}>취소</button>
          </div>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="table-header">이메일</th>
              <th className="table-header">이름</th>
              <th className="table-header">태그</th>
              <th className="table-header">구독 상태</th>
              <th className="table-header">등록일</th>
              <th className="table-header">액션</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="table-cell text-gray-400">로딩 중...</td></tr>}
            {recipients.map((r: any) => (
              <tr key={r.id} className="table-row">
                <td className="table-cell font-medium">{r.email}</td>
                <td className="table-cell">{r.name || "-"}</td>
                <td className="table-cell">
                  <div className="flex gap-1 flex-wrap">
                    {(r.tags || []).map((t: string) => (
                      <span key={t} className="badge badge-blue">{t}</span>
                    ))}
                  </div>
                </td>
                <td className="table-cell">
                  <span className={`badge ${r.subscribed ? "badge-green" : "badge-gray"}`}>
                    {r.subscribed ? "구독중" : "구독취소"}
                  </span>
                </td>
                <td className="table-cell text-xs">{fmtDate(r.created_at)}</td>
                <td className="table-cell">
                  <div className="flex gap-1">
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => toggleMut.mutate({ id: r.id, subscribed: !r.subscribed })}
                    >
                      {r.subscribed ? "구독취소" : "구독복원"}
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => {
                        if (confirm(`${r.email}을 삭제하시겠습니까?`)) deleteMut.mutate(r.id);
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

      {showCsv && <CsvImport onClose={() => setShowCsv(false)} />}
    </div>
  );
}
