"use client";

import { FormEvent, useState } from "react";

type FeedbackFormProps = {
  baseCaseId: string;
  compareCaseId: string;
};

const LABELS = [
  { label: "Relevant", value: "relevant" },
  { label: "Not relevant", value: "not_relevant" },
  { label: "Facts differ", value: "facts_not_similar" },
  { label: "Missed fact", value: "material_fact_missed" },
  { label: "Wrong statute", value: "wrong_statute" },
  { label: "Outcome issue", value: "outcome_not_different" },
  { label: "Summary error", value: "summary_error" },
  { label: "Need source", value: "source_needed" },
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
        throw new Error("Feedback save failed.");
      }

      setComment("");
      setStatus("Feedback saved.");
    } catch {
      setStatus("Feedback could not be saved.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">Feedback</h2>
      <form className="mt-3 grid gap-3" onSubmit={handleSubmit}>
        <div className="grid gap-2 sm:grid-cols-4">
          {LABELS.map((item) => (
            <label
              className={`border px-3 py-2 text-sm ${
                label === item.value
                  ? "border-[#1f3d36] bg-[#eef0e8] text-[#1f3d36]"
                  : "border-[#d3d4ca] text-[#555950]"
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
          className="min-h-24 border border-[#bbbdb1] bg-white px-3 py-2 text-sm outline-none focus:border-[#1f3d36] focus:ring-2 focus:ring-[#1f3d36]/20"
          maxLength={2000}
          onChange={(event) => setComment(event.target.value)}
          placeholder="Optional note"
          value={comment}
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="bg-[#1f3d36] px-4 py-2 text-sm font-semibold text-white hover:bg-[#17312b] disabled:bg-[#87918b]"
            disabled={isSaving}
            type="submit"
          >
            {isSaving ? "Saving..." : "Submit feedback"}
          </button>
          {status ? <p className="text-sm text-[#666b61]">{status}</p> : null}
        </div>
      </form>
    </section>
  );
}
