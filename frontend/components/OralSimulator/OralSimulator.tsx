"use client";

import React, { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment, Center } from "@react-three/drei";
import LesionHighlight from "./LesionHighlight";
import ToothMap from "./ToothMap";
import { useOralModel, useRevealedLesions } from "./useOralModel";
import type { LesionRegion, OralModelData } from "./useOralModel";

// Anatomical positions for each region in a unit-normalized dental arch coordinate space
// (origin = arch center, +Z = anterior, +Y = superior, ±X = lateral).
// Populated from clinical anatomy; precise values will be refined from GLB mesh centroids.
const DEFAULT_LESION_POSITIONS: Record<string, [number, number, number]> = {
  // Buccal mucosa
  bukkal_mukoza_sag: [-0.35, 0.0, 0.05],
  bukkal_mukoza_sol: [0.35, 0.0, 0.05],
  bukkal_mukoza_eritroplaki: [-0.32, 0.05, 0.1],
  // Tongue
  dil_ucu: [0, -0.12, 0.4],
  dil_lateral: [0.15, -0.1, 0.1],
  dil_dorsum: [0, -0.05, 0.1],
  // Palate
  damak: [0, 0.2, 0.0],
  yumusak_damak: [0, 0.15, -0.2],
  // Gingiva (legacy key kept for back-compat)
  dis_eti: [0, -0.12, 0.1],
  dis_eti_ust: [0, 0.07, 0.25],
  dis_eti_ust_arka: [-0.25, 0.05, -0.05],
  dis_eti_alt: [0, -0.22, 0.15],
  dis_eti_alt_on: [0, -0.2, 0.3],
  dis_eti_nekrotik: [0.2, -0.2, 0.0],
  // Lips
  dudak_cinvar: [0, 0.02, 0.48],
  dudak_ici: [0, 0.0, 0.38],
  // Bone / jaw
  kemik_ekspoze_alt: [-0.2, -0.28, 0.0],
  // Throat / posterior
  tonsil: [0.2, 0.0, -0.35],
};

function fallbackPosition(lesion: LesionRegion): [number, number, number] {
  if (lesion.position) return lesion.position;
  return DEFAULT_LESION_POSITIONS[lesion.region_id] ?? [0, 0, 0.2];
}

interface GLBModelProps {
  url: string;
  revealedLesions: LesionRegion[];
  onLesionClick: (lesion: LesionRegion) => void;
}

function GLBModel({ url, revealedLesions, onLesionClick }: GLBModelProps) {
  const { scene } = useGLTF(url);
  return (
    <group>
      {/* Center auto-centers the model bounding box at the scene origin */}
      <Center>
        <primitive object={scene} />
      </Center>
      {revealedLesions.map((lesion) => (
        <LesionHighlight
          key={lesion.region_id}
          lesion={lesion}
          position={fallbackPosition(lesion)}
          onClick={onLesionClick}
        />
      ))}
    </group>
  );
}

