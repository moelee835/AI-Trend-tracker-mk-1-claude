import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";
import { ko } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(d: string | Date | null | undefined): string {
  if (!d) return "-";
  try {
    const parsed = typeof d === "string" ? parseISO(d) : d;
    return format(parsed, "yyyy.MM.dd HH:mm", { locale: ko });
  } catch {
    return String(d);
  }
}

export function fmtDateOnly(d: string | Date | null | undefined): string {
  if (!d) return "-";
  try {
    const parsed = typeof d === "string" ? parseISO(d) : d;
    return format(parsed, "yyyy.MM.dd", { locale: ko });
  } catch {
    return String(d);
  }
}

export const STATUS_LABELS: Record<string, string> = {
  draft: "초안",
  ready: "생성완료",
  approved: "승인됨",
  sent: "발송완료",
  pending: "대기중",
  failed: "실패",
  bounced: "반송됨",
  running: "실행중",
  success: "성공",
  partial: "부분성공",
};

export const CATEGORY_LABELS: Record<string, string> = {
  model_llm: "모델/LLM",
  ai_agent: "AI Agent",
  infra_serving: "인프라/서빙",
  opensource_framework: "오픈소스",
  product_launch: "제품 출시",
  research_paper: "연구/논문",
  security_policy: "보안/정책",
  dev_tools: "개발 도구",
  other: "기타",
};
