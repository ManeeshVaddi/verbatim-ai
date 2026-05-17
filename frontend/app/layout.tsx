import type { Metadata } from "next";
import { Geist, Geist_Mono, Playfair_Display } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import AnimatedBackground from "@/components/AnimatedBackground";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Verbatim.ai — Political quotes, in context",
  description:
    "Paste a political quote and trace it to the verified source transcript, with neutral AI context and fact-checks.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${playfair.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#000000] text-white">
        <AnimatedBackground />

        {/* Header */}
        <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-black/30 backdrop-blur-xl">
          <div className="max-w-5xl mx-auto px-5 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <span
                className="text-xl font-semibold tracking-tight text-white group-hover:text-blue-200 transition-colors"
                style={{ fontFamily: "var(--font-playfair)" }}
              >
                Verbatim
                <span className="text-blue-400 italic font-light">.ai</span>
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-400/10 text-amber-300/70 border border-amber-400/15 tracking-wide">
                prototype
              </span>
            </Link>

            <span className="text-[11px] text-white/20 hidden sm:block">
              ~55 transcripts · Miller Center
            </span>
          </div>
        </header>

        <div className="flex-1 flex flex-col">{children}</div>

        {/* Footer */}
        <footer className="relative z-10 border-t border-white/[0.05] py-5 text-center backdrop-blur-sm">
          <p className="text-[11px] text-white/25 mb-1">
            <span className="text-amber-300/50 font-medium">Prototype — not a production tool.</span>
            {" "}Database covers ~55 transcripts. Results may be incomplete or imprecise.
          </p>
          <p className="text-[11px] text-white/15">
            Transcripts from{" "}
            <a href="https://millercenter.org" target="_blank" rel="noopener noreferrer"
              className="hover:text-white/40 underline underline-offset-2 transition-colors">
              Miller Center
            </a>
            {" · "}AI by Gemini{" · "}Built for civic transparency
          </p>
        </footer>
      </body>
    </html>
  );
}
