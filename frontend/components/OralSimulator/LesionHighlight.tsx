"use client";

import { Html } from "@react-three/drei";
import type { LesionRegion } from "./useOralModel";

interface LesionHighlightProps {
  lesion: LesionRegion;
  position: [number, number, number];
  onClick?: (lesion: LesionRegion) => void;
}

export default function LesionHighlight({ lesion, position, onClick }: LesionHighlightProps) {
  return (
    <group position={position}>
      {/* Pulsing sphere marker */}
      <mesh onClick={() => onClick?.(lesion)}>
        <sphereGeometry args={[0.04, 16, 16]} />
        <meshStandardMaterial
          color={lesion.highlight_color}
          transparent
          opacity={0.75}
          emissive={lesion.highlight_color}
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* HTML label — always faces camera */}
      <Html distanceFactor={4} center>
        <div
          className="pointer-events-none select-none whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold text-white shadow-md"
          style={{ backgroundColor: lesion.highlight_color, opacity: 0.9 }}
        >
          {lesion.label}
        </div>
      </Html>
    </group>
  );
}
