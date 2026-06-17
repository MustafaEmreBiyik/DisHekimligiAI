"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";

interface ClinicalImagePanelProps {
  revealedMedia: string[];
  caseId: string;
}

interface ImageState {
  src: string | null;
  loading: boolean;
  error: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("access_token") ?? "";
}

function getFilename(mediaPath: string): string {
  return mediaPath.split("/").pop() ?? mediaPath;
}

function useJwtImage(caseId: string, mediaPath: string | null): ImageState {
  const [state, setState] = useState<ImageState>({ src: null, loading: false, error: false });
  const prevUrl = useRef<string | null>(null);

  useEffect(() => {
    if (!mediaPath) return;
    const filename = getFilename(mediaPath);
    const url = `${API_URL}/api/cases/${encodeURIComponent(caseId)}/media/${encodeURIComponent(filename)}`;
    if (prevUrl.current === url) return;
    prevUrl.current = url;

    let objectUrl: string | null = null;
    setState({ src: null, loading: true, error: false });

    const token = getToken();
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setState({ src: objectUrl, loading: false, error: false });
      })
      .catch(() => {
        setState({ src: null, loading: false, error: true });
      });

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [caseId, mediaPath]);

  return state;
}

interface ZoomableImageProps {
  caseId: string;
  mediaPath: string;
  isNew: boolean;
}

function ZoomableImage({ caseId, mediaPath, isNew }: ZoomableImageProps) {
  const { src, loading, error } = useJwtImage(caseId, mediaPath);
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, tx: 0, ty: 0 });

  const resetZoom = () => {
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  };

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setScale((prev) => Math.min(4, Math.max(1, prev - e.deltaY * 0.002)));
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale <= 1) return;
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, tx: translate.x, ty: translate.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setTranslate({
      x: dragStart.current.tx + (e.clientX - dragStart.current.x),
      y: dragStart.current.ty + (e.clientY - dragStart.current.y),
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  if (loading) {
    return (
      <div className="w-full h-48 flex items-center justify-center bg-gray-100 rounded-xl">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !src) {
    return (
      <div className="w-full h-48 flex items-center justify-center bg-red-50 rounded-xl border border-red-200">
        <p className="text-sm text-red-500">Görsel yüklenemedi</p>
      </div>
    );
  }

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-gray-200 bg-gray-50 select-none ${
        isNew ? "animate-fade-in" : ""
      }`}
      style={{ cursor: scale > 1 ? (isDragging ? "grabbing" : "grab") : "zoom-in" }}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onDoubleClick={resetZoom}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt="Klinik görsel"
        draggable={false}
        className="w-full max-h-72 object-contain transition-transform duration-150"
        style={{
          transform: `scale(${scale}) translate(${translate.x / scale}px, ${translate.y / scale}px)`,
          transformOrigin: "center center",
        }}
      />
      {scale > 1 && (
        <button
          onClick={resetZoom}
          className="absolute top-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded-md hover:bg-opacity-70 transition-all"
        >
          Sıfırla
        </button>
      )}
      <p className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-40 text-white text-xs px-2 py-1 text-center">
        Kaydır: zoom • Çift tık: sıfırla
      </p>
    </div>
  );
}

export default function ClinicalImagePanel({ revealedMedia, caseId }: ClinicalImagePanelProps) {
  const [prevCount, setPrevCount] = useState(0);
  const [showToast, setShowToast] = useState(false);
  const [newIndices, setNewIndices] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (revealedMedia.length > prevCount) {
      setNewIndices((prev) => {
        const next = new Set(prev);
        for (let i = prevCount; i < revealedMedia.length; i++) {
          next.add(i);
        }
        return next;
      });
      setShowToast(true);
      setPrevCount(revealedMedia.length);
      const t = setTimeout(() => setShowToast(false), 3000);
      return () => clearTimeout(t);
    }
  }, [revealedMedia.length, prevCount]);

  if (revealedMedia.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
        <svg
          className="w-16 h-16 text-gray-300 mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <p className="text-sm font-medium text-gray-500">Klinik görsel henüz açılmadı</p>
        <p className="text-xs text-gray-400 mt-1">Oral muayeneyi gerçekleştirin</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-3">
      {showToast && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-green-600 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-lg z-10 whitespace-nowrap animate-bounce">
          Yeni bulgu açıldı!
        </div>
      )}
      {revealedMedia.map((path, idx) => (
        <ZoomableImage
          key={path}
          caseId={caseId}
          mediaPath={path}
          isNew={newIndices.has(idx)}
        />
      ))}
    </div>
  );
}
