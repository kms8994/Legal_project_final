import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CaseLens",
  description: "판례 검색과 유사판례 비교를 위한 CaseLens MVP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
