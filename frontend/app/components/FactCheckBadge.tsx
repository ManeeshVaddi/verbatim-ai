import { FactCheck } from "@/app/lib/api";

const RATING_COLORS: Record<string, string> = {
  "true": "bg-emerald-400/15 text-emerald-300 border-emerald-400/25",
  "mostly true": "bg-emerald-400/15 text-emerald-300 border-emerald-400/25",
  "half true": "bg-yellow-400/15 text-yellow-300 border-yellow-400/25",
  "mostly false": "bg-orange-400/15 text-orange-300 border-orange-400/25",
  "false": "bg-red-400/15 text-red-300 border-red-400/25",
  "pants on fire": "bg-red-400/15 text-red-300 border-red-400/25",
  "misleading": "bg-orange-400/15 text-orange-300 border-orange-400/25",
};

function ratingColor(rating: string) {
  return RATING_COLORS[rating.toLowerCase()] ?? "bg-white/10 text-white/50 border-white/15";
}

interface Props {
  checks: FactCheck[];
}

export default function FactCheckBadge({ checks }: Props) {
  if (!checks.length) return null;

  return (
    <div className="bg-white/[0.04] rounded-2xl border border-white/8 p-5">
      <p className="text-[10px] uppercase tracking-[0.2em] text-white/25 mb-3">
        Fact-checks
      </p>
      <div className="space-y-2">
        {checks.map((c, i) => (
          <a
            key={i}
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/6 hover:bg-white/[0.07] hover:border-white/12 transition-all"
          >
            <div className="flex items-center gap-3">
              <span
                className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${ratingColor(c.rating)}`}
              >
                {c.rating}
              </span>
              <span className="text-xs text-white/50 font-medium">{c.publisher}</span>
            </div>
            {c.summary && (
              <p className="text-xs text-white/35 leading-relaxed line-clamp-2">{c.summary}</p>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
