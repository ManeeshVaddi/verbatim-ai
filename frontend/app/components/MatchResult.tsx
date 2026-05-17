import { Match } from "@/app/lib/api";

interface Props {
  match: Match;
  quoteText: string;
}

function highlightQuote(excerpt: string, quote: string): string {
  if (!quote.trim()) return excerpt;
  const words = quote.trim().split(/\s+/).slice(0, 8).join(" ");
  return excerpt.replace(
    new RegExp(`(${words.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"),
    "**$1**"
  );
}

function MatchBadge({ pct }: { pct: number }) {
  if (pct >= 70) return (
    <span className="shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-400/10 text-emerald-300/90 border border-emerald-400/20">
      Strong · {pct}%
    </span>
  );
  if (pct >= 50) return (
    <span className="shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-yellow-400/10 text-yellow-300/90 border border-yellow-400/20">
      Good · {pct}%
    </span>
  );
  return (
    <span className="shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-orange-400/10 text-orange-300/90 border border-orange-400/20">
      Partial · {pct}%
    </span>
  );
}

function formatDate(d: string): string {
  const [y, m, day] = d.split("-").map(Number);
  return new Date(y, m - 1, day).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
}

export default function MatchResult({ match, quoteText }: Props) {
  const pct = Math.round(match.similarity * 100);
  const highlighted = highlightQuote(match.excerpt, quoteText);

  return (
    <div className="bg-white/[0.04] rounded-2xl border border-white/8 p-5">
      <p className="text-[10px] uppercase tracking-[0.2em] text-white/20 mb-3">
        Matched transcript
      </p>

      <div className="flex items-start justify-between gap-3 mb-1">
        <h2
          className="text-base font-semibold text-white/85 leading-snug"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          {match.transcript_title}
        </h2>
        <MatchBadge pct={pct} />
      </div>

      {/* Date + speaker metadata */}
      {(match.speech_date || match.speech_speaker) && (
        <p className="text-[11px] text-white/25 mb-4">
          {match.speech_speaker && <span>{match.speech_speaker}</span>}
          {match.speech_speaker && match.speech_date && <span className="mx-1.5 text-white/15">·</span>}
          {match.speech_date && <span>{formatDate(match.speech_date)}</span>}
        </p>
      )}

      <p className="text-sm text-white/50 leading-relaxed">
        {highlighted.split("**").map((part, i) =>
          i % 2 === 1 ? (
            <mark key={i} className="bg-blue-400/20 text-blue-200/90 rounded px-0.5">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </p>

      <a
        href={match.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block mt-4 text-[11px] text-blue-400/50 hover:text-blue-400/80 transition-colors underline underline-offset-2"
      >
        View original source ↗
      </a>
    </div>
  );
}
