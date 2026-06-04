import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CaseLens",
  description: "손해배상 판례 검색과 비교 도구",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
