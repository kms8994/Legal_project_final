export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <section className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 py-6 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between border-b border-[#d8d8cf] pb-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#6d7165]">
              CaseLens
            </p>
            <h1 className="mt-1 text-2xl font-semibold">손해배상 판례 검색</h1>
          </div>
          <span className="hidden rounded border border-[#c7c8bd] px-3 py-1 text-sm text-[#5b5f55] sm:inline">
            MVP 데이터 기준
          </span>
        </header>

        <div className="flex flex-1 items-center py-10">
          <div className="w-full">
            <div className="mb-5 flex w-full max-w-xl rounded border border-[#c7c8bd] bg-white p-1">
              {["조문", "자연어", "사건번호"].map((mode, index) => (
                <button
                  key={mode}
                  className={`h-10 flex-1 text-sm font-medium ${
                    index === 0
                      ? "bg-[#1f3d36] text-white"
                      : "text-[#51564e] hover:bg-[#eeeeea]"
                  }`}
                  type="button"
                >
                  {mode}
                </button>
              ))}
            </div>

            <form className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <label className="sr-only" htmlFor="search">
                판례 검색어
              </label>
              <input
                id="search"
                className="h-14 w-full border border-[#bbbdb1] bg-white px-4 text-base outline-none transition focus:border-[#1f3d36] focus:ring-2 focus:ring-[#1f3d36]/20"
                placeholder="민법 제750조"
                type="search"
              />
              <button
                className="h-14 bg-[#1f3d36] px-8 text-base font-semibold text-white transition hover:bg-[#17312b]"
                type="submit"
              >
                검색
              </button>
            </form>

            <div className="mt-8 grid gap-3 text-sm text-[#555950] sm:grid-cols-3">
              <div className="border-l-2 border-[#aab2a0] pl-3">
                조문 기준 판례를 찾고
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                기준 판례를 선택하고
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                사실관계가 유사한 판례를 비교합니다
              </div>
            </div>
          </div>
        </div>

        <footer className="border-t border-[#d8d8cf] pt-4 text-sm text-[#666b61]">
          CaseLens의 검색 결과와 AI 요약은 참고용 정보입니다. 실제 판단은
          판례 원문, 최신 법령, 전문가 검토로 확인해야 합니다.
        </footer>
      </section>
    </main>
  );
}
