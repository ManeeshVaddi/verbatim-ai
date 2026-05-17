"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { waitForResult, QuoteResult } from "@/app/lib/api";
import MatchResult from "@/app/components/MatchResult";
import ContextCard from "@/app/components/ContextCard";
import FactCheckBadge from "@/app/components/FactCheckBadge";

function Pulse({ className }: { className: string }) {
  return <div className={`rounded animate-pulse bg-white/[0.07] ${className}`} />;
}

function Skeleton() {
  return (
    <div className="w-full space-y-4 pt-4">
      <div className="bg-white/[0.04] rounded-2xl border border-white/8 p-5 space-y-3">
        <Pulse className="h-2 w-20" />
        <Pulse className="h-5 w-3/4" />
        <Pulse className="h-4 w-1/2" />
      </div>
      <div className="bg-white/[0.04] rounded-2xl border border-white/8 p-5 space-y-3">
        <div className="flex justify-between items-start gap-3">
          <Pulse className="h-4 w-2/3" />
          <Pulse className="h-6 w-24 rounded-full shrink-0" />
        </div>
        <Pulse className="h-3 w-full" />
        <Pulse className="h-3 w-full" />
        <Pulse className="h-3 w-4/5" />
      </div>
      <div className="bg-white/[0.04] rounded-2xl border border-blue-400/10 p-5 space-y-3">
        <Pulse className="h-2 w-16" />
        <Pulse className="h-3 w-full" />
        <Pulse className="h-3 w-full" />
        <Pulse className="h-3 w-3/5" />
      </div>
      <p className="text-center text-[11px] text-white/20 animate-pulse pt-2">
        Searching transcripts and generating context…
      </p>
    </div>
  );
}

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, delay, ease: [0.25, 0.4, 0.25, 1] },
});

export default function ResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [result, setResult] = useState<QuoteResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    waitForResult(Number(params.id))
      .then(setResult)
      .catch((e) => setError(e.message));
  }, [params.id]);

  const noMatch = result && (result.status === "no_match" || result.status === "error" || !result.match);

  return (
    <main className="relative min-h-screen flex flex-col items-center px-4 pt-20 pb-16">
      <div className="pointer-events-none fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[280px] rounded-full bg-blue-500/5 blur-[100px] -z-[5]" />

      <div className="w-full max-w-2xl">
        <button
          onClick={() => router.push("/")}
          className="mb-6 mt-4 text-xs text-white/25 hover:text-white/55 transition-colors tracking-wide"
        >
          ← New search
        </button>

        {error && (
          <div className="text-center py-16">
            <p className="text-red-400/70 text-sm mb-2">Something went wrong</p>
            <p className="text-white/25 text-xs mb-6">{error}</p>
            <button
              onClick={() => router.push("/")}
              className="px-4 py-2 bg-white/[0.05] hover:bg-white/10 border border-white/10 text-white/50 text-sm rounded-xl transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {!result && !error && <Skeleton />}

        {result && (
          <div className="flex flex-col gap-4">
            {/* Original quote */}
            {result.quote_text && (
              <motion.div {...fadeUp(0)} className="bg-white/[0.04] rounded-2xl border border-white/8 p-5">
                <p className="text-[10px] uppercase tracking-[0.2em] text-white/20 mb-3">
                  Submitted quote
                </p>
                <blockquote
                  className="text-lg text-white/85 leading-relaxed border-l-2 border-blue-400/40 pl-4 italic"
                  style={{ fontFamily: "var(--font-playfair)" }}
                >
                  &ldquo;{result.quote_text}&rdquo;
                </blockquote>
                {result.speaker && (
                  <p className="mt-2 text-sm text-white/35" style={{ fontFamily: "var(--font-playfair)" }}>
                    — {result.speaker}
                  </p>
                )}
              </motion.div>
            )}

            {noMatch ? (
              <motion.div
                {...fadeUp(0.1)}
                className="text-center py-14 bg-white/[0.03] rounded-2xl border border-white/8 px-6"
              >
                <p className="text-3xl mb-4">📭</p>
                <p className="text-white/75 font-medium mb-2 text-lg" style={{ fontFamily: "var(--font-playfair)" }}>
                  No transcript match found
                </p>
                <p className="text-white/30 text-sm max-w-sm mx-auto mb-6 leading-relaxed">
                  This quote may not be in our database, or may be phrased differently from the original.
                  Our prototype covers ~55 major speeches — try a verbatim famous quote.
                </p>
                <button
                  onClick={() => router.push("/")}
                  className="px-5 py-2.5 bg-blue-500/70 hover:bg-blue-500/90 text-white text-sm rounded-xl font-medium transition-colors"
                >
                  Try a sample quote
                </button>
              </motion.div>
            ) : result.match ? (
              <>
                <motion.div {...fadeUp(0.1)}><MatchResult match={result.match} quoteText={result.quote_text ?? ""} /></motion.div>
                {result.summary && <motion.div {...fadeUp(0.2)}><ContextCard summary={result.summary} /></motion.div>}
                {result.fact_checks?.length > 0 && (
                  <motion.div {...fadeUp(0.3)}><FactCheckBadge checks={result.fact_checks} /></motion.div>
                )}
              </>
            ) : null}
          </div>
        )}
      </div>
    </main>
  );
}
