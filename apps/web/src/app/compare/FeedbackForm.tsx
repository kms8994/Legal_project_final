"use client";

import { FormEvent, useState } from "react";

type FeedbackFormProps = {
  baseCaseId: string;
  compareCaseId: string;
};

const LABELS = [
  { label: "관련 있음", value: "relevant" },
  { label: "관련 낮음", value: "not_relevant" },
  { label: "사실관계 다름", value: "facts_not_similar" },
  { label: "중요 사실 누락", value: "material_fact_missed" },
  { label: "조문 오류", value: "wrong_statute" },
  { label: "결론 차이 오류", value: "outcome_not_different" },
  { label: "요약 오류", value: "summary_error" },
  { label: "근거 필요", value: "source_needed" },
] as const;

type FeedbackLabel = (typeof LABELS)[number]["value"];

export function FeedbackForm({ baseCaseId, compareCaseId }: FeedbackFormProps) {
  const [label, setLabel] = useState<FeedbackLabel>("relevant");
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setStatus(null);

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          base_case_id: baseCaseId,
          compare_case_id: compareCaseId,
          label,
          comment: comment.trim() || null,
          user_id: "anonymous",
        }),
      });

      if (!response.ok) {
        throw new Error("피드백 저장에 실패했습니다.");
      }

      setComment("");
      setStatus("피드백을 저장했습니다.");
    } catch {
      setStatus("피드백을 저장하지 못했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5">
      <h2 className="text-sm font-bold text-[#111827]">비교 결과 피드백</h2>
      <form className="mt-3 grid gap-3" onSubmit={handleSubmit}>
        <div className="grid gap-2 sm:grid-cols-4">
          {LABELS.map((item) => (
            <label
              className={`cursor-pointer rounded-[6px] border px-3 py-2 text-sm transition ${
                label === item.value
                  ? "border-[#2563eb] bg-[#eff6ff] font-semibold text-[#2563eb]"
                  : "border-[#d7dce2] text-[#526070] hover:border-[#b9c2cf]"
              }`}
              key={item.value}
            >
              <input
                checked={label === item.value}
                className="sr-only"
                name="label"
                onChange={() => setLabel(item.value)}
                type="radio"
                value={item.value}
              />
              {item.label}
            </label>
          ))}
        </div>
        <textarea
          className="min-h-24 rounded-[6px] border border-[#b9c2cf] bg-white px-3 py-2 text-sm outline-none transition focus:border-[#2563eb] focus:ring-3 focus:ring-[#2563eb]/15"
          maxLength={2000}
          onChange={(event) => setComment(event.target.value)}
          placeholder="비교 결과가 맞았는지, 어떤 점이 부족했는지 적어주세요."
          value={comment}
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-[6px] bg-[#2563eb] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#1d4ed8] disabled:bg-[#9aa8bd]"
            disabled={isSaving}
            type="submit"
          >
            {isSaving ? "저장 중" : "피드백 제출"}
          </button>
          {status ? <p className="text-sm font-medium text-[#667085]">{status}</p> : null}
        </div>
      </form>
    </section>
  );
}
