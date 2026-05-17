interface Props {
  summary: string;
}

export default function ContextCard({ summary }: Props) {
  return (
    <div className="bg-white/[0.04] rounded-2xl border border-blue-400/15 p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-300/70">
          AI Context
        </span>
        <span className="text-[10px] text-white/20">· Powered by Gemini</span>
      </div>
      <p
        className="text-sm text-white/75 leading-relaxed"
        style={{ fontFamily: "var(--font-playfair)" }}
      >
        {summary}
      </p>
      <p className="mt-3 text-[10px] text-white/20 leading-relaxed">
        Generated from the matched transcript. Neutral — no editorial opinion.
      </p>
    </div>
  );
}
