"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import {
  mappingAPI,
  CreateMappingPayload,
  MappingFilters,
  MappingType,
  MappingReviewStatus,
  QuestionCaseMappingItem,
} from "@/lib/api";
import {
  ArrowLeft,
  GitBranch,
  Loader2,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";

// ── Constants ─────────────────────────────────────────────────────────────────

const MAPPING_TYPE_OPTIONS: { value: MappingType; label: string }[] = [
  { value: "theory_support", label: "Theory Support" },
  { value: "case_reinforcement", label: "Case Reinforcement" },
  { value: "assessment_link", label: "Assessment Link" },
];

const REVIEW_STATUS_OPTIONS: { value: MappingReviewStatus; label: string }[] = [
  { value: "unmapped", label: "Unmapped" },
  { value: "approved", label: "Approved" },
  { value: "blocked_review_needed", label: "Blocked — Review Needed" },
];

const MAPPING_TYPE_COLORS: Record<MappingType, string> = {
  theory_support: "bg-blue-100 text-blue-700",
  case_reinforcement: "bg-violet-100 text-violet-700",
  assessment_link: "bg-amber-100 text-amber-700",
};

const REVIEW_STATUS_COLORS: Record<MappingReviewStatus, string> = {
  unmapped: "bg-slate-100 text-slate-600",
  approved: "bg-emerald-100 text-emerald-700",
  blocked_review_needed: "bg-rose-100 text-rose-700",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function readErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
  }
  if (error instanceof Error && error.message.trim()) return error.message.trim();
  return fallback;
}

function labelFor<T extends string>(
  options: { value: T; label: string }[],
  value: T,
): string {
  return options.find((o) => o.value === value)?.label ?? value;
}

// ── Empty form state ──────────────────────────────────────────────────────────

const EMPTY_FORM: CreateMappingPayload = {
  question_id: "",
  case_id: "",
  mapping_type: "theory_support",
  review_status: "unmapped",
};

const EMPTY_FILTERS: MappingFilters = {
  question_id: "",
  case_id: "",
  mapping_type: "",
  review_status: "",
};

// ── Page component ────────────────────────────────────────────────────────────

