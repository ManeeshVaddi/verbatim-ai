"use client";

import { MeshGradient } from "@paper-design/shaders-react";

export default function AnimatedBackground() {
  return (
    <>
      {/* Primary mesh — deep navy/blue */}
      <MeshGradient
        className="fixed inset-0 w-full h-full -z-10"
        colors={["#000000", "#050e1e", "#091828", "#0d2038", "#000000"]}
        speed={0.12}
        backgroundColor="#000000"
      />
      {/* Wireframe overlay — subtle blue veins */}
      <MeshGradient
        className="fixed inset-0 w-full h-full -z-10 opacity-25"
        colors={["#000000", "#0a1830", "#102840", "#000000"]}
        speed={0.08}
        wireframe
        backgroundColor="transparent"
      />
    </>
  );
}
