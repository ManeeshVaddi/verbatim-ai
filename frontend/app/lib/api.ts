const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface FactCheck {
  publisher: string;
  rating: string;
  url: string;
  summary: string;
}

export interface Match {
  transcript_title: string;
  source_url: string;
  excerpt: string;
  similarity: number;
  speech_date?: string;
  speech_speaker?: string;
}

export interface QuoteResult {
  quote_id: number;
  status: "processing" | "complete" | "no_match" | "error";
  quote_text?: string;
  speaker?: string;
  match?: Match;
  summary?: string;
  fact_checks: FactCheck[];
}

export async function pingBackend(): Promise<void> {
  try {
    await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(10000) });
  } catch {
    // best-effort warm-up, ignore errors
  }
}

export async function submitQuote(text: string, speaker: string): Promise<{ quote_id: number }> {
  const res = await fetch(`${API_URL}/api/quotes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, speaker: speaker || null }),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  const data: QuoteResult = await res.json();
  return { quote_id: data.quote_id };
}

export async function pollResult(quoteId: number): Promise<QuoteResult> {
  const res = await fetch(`${API_URL}/api/quotes/${quoteId}`);
  if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
  return res.json();
}

export async function waitForResult(quoteId: number, timeoutMs = 30000): Promise<QuoteResult> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await pollResult(quoteId);
    if (result.status !== "processing") return result;
    await new Promise((r) => setTimeout(r, 1200));
  }
  throw new Error("Timed out waiting for result");
}
