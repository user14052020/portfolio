"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float } from "@react-three/drei";
import { useRef } from "react";
import type { Mesh } from "three";

function FloatingShape({ accent }: { accent: string }) {
  const meshRef = useRef<Mesh>(null);

  useFrame((_, delta) => {
    if (!meshRef.current) {
      return;
    }
    meshRef.current.rotation.x += delta * 0.3;
    meshRef.current.rotation.y += delta * 0.45;
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={1.6}>
      <mesh ref={meshRef}>
        <torusKnotGeometry args={[1, 0.34, 180, 32]} />
        <meshStandardMaterial color={accent} roughness={0.2} metalness={0.85} />
      </mesh>
    </Float>
  );
}

export function ThreeScenePlaceholder({
  title,
  sceneKey,
  accent = "#d0a46d"
}: {
  title: string;
  sceneKey: string;
  accent?: string;
}) {
  return (
    <div className="relative h-[260px] overflow-hidden rounded-[24px] border border-white/70 bg-gradient-to-br from-white via-[#f8f1e8] to-[#f2f4f8]">
      <div className="absolute left-5 top-4 z-10">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">{sceneKey}</p>
        <p className="text-sm text-slate-700">{title}</p>
      </div>
      <Canvas camera={{ position: [0, 0, 4.6], fov: 40 }}>
        <ambientLight intensity={1.2} />
        <directionalLight position={[4, 4, 4]} intensity={1.5} />
        <FloatingShape accent={accent} />
        <Environment preset="sunset" />
      </Canvas>
    </div>
  );
}

