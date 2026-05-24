"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import axios from "axios";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import {
  instructorAPI,
  InstructorQuestionBankItem,
  InstructorQuestionCreatePayload,
} from "@/lib/api";
import {
  ArrowLeft,
  Copy,
  FilePlus2,
  ListChecks,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";

type AuthoringMode = "OPEN_ENDED" | "MCQ";

type QuestionFormState = {
  question_id: string;
  question_text: string;
  topic_id: string;
  competency_areas: string;
  bloom_level: string;
  difficulty: string;
  safety_category: string;
  unit_id: string;        // T-2A: ünite etiketi
  week_number: string;    // T-2A: hafta numarası (string → int dönüşümü payload'da)
  rubric_guide: string;
  model_answer_outline: string;
  instructor_explanation: string;
  options: string[];
  correct_option: string;
  max_score: number;
  is_active: boolean;
};

const BLOOM_OPTIONS = ["remember", "understand", "apply", "analyze", "evaluate", "create"];
const DIFFICULTY_OPTIONS = ["easy", "medium", "hard"];
const SAFETY_OPTIONS = ["none", "low", "moderate", "high"];

const EMPTY_FORM: QuestionFormState = {
  question_id: "",
  question_text: "",
  topic_id: "Oral Patoloji",
  competency_areas: "",
  bloom_level: "analyze",
  difficulty: "medium",
  safety_category: "low",
  unit_id: "",
  week_number: "",
  rubric_guide: "",
  model_answer_outline: "",
  instructor_explanation: "",
  options: ["", "", "", ""],
  correct_option: "",
  max_score: 10,
  is_active: true,
};

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function splitCompetencies(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildOpenEndedPrompt(form: QuestionFormState): string {
  const competencies = splitCompetencies(form.competency_areas);

  return [
    "You are a senior dental education assessment designer creating one high-quality open-ended question for DentAI.",
    "Produce an instructor-ready item that measures clinical reasoning, not shallow recall.",
    "",
    "Hard constraints:",
    `- Topic: ${form.topic_id || "Oral Patoloji"}`,
    `- Bloom level: ${form.bloom_level}`,
    `- Difficulty: ${form.difficulty}`,
    `- Safety category: ${form.safety_category}`,
    `- Max score: ${form.max_score}`,
    `- Competency areas: ${competencies.length > 0 ? competencies.join(", ") : "Add competency tags that clearly match the item."}`,
    `- Draft or focus area: ${form.question_text || "Generate the best possible question text for this topic."}`,
    "",
    "Question design requirements:",
    "- Anchor the item in a realistic dental or oral medicine context.",
    "- Make the prompt precise enough that strong and weak answers are distinguishable.",
    "- Require the learner to justify, compare, explain, or prioritize rather than list memorized facts.",
    "- Avoid answer leakage, yes/no phrasing, trivia, and multiple independent asks in one sentence.",
    "- Ensure the rubric can be graded consistently by an instructor.",
    "",
    "Return strict JSON only with this schema:",
    "{",
    '  "question_text": "string",',
    '  "rubric_guide": "3-6 bullet-like criteria in plain text for instructor grading",',
    '  "model_answer_outline": "concise ideal-answer outline covering the must-hit points",',
    '  "instructor_explanation": "why this question is pedagogically valuable and what misconception it exposes",',
    '  "competency_areas": ["string", "string"],',
    `  "bloom_level": "${form.bloom_level}",`,
    `  "difficulty": "${form.difficulty}",`,
    `  "safety_category": "${form.safety_category}",`,
    `  "max_score": ${form.max_score}`,
    "}",
    "",
    "The JSON must be ready to paste into a question-authoring form with no markdown fences and no extra commentary.",
  ].join("\n");
}

function buildMcqPrompt(form: QuestionFormState): string {
  const competencies = splitCompetencies(form.competency_areas);
  const optionCount = Math.max(4, form.options.length);

  return [
    "You are a senior dental education assessment designer creating one high-quality one-best-answer MCQ for DentAI.",
    "Produce an instructor-ready item that tests clinical reasoning or applied interpretation, not superficial recall.",
    "",
    "Hard constraints:",
    `- Topic: ${form.topic_id || "Oral Patoloji"}`,
    `- Bloom level: ${form.bloom_level}`,
    `- Difficulty: ${form.difficulty}`,
    `- Safety category: ${form.safety_category}`,
    `- Max score: ${form.max_score}`,
    `- Competency areas: ${competencies.length > 0 ? competencies.join(", ") : "Add competency tags that clearly match the item."}`,
    `- Draft or focus area: ${form.question_text || "Generate the best possible MCQ stem for this topic."}`,
    `- Number of answer options: ${optionCount}`,
    "",
    "MCQ design requirements:",
    "- Use a realistic dental or oral medicine context whenever possible.",
    "- Write one clearly best answer, with distractors that are plausible but ultimately inferior.",
    "- Avoid trick wording, giveaway length differences, absolute terms, and grammatical clueing.",
    "- Make distractors reflect believable misconceptions a learner might actually hold.",
    "- Keep the stem focused on one decision or interpretation target.",
    "- Do not use all of the above or none of the above.",
    "",
    "Return strict JSON only with this schema:",
    "{",
    '  "question_text": "string",',
    `  "options": ["string", "string", "string", "string"],`,
    '  "correct_option": "must exactly match one option",',
    '  "instructor_explanation": "brief explanation of why the correct answer is best and why the distractors are attractive but wrong",',
    '  "competency_areas": ["string", "string"],',
    `  "bloom_level": "${form.bloom_level}",`,
    `  "difficulty": "${form.difficulty}",`,
    `  "safety_category": "${form.safety_category}",`,
    `  "max_score": ${form.max_score}`,
    "}",
    "",
    "The JSON must be ready to paste into a question-authoring form with no markdown fences and no extra commentary.",
  ].join("\n");
}

function readErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }

  return fallback;
}

