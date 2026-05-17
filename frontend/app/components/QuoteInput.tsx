"use client";

import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { submitQuote } from "@/app/lib/api";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ArrowUpIcon } from "lucide-react";

const SAMPLES = [
  {
    text: "Ask not what your country can do for you, ask what you can do for your country.",
    speaker: "John F. Kennedy",
  },
  {
    text: "The only thing we have to fear is fear itself.",
    speaker: "Franklin D. Roosevelt",
  },
  {
    text: "Mr. Gorbachev, tear down this wall!",
    speaker: "Ronald Reagan",
  },
  {
    text: "We shall overcome because the arc of the moral universe is long but it bends toward justice.",
    speaker: "Lyndon B. Johnson",
  },
];

function useAutoResize(minH: number, maxH: number) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const adjust = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = `${minH}px`;
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
  }, [minH, maxH]);
  useEffect(() => {
    if (ref.current) ref.current.style.height = `${minH}px`;
  }, [minH]);
  return { ref, adjust };
}

export default function QuoteInput() {
  const router = useRouter();
  const [quote, setQuote] = useState("");
  const [speaker, setSpeaker] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { ref: textareaRef, adjust } = useAutoResize(56, 180);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!quote.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { quote_id } = await submitQuote(quote.trim(), speaker.trim());
      router.push(`/result/${quote_id}`);
    } catch {
      setError("Failed to submit. Is the backend running?");
      setLoading(false);
    }
  }

  function fillSample(s: { text: string; speaker: string }) {
    setQuote(s.text);
    setSpeaker(s.speaker);
    setError(null);
    setTimeout(adjust, 0);
  }

  const canSubmit = quote.trim().length > 0 && !loading;

  return (
    <div className="w-full max-w-2xl px-4">
      <form onSubmit={handleSubmit}>
        {/* Glass card */}
        <div
          className={cn(
            "relative rounded-2xl border transition-all duration-300",
            focused
              ? "border-blue-500/40 bg-white/[0.07] shadow-[0_0_40px_rgba(59,130,246,0.12)]"
              : "border-white/10 bg-white/[0.04] shadow-xl shadow-black/40"
          )}
        >
          {/* Speaker row */}
          <div className="flex items-center gap-2 px-4 pt-4 pb-2 border-b border-white/[0.07]">
            <span className="text-[10px] uppercase tracking-widest text-white/20 shrink-0">
              Speaker
            </span>
            <input
              type="text"
              value={speaker}
              onChange={(e) => setSpeaker(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="optional — e.g. President Kennedy"
              className="flex-1 bg-transparent text-xs text-white/60 placeholder:text-white/20 outline-none"
            />
          </div>

          {/* Quote textarea */}
          <Textarea
            ref={textareaRef}
            value={quote}
            onChange={(e) => { setQuote(e.target.value); adjust(); }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit(e as unknown as FormEvent);
            }}
            placeholder="Paste a verbatim political quote..."
            className={cn(
              "w-full px-4 py-3 resize-none border-none rounded-none bg-transparent",
              "text-white/90 text-base leading-relaxed",
              "focus-visible:ring-0 focus-visible:ring-offset-0",
              "placeholder:text-white/20 min-h-[56px]"
            )}
            style={{
              overflow: "hidden",
              fontFamily: "var(--font-playfair)",
              fontStyle: quote ? "italic" : "normal",
            }}
          />

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.05]">
            <p className="text-[10px] text-white/15">
              {canSubmit ? "⌘↵ to submit" : ""}
            </p>
            <button
              type="submit"
              disabled={!canSubmit}
              className={cn(
                "flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200",
                canSubmit
                  ? "bg-blue-500 hover:bg-blue-400 text-white shadow-lg shadow-blue-500/30 scale-100"
                  : "bg-white/8 text-white/20 cursor-not-allowed scale-95"
              )}
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
              ) : (
                <ArrowUpIcon className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-2 text-red-400/70 text-xs text-center">{error}</p>
        )}
      </form>

      {/* Sample quotes */}
      <div className="mt-5">
        <p className="text-center text-[10px] uppercase tracking-[0.25em] text-white/20 mb-3">
          Try a famous quote
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {SAMPLES.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => fillSample(s)}
              className="text-left px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.07] hover:bg-white/[0.07] hover:border-blue-400/25 transition-all duration-200 group"
            >
              <p
                className="text-xs text-white/45 leading-snug line-clamp-2 group-hover:text-white/70 transition-colors italic"
                style={{ fontFamily: "var(--font-playfair)" }}
              >
                &ldquo;{s.text}&rdquo;
              </p>
              <p className="text-[10px] text-blue-400/40 mt-1.5 group-hover:text-blue-400/70 transition-colors">
                — {s.speaker}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