export default function InstructorMappingsPage() {
  // ── List state
  const [mappings, setMappings] = useState<QuestionCaseMappingItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  // ── Filter state
  const [filters, setFilters] = useState<MappingFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<MappingFilters>(EMPTY_FILTERS);

  // ── Create form state
  const [form, setForm] = useState<CreateMappingPayload>(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [formError, setFormError] = useState("");

  // ── Delete state
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // ── Load mappings ─────────────────────────────────────────────────────────

  const loadMappings = useCallback(async (activeFilters: MappingFilters) => {
    setIsLoading(true);
    setLoadError("");
    try {
      const result = await mappingAPI.getMappings(activeFilters);
      setMappings(result.mappings);
      setTotal(result.total);
    } catch (error) {
      setLoadError(readErrorMessage(error, "Could not load mappings."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMappings(EMPTY_FILTERS);
  }, [loadMappings]);

  // ── Filter handlers ───────────────────────────────────────────────────────

  const handleFilterChange =
    (field: keyof MappingFilters) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setFilters((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleApplyFilters = () => {
    setAppliedFilters(filters);
    loadMappings(filters);
  };

  const handleClearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    loadMappings(EMPTY_FILTERS);
  };

  const hasActiveFilters = Object.values(appliedFilters).some((v) => Boolean(v));

  // ── Create mapping ────────────────────────────────────────────────────────

  const handleFormChange =
    (field: keyof CreateMappingPayload) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setSuccessMessage("");
    setFormError("");

    try {
      const created = await mappingAPI.createMapping(form);
      setMappings((prev) => [created, ...prev]);
      setTotal((prev) => prev + 1);
      setForm(EMPTY_FORM);
      setSuccessMessage(
        `Mapping created: "${created.question_id}" → "${created.case_id}" [${created.mapping_type}]`,
      );
    } catch (error) {
      setFormError(readErrorMessage(error, "Could not create mapping."));
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Delete mapping ────────────────────────────────────────────────────────

  const handleDelete = async (mappingId: number) => {
    setDeletingId(mappingId);
    try {
      await mappingAPI.deleteMapping(mappingId);
      setMappings((prev) => prev.filter((m) => m.id !== mappingId));
      setTotal((prev) => prev - 1);
    } catch (error) {
      // Surface inline without clobbering the form messages
      setLoadError(readErrorMessage(error, "Could not delete mapping."));
    } finally {
      setDeletingId(null);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">

          {/* ── Header ── */}
          <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="mb-3 flex items-center gap-3 text-sm font-semibold text-slate-500">
                  <Link
                    href="/instructor/dashboard"
                    className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900"
                  >
                    <ArrowLeft size={16} />
                    Instructor Dashboard
                  </Link>
                </div>
                <h1 className="flex items-center gap-3 text-3xl font-bold text-slate-900">
                  <GitBranch size={32} className="text-violet-600" />
                  Question–Case Mappings
                </h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">
                  Link theory questions to clinical cases to build the pedagogical graph.
                  Mappings control how cases appear in student recommendations and how
                  case-component scores are attributed.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/instructor/questions"
                  className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Question Bank
                </Link>
              </div>
            </div>
          </header>

          {/* ── Body: create form + mapping list ── */}
          <div className="grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">

            {/* ── Create Mapping Form ── */}
            <form
              onSubmit={handleSubmit}
              className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-violet-50 p-3 text-violet-600">
                  <Plus size={22} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">New Mapping</h2>
                  <p className="text-sm text-slate-500">
                    Link a question to a case.
                  </p>
                </div>
              </div>

              {successMessage ? (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                  {successMessage}
                </div>
              ) : null}
              {formError ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {formError}
                </div>
              ) : null}

              <label className="block space-y-2 text-sm font-medium text-slate-700">
                <span>Question ID <span className="text-rose-500">*</span></span>
                <input
                  value={form.question_id}
                  onChange={handleFormChange("question_id")}
                  placeholder="e.g. oral_path_001"
                  required
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                />
              </label>

              <label className="block space-y-2 text-sm font-medium text-slate-700">
                <span>Case ID <span className="text-rose-500">*</span></span>
                <input
                  value={form.case_id}
                  onChange={handleFormChange("case_id")}
                  placeholder="e.g. pericoronitis_case_01"
                  required
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                />
              </label>

              <label className="block space-y-2 text-sm font-medium text-slate-700">
                <span>Mapping Type <span className="text-rose-500">*</span></span>
                <select
                  value={form.mapping_type}
                  onChange={handleFormChange("mapping_type")}
                  required
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                >
                  {MAPPING_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2 text-sm font-medium text-slate-700">
                <span>Review Status</span>
                <select
                  value={form.review_status}
                  onChange={handleFormChange("review_status")}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                >
                  {REVIEW_STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Plus size={18} />
                )}
                Create Mapping
              </button>

              {/* ── Mapping type reference ── */}
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 space-y-1.5">
                <p className="font-semibold text-slate-700 mb-2">Mapping type reference</p>
                <p><span className="font-medium text-blue-700">Theory Support</span> — question tests the theory underpinning this case.</p>
                <p><span className="font-medium text-violet-700">Case Reinforcement</span> — case reinforces the topic this question covers.</p>
                <p><span className="font-medium text-amber-700">Assessment Link</span> — formal exam linkage; counts toward case-component scoring.</p>
              </div>
            </form>

            {/* ── Mapping List + Filters ── */}
            <div className="space-y-4">

              {/* Filters */}
              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-3">
                  <Search size={18} className="text-slate-500" />
                  <h2 className="text-base font-bold text-slate-900">Filter Mappings</h2>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={handleClearFilters}
                      className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                    >
                      <X size={13} />
                      Clear filters
                    </button>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <input
                    value={filters.question_id}
                    onChange={handleFilterChange("question_id")}
                    placeholder="Question ID"
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                  />
                  <input
                    value={filters.case_id}
                    onChange={handleFilterChange("case_id")}
                    placeholder="Case ID"
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                  />
                  <select
                    value={filters.mapping_type}
                    onChange={handleFilterChange("mapping_type")}
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                  >
                    <option value="">All Types</option>
                    {MAPPING_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={filters.review_status}
                    onChange={handleFilterChange("review_status")}
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                  >
                    <option value="">All Statuses</option>
                    {REVIEW_STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={handleApplyFilters}
                    className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                  >
                    <Search size={15} />
                    Apply
                  </button>
                </div>
              </section>

              {/* Mapping rows */}
              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="flex items-center gap-3 text-base font-bold text-slate-900">
                    <GitBranch size={18} className="text-violet-600" />
                    Mapping Graph
                  </h2>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {total} {total === 1 ? "mapping" : "mappings"}
                  </span>
                </div>

                {loadError ? (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {loadError}
                  </div>
                ) : isLoading ? (
                  <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-600">
                    <Loader2 size={18} className="animate-spin" />
                    Loading mappings…
                  </div>
                ) : mappings.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                    {hasActiveFilters
                      ? "No mappings match the active filters."
                      : "No mappings yet. Create the first one using the form."}
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {mappings.map((mapping) => (
                      <MappingRow
                        key={mapping.id}
                        mapping={mapping}
                        isDeleting={deletingId === mapping.id}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </div>
    </InstructorRouteGuard>
  );
}

// ── MappingRow sub-component ──────────────────────────────────────────────────

interface MappingRowProps {
  mapping: QuestionCaseMappingItem;
  isDeleting: boolean;
  onDelete: (id: number) => void;
}

function MappingRow({ mapping, isDeleting, onDelete }: MappingRowProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleDeleteClick = () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    onDelete(mapping.id);
    setConfirmDelete(false);
  };

  const handleCancelDelete = () => setConfirmDelete(false);

  return (
    <div className="flex flex-wrap items-start gap-3 py-4 first:pt-0 last:pb-0">
      <div className="min-w-0 flex-1 space-y-1.5">
        {/* Question → Case arrow */}
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-mono text-xs font-semibold text-slate-800">
            {mapping.question_id}
          </span>
          <span className="text-slate-400">→</span>
          <span className="font-mono text-xs font-semibold text-violet-700">
            {mapping.case_id}
          </span>
        </div>

        {/* Question text preview */}
        <p className="line-clamp-2 text-sm text-slate-600">{mapping.question_text}</p>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${MAPPING_TYPE_COLORS[mapping.mapping_type]}`}
          >
            {labelFor(MAPPING_TYPE_OPTIONS, mapping.mapping_type)}
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${REVIEW_STATUS_COLORS[mapping.review_status]}`}
          >
            {labelFor(REVIEW_STATUS_OPTIONS, mapping.review_status)}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
            {mapping.question_type}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
            {mapping.topic_id}
          </span>
        </div>
      </div>

      {/* Delete control */}
      <div className="flex shrink-0 items-center gap-2">
        {confirmDelete ? (
          <>
            <button
              type="button"
              onClick={handleCancelDelete}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDeleteClick}
              disabled={isDeleting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
            >
              {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
              Confirm
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-60"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
