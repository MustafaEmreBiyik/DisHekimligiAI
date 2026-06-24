"use client";

import { useState, useEffect, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("access_token") ?? "";
}

export interface LesionRegion {
  region_id: string;
  label: string;
  highlight_color: string;
  reveal_on: string;
  highlight_teeth?: number[];
  position?: [number, number, number];
}

export interface OralModelData {
  model_file: string;
  lesion_regions: LesionRegion[];
}

interface ModelState {
  url: string | null;
  loading: boolean;
  error: boolean;
}

export function useOralModel(caseId: string, modelFile: string | null): ModelState {
  const [state, setState] = useState<ModelState>({ url: null, loading: false, error: false });
  const prevFile = useRef<string | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!modelFile) return;

    const filename = modelFile.split("/").pop() ?? modelFile;
    const url = `${API_URL}/api/cases/${encodeURIComponent(caseId)}/model/${encodeURIComponent(filename)}`;

    if (prevFile.current === url) return;
    prevFile.current = url;

    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }

    setState({ url: null, loading: true, error: false });

    const token = getToken();
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        const objectUrl = URL.createObjectURL(blob);
        objectUrlRef.current = objectUrl;
        setState({ url: objectUrl, loading: false, error: false });
      })
      .catch(() => {
        setState({ url: null, loading: false, error: true });
      });

    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [caseId, modelFile]);

  return state;
}

export function useRevealedLesions(
  lesionRegions: LesionRegion[],
  revealedActions: string[]
): LesionRegion[] {
  return lesionRegions.filter((r) => revealedActions.includes(r.reveal_on));
}
