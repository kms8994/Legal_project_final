import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-[#d7dce2] bg-white">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link className="text-xl font-bold text-[#111827]" href="/">
          CaseLens
        </Link>
        <p className="hidden text-sm text-[#667085] sm:block">판례 검색 · 비교 MVP</p>
      </div>
    </header>
  );
}
