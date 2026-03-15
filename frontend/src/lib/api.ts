import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// ---- Dashboard ----
export const getDashboardSummary = () =>
  api.get("/dashboard/summary").then((r) => r.data);

// ---- Sources ----
export const getSources = () => api.get("/sources/").then((r) => r.data);
export const createSource = (data: any) => api.post("/sources/", data).then((r) => r.data);
export const updateSource = (id: number, data: any) =>
  api.patch(`/sources/${id}`, data).then((r) => r.data);
export const toggleSource = (id: number) =>
  api.post(`/sources/${id}/toggle`).then((r) => r.data);
export const deleteSource = (id: number) => api.delete(`/sources/${id}`);

// ---- Articles ----
export const getArticles = (params: Record<string, any> = {}) =>
  api.get("/articles/", { params }).then((r) => r.data);
export const getArticle = (id: number) => api.get(`/articles/${id}`).then((r) => r.data);

// ---- Reports ----
export const getReports = (params?: Record<string, any>) =>
  api.get("/reports/", { params }).then((r) => r.data);
export const getReport = (id: number) => api.get(`/reports/${id}`).then((r) => r.data);
export const getReportVersions = (id: number) =>
  api.get(`/reports/${id}/versions`).then((r) => r.data);
export const getVersionHtml = (reportId: number, versionId: number) =>
  api
    .get(`/reports/${reportId}/versions/${versionId}/html`, { responseType: "text" })
    .then((r) => r.data);
export const approveReport = (id: number) =>
  api.post(`/reports/${id}/approve`).then((r) => r.data);
export const generateReport = (date: string) =>
  api.post("/reports/generate", null, { params: { report_date: date } }).then((r) => r.data);

// ---- Recipients ----
export const getRecipients = (params?: Record<string, any>) =>
  api.get("/recipients/", { params }).then((r) => r.data);
export const createRecipient = (data: any) =>
  api.post("/recipients/", data).then((r) => r.data);
export const updateRecipient = (id: number, data: any) =>
  api.patch(`/recipients/${id}`, data).then((r) => r.data);
export const deleteRecipient = (id: number) => api.delete(`/recipients/${id}`);
export const importCsv = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/recipients/import/csv", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

// ---- Deliveries ----
export const sendReport = (data: any) => api.post("/deliveries/send", data).then((r) => r.data);
export const testSend = (data: any) =>
  api.post("/deliveries/test-send", data).then((r) => r.data);
export const getDeliveries = (params?: Record<string, any>) =>
  api.get("/deliveries/", { params }).then((r) => r.data);

// ---- Analytics ----
export const getTrends = (params: { start_date: string; end_date: string }) =>
  api.get("/analytics/trends", { params }).then((r) => r.data);
export const getLast7Trends = () => api.get("/analytics/trends/last7").then((r) => r.data);
export const getReportDiff = (a: number, b: number) =>
  api.get("/analytics/diff", { params: { report_id_a: a, report_id_b: b } }).then((r) => r.data);

// ---- Jobs ----
export const getJobLogs = (params?: Record<string, any>) =>
  api.get("/jobs/logs", { params }).then((r) => r.data);
export const runCollect = () => api.post("/jobs/run/collect").then((r) => r.data);
export const runReport = (date?: string) =>
  api.post("/jobs/run/report", null, { params: date ? { report_date: date } : {} }).then((r) => r.data);
export const runSend = (reportId: number) =>
  api.post("/jobs/run/send", null, { params: { report_id: reportId } }).then((r) => r.data);