function buildPayload(mode: AuthoringMode, form: QuestionFormState): InstructorQuestionCreatePayload {
  const payload: InstructorQuestionCreatePayload = {
    question_type: mode,
    question_id: form.question_id.trim() || undefined,
    question_text: form.question_text.trim(),
    topic_id: form.topic_id.trim(),
    competency_areas: splitCompetencies(form.competency_areas),
    bloom_level: form.bloom_level,
    difficulty: form.difficulty,
    safety_category: form.safety_category,
    unit_id: form.unit_id.trim() || undefined,                                    // T-2A
    week_number: form.week_number ? parseInt(form.week_number, 10) : undefined,   // T-2A
    instructor_explanation: form.instructor_explanation.trim() || undefined,
    max_score: form.max_score,
    is_active: form.is_active,
  };

  if (mode === "OPEN_ENDED") {
    payload.rubric_guide = form.rubric_guide.trim();
    payload.model_answer_outline = form.model_answer_outline.trim();
  } else {
    const options = form.options.map((item) => item.trim()).filter(Boolean);
    payload.options = options;
    payload.correct_option = form.correct_option.trim();
  }

  return payload;
}

function questionTypeLabel(type: string): string {
  return type === "MCQ" ? "MCQ" : "Open-Ended";
}

export default function InstructorQuestionsPage() {
  const [mode, setMode] = useState<AuthoringMode>("OPEN_ENDED");
  const [form, setForm] = useState<QuestionFormState>(EMPTY_FORM);
  const [questions, setQuestions] = useState<InstructorQuestionBankItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCopyingPrompt, setIsCopyingPrompt] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const loadQuestions = async () => {
      setIsLoading(true);
      try {
        const response = await instructorAPI.getQuestionBank(mode);
        setQuestions(response);
      } catch (error) {
        console.error("Failed to load instructor question bank", error);
        setErrorMessage(readErrorMessage(error, "Question bank could not be loaded."));
      } finally {
        setIsLoading(false);
      }
    };

    loadQuestions();
  }, [mode]);

  const promptText = useMemo(
    () => (mode === "OPEN_ENDED" ? buildOpenEndedPrompt(form) : buildMcqPrompt(form)),
    [form, mode],
  );

  const topicSuggestions = useMemo(
    () => Array.from(new Set(questions.map((question) => question.topic_id))).filter(Boolean),
    [questions],
  );

  const resetForMode = (nextMode: AuthoringMode) => {
    setMode(nextMode);
    setForm((current) => ({
      ...EMPTY_FORM,
      topic_id: current.topic_id,
      competency_areas: current.competency_areas,
      bloom_level: current.bloom_level,
      difficulty: current.difficulty,
      safety_category: current.safety_category,
      max_score: nextMode === "MCQ" ? 1 : current.max_score,
      is_active: current.is_active,
    }));
    setSuccessMessage("");
    setErrorMessage("");
  };

  const handleFieldChange =
    (field: keyof QuestionFormState) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const target = event.target;
      const value =
        target instanceof HTMLInputElement && target.type === "checkbox"
          ? target.checked
          : target.value;

      setForm((current) => ({
        ...current,
        [field]: field === "max_score" ? Number(value) : value,
      }));
    };

  const handleOptionChange = (index: number, value: string) => {
    setForm((current) => {
      const nextOptions = [...current.options];
      nextOptions[index] = value;

      const selectedCorrect =
        current.correct_option && current.options[index] === current.correct_option
          ? value
          : current.correct_option;

      return {
        ...current,
        options: nextOptions,
        correct_option: selectedCorrect,
      };
    });
  };

  const addOption = () => {
    setForm((current) => ({
      ...current,
      options: [...current.options, ""],
    }));
  };

  const removeOption = (index: number) => {
    setForm((current) => {
      if (current.options.length <= 3) {
        return current;
      }

      const removed = current.options[index];
      const nextOptions = current.options.filter((_, itemIndex) => itemIndex !== index);
      return {
        ...current,
        options: nextOptions,
        correct_option: current.correct_option === removed ? "" : current.correct_option,
      };
    });
  };

  const handleCopyPrompt = async () => {
    setIsCopyingPrompt(true);
    try {
      await navigator.clipboard.writeText(promptText);
      setSuccessMessage(`${questionTypeLabel(mode)} prompt copied.`);
      setErrorMessage("");
    } catch (error) {
      console.error("Failed to copy prompt", error);
      setErrorMessage(readErrorMessage(error, "Prompt could not be copied."));
    } finally {
      setIsCopyingPrompt(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setSuccessMessage("");
    setErrorMessage("");

    try {
      const created = await instructorAPI.createQuestion(buildPayload(mode, form));
      setQuestions((current) => [created, ...current]);
      setForm((current) => ({
        ...EMPTY_FORM,
        topic_id: current.topic_id,
        competency_areas: current.competency_areas,
        bloom_level: current.bloom_level,
        difficulty: current.difficulty,
        safety_category: current.safety_category,
        max_score: mode === "MCQ" ? 1 : current.max_score,
        is_active: current.is_active,
      }));
      setSuccessMessage(`Question created: ${created.question_id}`);
    } catch (error) {
      console.error("Failed to create question", error);
      setErrorMessage(readErrorMessage(error, "Question could not be saved."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
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
                  <FilePlus2 size={32} className="text-blue-600" />
                  Question Authoring
                </h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">
                  Build both open-ended items and MCQs from the same instructor panel, with a
                  question-bank view and generation prompts tuned to each format.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  href="/instructor/grading"
                  className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Grading Queue
                </Link>
              </div>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
            <form
              onSubmit={handleSubmit}
              className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-blue-50 p-3 text-blue-600">
                    <FilePlus2 size={22} />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">New {questionTypeLabel(mode)}</h2>
                    <p className="text-sm text-slate-500">
                      Switch formats without leaving the instructor flow.
                    </p>
                  </div>
                </div>

                <div className="inline-flex rounded-2xl bg-slate-100 p-1">
                  <button
                    type="button"
                    onClick={() => resetForMode("OPEN_ENDED")}
                    className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                      mode === "OPEN_ENDED"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Open-Ended
                  </button>
                  <button
                    type="button"
                    onClick={() => resetForMode("MCQ")}
                    className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                      mode === "MCQ"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    MCQ
                  </button>
                </div>
              </div>

              {successMessage ? (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                  {successMessage}
                </div>
              ) : null}
              {errorMessage ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errorMessage}
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Question ID</span>
                  <input
                    value={form.question_id}
                    onChange={handleFieldChange("question_id")}
                    placeholder={mode === "MCQ" ? "mcq-oral-pathology-lesion-triage" : "oe-oral-pathology-lesion-triage"}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Topic</span>
                  <input
                    list="topic-suggestions"
                    value={form.topic_id}
                    onChange={handleFieldChange("topic_id")}
                    placeholder="Oral Patoloji"
                    required
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                  <datalist id="topic-suggestions">
                    {topicSuggestions.map((topic) => (
                      <option key={topic} value={topic} />
                    ))}
                  </datalist>
                </label>
              </div>

              <label className="space-y-2 text-sm font-medium text-slate-700">
                <span>{mode === "MCQ" ? "Stem" : "Question Text"}</span>
                <textarea
                  rows={5}
                  value={form.question_text}
                  onChange={handleFieldChange("question_text")}
                  placeholder={
                    mode === "MCQ"
                      ? "Write the MCQ stem or the content goal for the AI prompt."
                      : "Write the open-ended question or the content goal for the AI prompt."
                  }
                  required
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Bloom Level</span>
                  <select
                    value={form.bloom_level}
                    onChange={handleFieldChange("bloom_level")}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  >
                    {BLOOM_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Difficulty</span>
                  <select
                    value={form.difficulty}
                    onChange={handleFieldChange("difficulty")}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  >
                    {DIFFICULTY_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Safety Category</span>
                  <select
                    value={form.safety_category}
                    onChange={handleFieldChange("safety_category")}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  >
                    {SAFETY_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Ünite (isteğe bağlı)</span>
                  <input
                    value={form.unit_id}
                    onChange={handleFieldChange("unit_id")}
                    placeholder="Örn: unit_1_immune_mediated"
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Hafta (isteğe bağlı)</span>
                  <input
                    type="number"
                    min={1}
                    max={52}
                    value={form.week_number}
                    onChange={handleFieldChange("week_number")}
                    placeholder="Örn: 3"
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-700">
                  <span>Max Score</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={form.max_score}
                    onChange={handleFieldChange("max_score")}
                    required
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </label>
              </div>

              <label className="space-y-2 text-sm font-medium text-slate-700">
                <span>Competency Areas</span>
                <input
                  value={form.competency_areas}
                  onChange={handleFieldChange("competency_areas")}
                  placeholder="oral diagnosis, lesion triage, differential diagnosis"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </label>

              {mode === "OPEN_ENDED" ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  <label className="space-y-2 text-sm font-medium text-slate-700">
                    <span>Rubric Guide</span>
                    <textarea
                      rows={6}
                      value={form.rubric_guide}
                      onChange={handleFieldChange("rubric_guide")}
                      placeholder="Describe the must-hit points, scoring anchors, and common misses."
                      required
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                  </label>

                  <label className="space-y-2 text-sm font-medium text-slate-700">
                    <span>Model Answer Outline</span>
                    <textarea
                      rows={6}
                      value={form.model_answer_outline}
                      onChange={handleFieldChange("model_answer_outline")}
                      placeholder="Capture the ideal answer structure and key reasoning moves."
                      required
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                  </label>
                </div>
              ) : (
                <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">MCQ Options</h3>
                      <p className="text-sm text-slate-500">
                        Enter plausible distractors and mark one best answer.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={addOption}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-white"
                    >
                      <Plus size={16} />
                      Add Option
                    </button>
                  </div>

                  <div className="space-y-3">
                    {form.options.map((option, index) => (
                      <div key={`option-${index}`} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_auto]">
                        <input
                          value={option}
                          onChange={(event) => handleOptionChange(index, event.target.value)}
                          placeholder={`Option ${index + 1}`}
                          className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />
                        <label className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm text-slate-700">
                          <input
                            type="radio"
                            name="correct_option"
                            checked={form.correct_option === option && option.trim().length > 0}
                            onChange={() =>
                              setForm((current) => ({ ...current, correct_option: current.options[index] }))
                            }
                            className="h-4 w-4 border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                          Mark correct
                        </label>
                        <button
                          type="button"
                          onClick={() => removeOption(index)}
                          disabled={form.options.length <= 3}
                          className="inline-flex items-center justify-center rounded-xl border border-slate-300 px-3 py-3 text-slate-600 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <label className="space-y-2 text-sm font-medium text-slate-700">
                <span>Instructor Explanation</span>
                <textarea
                  rows={4}
                  value={form.instructor_explanation}
                  onChange={handleFieldChange("instructor_explanation")}
                  placeholder={
                    mode === "MCQ"
                      ? "Explain why the best answer is best and what misconception the distractors target."
                      : "Explain what this question probes pedagogically and what misconception it exposes."
                  }
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </label>

              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={handleFieldChange("is_active")}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Activate this question immediately for the student pool
              </label>

              <div className="flex flex-wrap justify-end gap-3">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <FilePlus2 size={18} />}
                  Save {questionTypeLabel(mode)}
                </button>
              </div>
            </form>

            <div className="space-y-6">
              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <h2 className="flex items-center gap-3 text-xl font-bold text-slate-900">
                      <Sparkles size={22} className="text-amber-500" />
                      {questionTypeLabel(mode)} Prompt
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Copy this prompt into an LLM when you want a better first draft that still
                      matches your authoring schema.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleCopyPrompt}
                    disabled={isCopyingPrompt}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                  >
                    {isCopyingPrompt ? <Loader2 size={16} className="animate-spin" /> : <Copy size={16} />}
                    Copy
                  </button>
                </div>

                <pre className="max-h-[460px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                  {promptText}
                </pre>
              </section>

              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="flex items-center gap-3 text-xl font-bold text-slate-900">
                      <ListChecks size={22} className="text-slate-700" />
                      {questionTypeLabel(mode)} Bank
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Recently authored items for the active panel.
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {questions.length} items
                  </span>
                </div>

                {isLoading ? (
                  <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-600">
                    <Loader2 size={18} className="animate-spin" />
                    Question bank loading...
                  </div>
                ) : questions.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                    No {questionTypeLabel(mode).toLowerCase()} items yet.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {questions.map((question) => (
                      <article
                        key={question.question_id}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                            {question.topic_id}
                          </span>
                          <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700">
                            {question.question_type}
                          </span>
                          <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700">
                            {question.max_score} pts
                          </span>
                          <span className="ml-auto text-xs text-slate-500">
                            {formatDate(question.created_at)}
                          </span>
                        </div>

                        <h3 className="text-sm font-semibold text-slate-900">{question.question_text}</h3>

                        <p className="mt-1 text-xs text-slate-400 font-mono">{question.question_id}</p>

                        {/* T-2A: unit_id and week_number badges */}
                        {(question.unit_id || question.week_number) && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {question.unit_id && (
                              <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                                Ünite: {question.unit_id}
                              </span>
                            )}
                            {question.week_number && (
                              <span className="rounded-full bg-teal-100 px-2.5 py-0.5 text-xs font-medium text-teal-700">
                                Hafta {question.week_number}
                              </span>
                            )}
                          </div>
                        )}

                        {question.rubric_guide && (
                          <p className="mt-2 line-clamp-2 text-xs text-slate-500">
                            <span className="font-semibold">Rubric:</span> {question.rubric_guide}
                          </p>
                        )}
                      </article>
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
