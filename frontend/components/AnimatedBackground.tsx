"use client";

import { MeshGradient } from "@paper-design/shaders-react";

export default function AnimatedBackground() {
  return (
    <MeshGradient
      className="fixed inset-0 w-full h-full -z-10"
      colors={["#000000", "#050e1e", "#091828", "#0d2038", "#020a14"]}
      speed={0.1}
      distortion={0.3}
      swirl={0.2}
    />
  );
}
