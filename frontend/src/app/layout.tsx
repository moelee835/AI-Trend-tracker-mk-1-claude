import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Providers } from "./providers";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "AI Newsletter Admin",
  description: "AI 트렌드 뉴스레터 관리자 대시보드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900">
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-56 p-6 overflow-auto">{children}</main>
          </div>
          <Toaster position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