function PlaceholderModel({ revealedLesions, onLesionClick }: Omit<GLBModelProps, "url">) {
  return (
    <group>
      {/* Simple placeholder geometry representing an open mouth */}
      <mesh position={[0, 0, 0]}>
        <torusGeometry args={[0.4, 0.08, 12, 48, Math.PI]} />
        <meshStandardMaterial color="#f5cba7" />
      </mesh>
      {/* Upper teeth row */}
      {Array.from({ length: 8 }).map((_, i) => (
        <mesh key={`upper-${i}`} position={[-0.35 + i * 0.1, 0.06, 0]}>
          <boxGeometry args={[0.07, 0.1, 0.07]} />
          <meshStandardMaterial color="#fffde7" />
        </mesh>
      ))}
      {/* Lower teeth row */}
      {Array.from({ length: 8 }).map((_, i) => (
        <mesh key={`lower-${i}`} position={[-0.35 + i * 0.1, -0.06, 0]}>
          <boxGeometry args={[0.07, 0.08, 0.07]} />
          <meshStandardMaterial color="#fffde7" />
        </mesh>
      ))}
      {/* Tongue */}
      <mesh position={[0, -0.05, 0.15]}>
        <sphereGeometry args={[0.18, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#e57373" />
      </mesh>
      {revealedLesions.map((lesion) => (
        <LesionHighlight
          key={lesion.region_id}
          lesion={lesion}
          position={fallbackPosition(lesion)}
          onClick={onLesionClick}
        />
      ))}
    </group>
  );
}

interface OralSimulatorProps {
  caseId: string;
  oralModel: OralModelData | null;
  revealedActions: string[];
}

export default function OralSimulator({ caseId, oralModel, revealedActions }: OralSimulatorProps) {
  const modelFile = oralModel?.model_file ?? null;
  const { url, loading, error } = useOralModel(caseId, modelFile);
  const lesionRegions = oralModel?.lesion_regions ?? [];
  const revealedLesions = useRevealedLesions(lesionRegions, revealedActions);
  const [selectedLesion, setSelectedLesion] = useState<LesionRegion | null>(null);

  const highlightedTeeth = revealedLesions.flatMap((l) => l.highlight_teeth ?? []);

  return (
    <div className="flex flex-col gap-3">
      {/* 3D Viewport */}
      <div className="relative w-full rounded-xl overflow-hidden border border-gray-200 bg-gray-900" style={{ height: 320 }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400" />
          </div>
        )}
        {error && (
          <div className="absolute top-2 left-0 right-0 flex justify-center z-10">
            <span className="bg-yellow-800 text-yellow-100 text-xs px-3 py-1 rounded-full">
              3D model yüklenemedi — placeholder gösteriliyor
            </span>
          </div>
        )}

        <Canvas camera={{ position: [0, 0, 1.4], fov: 45 }} shadows>
          <ambientLight intensity={0.6} />
          <directionalLight position={[2, 4, 3]} intensity={1} castShadow />
          <Environment preset="studio" />

          <Suspense fallback={null}>
            {url ? (
              <GLBModel
                url={url}
                revealedLesions={revealedLesions}
                onLesionClick={setSelectedLesion}
              />
            ) : (
              <PlaceholderModel
                revealedLesions={revealedLesions}
                onLesionClick={setSelectedLesion}
              />
            )}
          </Suspense>

          <OrbitControls
            enablePan={false}
            minDistance={0.6}
            maxDistance={3}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 1.5}
          />
        </Canvas>

        {/* Controls hint */}
        <p className="absolute bottom-2 left-0 right-0 text-center text-[10px] text-gray-400 pointer-events-none">
          Sol tık: döndür &nbsp;·&nbsp; Scroll: zoom
        </p>
      </div>

      {/* Lesion info card */}
      {selectedLesion && (
        <div
          className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm"
          style={{ borderColor: selectedLesion.highlight_color, background: `${selectedLesion.highlight_color}18` }}
        >
          <span className="font-medium" style={{ color: selectedLesion.highlight_color }}>
            {selectedLesion.label}
          </span>
          <button
            onClick={() => setSelectedLesion(null)}
            className="text-gray-400 hover:text-gray-600 text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* FDI tooth map */}
      <div className="rounded-xl border border-gray-200 bg-white p-3">
        <ToothMap highlightedTeeth={highlightedTeeth} />
      </div>

      {/* Revealed lesions list */}
      {revealedLesions.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Açılmış Bulgular
          </p>
          <ul className="space-y-1">
            {revealedLesions.map((l) => (
              <li key={l.region_id} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: l.highlight_color }}
                />
                {l.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {revealedLesions.length === 0 && (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 py-5 text-center">
          <p className="text-sm text-gray-500">Henüz lezyon bölgesi açılmadı</p>
          <p className="text-xs text-gray-400 mt-0.5">Oral muayeneyi gerçekleştirin</p>
        </div>
      )}

      {/* CC-BY model attribution (required by license) */}
      {url && (
        <p className="text-[10px] text-gray-400 text-right pr-1">
          3D model: &ldquo;(Dentistry) Human Teeth&rdquo; by RealDoCC / Ali Aminimofrad — CC BY 4.0
        </p>
      )}
    </div>
  );
}
