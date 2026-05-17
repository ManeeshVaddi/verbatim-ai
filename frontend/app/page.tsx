"use client";

import { motion } from "framer-motion";
import QuoteInput from "@/app/components/QuoteInput";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.4, 0.25, 1] as [number, number, number, number] },
});

export default function Home() {
  return (
    <main className="relative min-h-screen w-full flex flex-col items-center">
      {/* Top glow over the mesh */}
      <div className="pointer-events-none fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[350px] rounded-full bg-blue-500/6 blur-[120px] -z-[5]" />

      <div className="flex-1 w-full flex flex-col items-center justify-center pt-28 pb-12 px-4">
        {/* Hero */}
        <div className="text-center mb-10">
          <motion.div
            {...fadeUp(0.1)}
            className="text-7xl text-blue-300/15 leading-none mb-1 select-none"
            style={{ fontFamily: "var(--font-playfair)" }}
            aria-hidden
          >
            ❝
          </motion.div>

          <motion.h1
            {...fadeUp(0.25)}
            className="text-5xl sm:text-[3.75rem] font-semibold text-white leading-tight mb-4 italic tracking-tight"
            style={{ fontFamily: "var(--font-playfair)" }}
          >
            Verbatim
            <span className="text-blue-300 not-italic font-light">.ai</span>
          </motion.h1>

          <motion.p {...fadeUp(0.4)} className="text-white/35 text-sm sm:text-base max-w-sm mx-auto leading-relaxed">
            Paste a political quote — we&apos;ll trace it to the original speech,
            surface the context, and find fact-checks.
          </motion.p>
        </div>

        <motion.div {...fadeUp(0.55)} className="w-full flex justify-center">
          <QuoteInput />
        </motion.div>
      </div>
    </main>
  );
}
