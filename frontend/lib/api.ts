/**
 * API Client Configuration
 * ========================
 * Axios instance configured for FastAPI backend communication.
 * Automatically handles JWT token attachment and error responses.
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

// API base URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AppUserRole = "student" | "instructor" | "admin";

export interface AuthMeResponse {
  user_id: string;
  role: AppUserRole;
  display_name: string;
  student_id: string;
  name: string;
  email?: string | null;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? error.message ?? fallback;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor - Automatically attach JWT token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage
    const token = localStorage.getItem("access_token");

    if (token && config.headers) {
      // Attach Bearer token to Authorization header
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;

      if (status === 401) {
        // Unauthorized - clear all auth data and redirect to login
        ["access_token", "user_id", "student_id", "name", "display_name", "role"].forEach(
          (key) => localStorage.removeItem(key)
        );

        // Only redirect if not already on login page
        if (
          typeof window !== "undefined" &&
          !window.location.pathname.includes("/login")
        ) {
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

// ==================== API FUNCTIONS ====================

/**
 * Authentication API
 */
export const authAPI = {
  /**
   * Register a new student account
   */
  register: async (data: {
    student_id: string;
    name: string;
    password: string;
    email?: string;
  }) => {
    const response = await apiClient.post("/api/auth/register", data);
    return response.data;
  },

  /**
   * Login with student credentials
   */
  login: async (student_id: string, password: string) => {
    const response = await apiClient.post("/api/auth/login", {
      student_id,
      password,
    });
    return response.data; // { access_token, token_type, student_id, name }
  },

  /**
   * Get current user information
   */
  getCurrentUser: async (): Promise<AuthMeResponse> => {
    const response = await apiClient.get("/api/auth/me");
    return response.data as AuthMeResponse;
  },
};

/**
 * Chat API
 */
export const chatAPI = {
  /**
   * Send a chat message (requires authentication)
   */
  sendMessage: async (message: string, case_id: string): Promise<ChatApiResponse> => {
    const response = await apiClient.post("/api/chat/send", {
      message,
      case_id,
    });
    return response.data as ChatApiResponse;
  },

  /**
   * Get chat history for a session
   */
  getHistory: async (student_id: string, case_id: string) => {
    const response = await apiClient.get(
      `/api/chat/history/${student_id}/${case_id}`
    );
    return response.data;
  },
};

/**
 * Cases API
 */
export const casesAPI = {
  /**
   * List all available cases
   */
  getAllCases: async () => {
    const response = await apiClient.get("/api/cases");
    return response.data;
  },

  /**
   * Get a specific case (student-safe view)
   */
  getCase: async (caseId: string) => {
    const response = await apiClient.get(`/api/cases/${caseId}`);
    return response.data;
  },

  /**
   * Start or resume a session for a case
   */
  startSession: async (caseId: string) => {
    const response = await apiClient.post(`/api/cases/${caseId}/start`);
    return response.data;
  },

  /**
   * Get current session info for a case
   */
  getSession: async (caseId: string) => {
    const response = await apiClient.get(`/api/cases/${caseId}/session`);
    return response.data;
  },
};

export interface TopFeature {
  name: string;
  contribution: number;
  direction: "up" | "down";
}

export interface RecommendationItem {
  case_id: string;
  title: string;
  difficulty: string;
  estimated_duration_minutes: number;
  competency_tags: string[];
  reason_code: string;
  reason_text: string;
  priority_score: number;
  top_features?: TopFeature[] | null;
  model_version?: string | null;
}

export interface RecommendationMeta {
  algorithm_version: string;
  generated_at: string;
  cold_start: boolean;
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[];
  meta: RecommendationMeta;
}

/**
 * Recommendation API
 */
export const recommendationsAPI = {
  getMyRecommendations: async (algorithm?: string): Promise<RecommendationResponse> => {
    const params = algorithm ? { algorithm } : {};
    const response = await apiClient.get("/api/recommendations/me", { params });
    return response.data as RecommendationResponse;
  },
};

export interface InstructorAssignedStudent {
  user_id: string;
  display_name: string;
  total_sessions: number;
  avg_score: number;
  last_active: string | null;
  risk_level: "high" | "medium" | "low";
  weak_competencies: string[];
}

export interface InstructorSafetyFlag {
  user_id: string;
  display_name: string;
  session_id: string;
  case_id: string;
  flag_type: string;
  created_at: string | null;
}

export interface InstructorCompetencySummaryItem {
  avg_score: number;
  student_count: number;
}

export interface InstructorOverviewResponse {
  assigned_students: InstructorAssignedStudent[];
  safety_flags: InstructorSafetyFlag[];
  competency_summary: Record<string, InstructorCompetencySummaryItem>;
}

export interface InstructorStudent {
  user_id: string;
  display_name: string;
  avg_score: number;
  weak_competencies: string[];
  risk_level: "high" | "medium" | "low";
}

export interface InstructorStudentSession {
  session_id: string;
  case_id: string;
  case_title: string;
  score: number;
  is_finished: boolean;
  created_at: string | null;
  safety_flags: string[];
  hint_count: number;
}

export interface InstructorRecommendationHistoryItem {
  case_id: string;
  reason_code: string;
  reason_text: string;
  created_at: string | null;
  is_spotlight: boolean;
}

export interface InstructorStudentDrilldownResponse {
  student: InstructorStudent;
  sessions: InstructorStudentSession[];
  recommendation_history: InstructorRecommendationHistoryItem[];
}

export interface InstructorSessionAction {
  message_id: string;
  student_message: string;
  interpreted_action: string;
  score_delta: number;
  is_critical_safety_rule: boolean;
  safety_category: string | null;
  timestamp: string | null;
}

export interface InstructorValidatorNote {
  safety_violation: boolean;
  missing_critical_steps: string[];
  clinical_accuracy: boolean | null;
  faculty_notes: string | null;
  created_at: string | null;
}

export interface InstructorCoachHint {
  hint_level: string;
  content: string;
  created_at: string | null;
}

export interface InstructorSessionDetailResponse {
  session_id: string;
  student_id: string;
  case_id: string;
  score: number;
  is_finished: boolean;
  actions: InstructorSessionAction[];
  validator_notes: InstructorValidatorNote[];
  coach_hints: InstructorCoachHint[];
}

export interface InstructorSpotlightPayload {
  case_id: string;
  reason: string;
}

export interface InstructorSpotlightResponse {
  success: boolean;
  spotlight_id: string;
  message: string;
}

export interface GradingQueueItem {
  answer_id: number;
  attempt_id: number;
  question_id: string;
  question_text: string;
  student_response: string;
  rubric_guide?: string | null;
  model_answer_outline?: string | null;
  max_score: number;
  submitted_at?: string | null;
}

export interface GradeSubmission {
  instructor_score: number;
  instructor_feedback: string;
  publish: boolean;
}

export interface InstructorQuestionBankItem {
  id: number;                        // T-4B: DB primary key (for rubric versioning)
  question_id: string;
  question_type: string;
  question_text: string;
  topic_id: string;
  competency_areas: string[];
  bloom_level: string;
  difficulty: string;
  safety_category: string;
  unit_id?: string | null;           // T-2A
  week_number?: number | null;       // T-2A
  rubric_guide?: string | null;
  model_answer_outline?: string | null;
  instructor_explanation?: string | null;
  options: string[];
  correct_option?: string | null;
  max_score: number;
  is_active: boolean;
  current_rubric_version?: number | null; // T-4B: latest published rubric version
  created_at?: string | null;
  updated_at?: string | null;
}

export interface InstructorQuestionCreatePayload {
  question_type: string;
  question_id?: string;
  question_text: string;
  topic_id: string;
  competency_areas: string[];
  bloom_level: string;
  difficulty: string;
  safety_category: string;
  unit_id?: string;          // T-2A
  week_number?: number;      // T-2A
  rubric_guide?: string;
  model_answer_outline?: string;
  instructor_explanation?: string;
  options?: string[];
  correct_option?: string;
  max_score: number;
  is_active?: boolean;
}

// ── S10-D: Cognitive Load Profiling ──────────────────────────────────────────
export interface CognitiveLoadResponse {
  session_id: number;
  student_id: string;
  avg_response_time_ms: number | null;
  hint_count: number;
  deviation_count: number;
  action_count: number;
  load_level: "low" | "medium" | "high";
  computed_at: string;
}

// ── S10-E: Safety-Critical Action Reaction Time ───────────────────────────────
export interface SafetyMetricsResponse {
  session_id: number;
  student_id: string;
  case_id: string;
  safety_actions_taken: string[];
  safety_actions_missing: string[];
  first_safety_action_seconds: number | null;
  all_safety_checks_done: boolean;
  computed_at: string;
}

// ── S10-F: Diagnostic Reasoning Process Trace ─────────────────────────────────
export interface ProcessTraceEvent {
  seq: number;
  role: string;
  timestamp: string | null;
  content_preview: string;
  interpreted_action: string | null;
  score: number | null;
  reasoning_deviation: boolean | null;
  clinical_intent: string | null;
}

export interface ProcessTraceResponse {
  session_id: number;
  student_id: string;
  case_id: string;
  total_score: number;
  events: ProcessTraceEvent[];
  reasoning_pattern: Record<string, unknown> | null;
  total_actions: number;
  deviation_count: number;
}

/**
 * Instructor API
 */
export const instructorAPI = {
  getOverview: async (): Promise<InstructorOverviewResponse> => {
    const response = await apiClient.get("/api/instructor/overview");
    return response.data as InstructorOverviewResponse;
  },

  getStudentDrilldown: async (
    studentId: string,
  ): Promise<InstructorStudentDrilldownResponse> => {
    const response = await apiClient.get(`/api/instructor/students/${studentId}`);
    return response.data as InstructorStudentDrilldownResponse;
  },

  getSessionDetail: async (
    sessionId: string,
  ): Promise<InstructorSessionDetailResponse> => {
    const response = await apiClient.get(`/api/instructor/sessions/${sessionId}`);
    return response.data as InstructorSessionDetailResponse;
  },

  createSpotlight: async (
    studentId: string,
    payload: InstructorSpotlightPayload,
  ): Promise<InstructorSpotlightResponse> => {
    const response = await apiClient.post(
      `/api/instructor/students/${studentId}/spotlight`,
      payload,
    );
    return response.data as InstructorSpotlightResponse;
  },

  getGradingQueue: async (): Promise<GradingQueueItem[]> => {
    const response = await apiClient.get("/api/quiz/instructor/grading_queue");
    return response.data as GradingQueueItem[];
  },

  submitGrade: async (answerId: number, payload: GradeSubmission): Promise<void> => {
    await apiClient.post(`/api/quiz/instructor/grade/${answerId}`, payload);
  },

  getQuestionBank: async (questionType?: string): Promise<InstructorQuestionBankItem[]> => {
    const suffix = questionType ? `?question_type=${encodeURIComponent(questionType)}` : "";
    const response = await apiClient.get(`/api/quiz/instructor/questions${suffix}`);
    return response.data as InstructorQuestionBankItem[];
  },

  createQuestion: async (
    payload: InstructorQuestionCreatePayload,
  ): Promise<InstructorQuestionBankItem> => {
    const response = await apiClient.post("/api/quiz/instructor/questions", payload);
    return response.data as InstructorQuestionBankItem;
  },

  bulkUpdateQuestions: async (payload: { question_ids: number[]; action: string; value?: string }): Promise<{ affected: number; action: string }> => {
    const response = await apiClient.patch("/api/quiz/instructor/questions/bulk", payload);
    return response.data;
  },

  exportQuestionsCSV: async (): Promise<Blob> => {
    const response = await apiClient.get("/api/quiz/instructor/questions/export", { responseType: "blob" });
    return response.data as Blob;
  },

  getSessionCognitiveLoad: async (sessionId: string): Promise<CognitiveLoadResponse> => {
    const response = await apiClient.get(`/api/sessions/${sessionId}/cognitive-load`);
    return response.data as CognitiveLoadResponse;
  },

  getSessionSafetyMetrics: async (sessionId: string): Promise<SafetyMetricsResponse> => {
    const response = await apiClient.get(`/api/sessions/${sessionId}/safety-metrics`);
    return response.data as SafetyMetricsResponse;
  },

  getSessionProcessTrace: async (sessionId: string): Promise<ProcessTraceResponse> => {
    const response = await apiClient.get(`/api/sessions/${sessionId}/process-trace`);
    return response.data as ProcessTraceResponse;
  },
};

export type ServiceHealthStatus = "ok" | "degraded" | "unavailable";

export interface AdminUserItem {
  user_id: string;
  display_name: string;
  email: string | null;
  role: AppUserRole;
  is_archived: boolean;
  created_at: string | null;
}

export interface AdminUsersResponse {
  users: AdminUserItem[];
}

export interface AdminUserCreatePayload {
  display_name: string;
  email: string;
  password: string;
  role: AppUserRole;
}

export interface AdminUserUpdatePayload {
  role?: AppUserRole;
  is_archived?: boolean;
}

export interface AdminCaseItem {
  case_id: string;
  title: string;
  category: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  is_active: boolean;
  schema_version: string;
  published_version: number;
  last_published_at: string | null;
}

export interface AdminCasesResponse {
  cases: AdminCaseItem[];
}

export interface AdminCaseCreatePayload {
  case_id: string;
  title: string;
  category: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  estimated_duration_minutes: number;
  is_active?: boolean;
  schema_version?: string;
  learning_objectives?: string[];
  prerequisite_competencies?: string[];
  competency_tags?: string[];
  initial_state?: string;
  states?: Record<string, unknown>;
  patient_info?: Record<string, unknown>;
}

export interface AdminCaseUpdatePayload {
  title?: string;
  category?: string;
  difficulty?: "beginner" | "intermediate" | "advanced";
  estimated_duration_minutes?: number;
  is_active?: boolean;
}

export interface AdminPublishPayload {
  change_notes: string;
}

export interface AdminPublishResponse {
  case_id: string;
  published_version: number;
  published_at: string | null;
  change_notes: string;
}

export interface AdminRulesItem {
  case_id: string;
  schema_version?: string;
  rules: Array<Record<string, unknown>>;
}

export interface AdminRulesUpdatePayload {
  rules: Array<Record<string, unknown>>;
}

export interface AdminHealthResponse {
  status: "ok" | "degraded";
  services: {
    database: ServiceHealthStatus;
    gemini_api: ServiceHealthStatus;
    medgemma_api: ServiceHealthStatus;
  };
  stats: {
    total_users: number;
    active_sessions_today: number;
    safety_flags_today: number;
    injection_attempts_today: number;
  };
}

/**
 * Admin API
 */
export const adminAPI = {
  getUsers: async (): Promise<AdminUsersResponse> => {
    const response = await apiClient.get("/api/admin/users");
    return response.data as AdminUsersResponse;
  },

  createUser: async (payload: AdminUserCreatePayload): Promise<AdminUserItem> => {
    const response = await apiClient.post("/api/admin/users", payload);
    return response.data as AdminUserItem;
  },

  updateUser: async (
    userId: string,
    payload: AdminUserUpdatePayload,
  ): Promise<AdminUserItem> => {
    const response = await apiClient.put(`/api/admin/users/${userId}`, payload);
    return response.data as AdminUserItem;
  },

  getCases: async (): Promise<AdminCasesResponse> => {
    const response = await apiClient.get("/api/admin/cases");
    return response.data as AdminCasesResponse;
  },

  createCase: async (payload: AdminCaseCreatePayload): Promise<AdminCaseItem> => {
    const response = await apiClient.post("/api/admin/cases", payload);
    return response.data as AdminCaseItem;
  },

  updateCase: async (
    caseId: string,
    payload: AdminCaseUpdatePayload,
  ): Promise<AdminCaseItem> => {
    const response = await apiClient.put(`/api/admin/cases/${caseId}`, payload);
    return response.data as AdminCaseItem;
  },

  publishCase: async (
    caseId: string,
    payload: AdminPublishPayload,
  ): Promise<AdminPublishResponse> => {
    const response = await apiClient.post(
      `/api/admin/cases/${caseId}/publish`,
      payload,
    );
    return response.data as AdminPublishResponse;
  },

  getRules: async (): Promise<AdminRulesItem[]> => {
    const response = await apiClient.get("/api/admin/rules");
    return response.data as AdminRulesItem[];
  },

  updateRules: async (
    caseId: string,
    payload: AdminRulesUpdatePayload,
  ): Promise<AdminRulesItem> => {
    const response = await apiClient.put(`/api/admin/rules/${caseId}`, payload);
    return response.data as AdminRulesItem;
  },

  getHealth: async (): Promise<AdminHealthResponse> => {
    const response = await apiClient.get("/api/admin/health");
    return response.data as AdminHealthResponse;
  },
};

/**
 * Feedback API
 */
export const feedbackAPI = {
    /**
     * Submit feedback after case completion
     */
    submitFeedback: async (session_id: number, case_id: string, rating: number, comment?: string) => {
        const response = await apiClient.post('/api/feedback/submit', {
            session_id,
            case_id,
            rating,
            comment,
        });
        return response.data;
    },
};

/**
 * Analytics API
 */
export const analyticsAPI = {
    /**
     * Download actions CSV
     */
    downloadActionsCSV: () => {
        window.open(`${apiClient.defaults.baseURL}/api/analytics/export/actions`, '_blank');
    },

    /**
     * Download feedback CSV
     */
    downloadFeedbackCSV: () => {
        window.open(`${apiClient.defaults.baseURL}/api/analytics/export/feedback`, '_blank');
    },

    /**
     * Download sessions CSV
     */
    downloadSessionsCSV: () => {
        window.open(`${apiClient.defaults.baseURL}/api/analytics/export/sessions`, '_blank');
    },
};

/**
 * User / Student Stats API
 */
export const userAPI = {
    /**
     * Get comprehensive stats for the authenticated student
     */
    getStats: async () => {
        const response = await apiClient.get('/api/analytics/student-stats');
        return response.data;
    },
};

// ==================== QUIZ TYPES (student-safe) ====================

// ── Composite score types (T-2B) ─────────────────────────────────────────────

export interface ComponentScoreData {
  available: boolean;
  earned: number;
  max_possible: number;
  /** null = no published records yet (cold start); 0.0 = records exist but zero earned */
  pct: number | null;
  design_weight: number;
  effective_weight: number;
}

export interface CompositeScoreData {
  mcq: ComponentScoreData;
  open_ended: ComponentScoreData;
  case: ComponentScoreData;
  /** null only when ALL three components are unavailable (true cold start) */
  composite_pct: number | null;
  all_components_available: boolean;
  computed_at: string;
}

// ── Topic accuracy types (T-2C) ───────────────────────────────────────────────

export interface TopicAccuracyItem {
  topic_id: string;
  topic_label: string;
  earned: number;
  max_possible: number;
  /** null when max_possible == 0 (defensive; should not occur in practice) */
  pct: number | null;
  answered_count: number;
  correct_count: number;
  /** true when pct < 60% */
  is_weak: boolean;
}

export interface TopicAccuracyData {
  /** Sorted weakest-first */
  topics: TopicAccuracyItem[];
  has_any_data: boolean;
  computed_at: string;
}

/** Student-safe question — no answer keys, no explanation. */
export interface QuizQuestion {
    id: string;
    topic: string;
    question: string;
    options: string[];
    question_type?: string;
    difficulty?: string;
    bloom_level?: string;
}

export interface AttemptSummary {
  attempted: boolean;
  last_score: number | null;
  attempt_count: number;
}

export interface QuestionBankEntry {
  question_id: string;
  question_text: string;
  question_type: string;
  topic_id: string;
  bloom_level: string;
  difficulty: string;
  max_score: number;
  options_json: string[] | null;
  attempt_summary: AttemptSummary;
}

export interface QuestionBankFilters {
  topic?: string;
  difficulty?: string;
  question_type?: string;
  bloom_level?: string;
  search?: string;
}

/** Per-question result after server-side grading — student-safe feedback only. */
export interface QuizQuestionResult {
    id: string;
    topic: string;
    question: string;
    selected_option: string | null;
    is_correct: boolean | null;
    feedback: string | null;
    question_type?: string;
    grading_status?: string;
    instructor_score?: number | null;
    instructor_feedback?: string | null;
    answer_id?: number | null;  // S10-B: for explanation lookup
}

/** Student quiz attempt list item (T-5D). */
export interface AttemptListItem {
    attempt_id: number;
    created_at: string;
    total_score: number;
    max_score: number;
    percentage: number | null;
    question_count: number;
    overall_status: string;
}

/** POST /api/quiz/submit response — student-safe. */
export interface QuizSubmitResponse {
    attempt_id: number;
    score: number | null;
    total: number;
    percentage: number | null;
    overall_status?: string;
    results: QuizQuestionResult[];
}

/**
 * Quiz API
 */
export const quizAPI = {
    getQuestions: async (topic?: string): Promise<QuizQuestion[]> => {
        const params = topic && topic !== 'Tümü' ? `?topic=${encodeURIComponent(topic)}` : '';
        const response = await apiClient.get(`/api/quiz/questions${params}`);
        return response.data as QuizQuestion[];
    },

    getTopics: async (): Promise<string[]> => {
        const response = await apiClient.get('/api/quiz/topics');
        return response.data as string[];
    },

    submitAnswers: async (answers: Record<string, string>): Promise<QuizSubmitResponse> => {
        const response = await apiClient.post('/api/quiz/submit', { answers });
        return response.data as QuizSubmitResponse;
    },

    /** Get the student's weighted composite score across MCQ / OE / Case components. */
    getMyScore: async (): Promise<CompositeScoreData> => {
        const response = await apiClient.get('/api/quiz/my-score');
        return response.data as CompositeScoreData;
    },

    /** Get the student's per-topic MCQ accuracy, sorted weakest-first. */
    getMyTopicAccuracy: async (): Promise<TopicAccuracyData> => {
        const response = await apiClient.get('/api/quiz/my-topic-accuracy');
        return response.data as TopicAccuracyData;
    },

    /** Get student question bank with filters. */
    getQuestionBank: async (filters?: QuestionBankFilters): Promise<QuestionBankEntry[]> => {
        const params = new URLSearchParams();
        if (filters?.topic) params.set('topic', filters.topic);
        if (filters?.difficulty) params.set('difficulty', filters.difficulty);
        if (filters?.question_type) params.set('question_type', filters.question_type);
        if (filters?.bloom_level) params.set('bloom_level', filters.bloom_level);
        if (filters?.search) params.set('search', filters.search);
        const qs = params.toString();
        const response = await apiClient.get(`/api/quiz/student/question-bank${qs ? '?' + qs : ''}`);
        return response.data as QuestionBankEntry[];
    },

    /** List all quiz attempts for the current student (T-5D). */
    getMyAttempts: async (): Promise<AttemptListItem[]> => {
        const response = await apiClient.get('/api/quiz/my-attempts');
        return response.data as AttemptListItem[];
    },

    /** Get detail for a specific attempt (T-5D). */
    getMyAttemptDetail: async (attemptId: number): Promise<QuizSubmitResponse> => {
        const response = await apiClient.get(`/api/quiz/my-attempts/${attemptId}`);
        return response.data as QuizSubmitResponse;
    },
};

// ==================== QUESTION-CASE MAPPING TYPES (T-3A / T-3B) ====================

export type MappingType = "theory_support" | "case_reinforcement" | "assessment_link";
export type MappingReviewStatus = "unmapped" | "approved" | "blocked_review_needed";

export interface QuestionCaseMappingItem {
  id: number;
  question_pk: number;
  question_id: string;
  question_type: string;
  topic_id: string;
  question_text: string;
  case_id: string;
  mapping_type: MappingType;
  review_status: MappingReviewStatus;
}

export interface QuestionCaseMappingsResponse {
  mappings: QuestionCaseMappingItem[];
  total: number;
  computed_at: string;
}

export interface CreateMappingPayload {
  question_id: string;
  case_id: string;
  mapping_type: MappingType;
  review_status?: MappingReviewStatus;
}

export interface MappingFilters {
  question_id?: string;
  case_id?: string;
  mapping_type?: MappingType | "";
  review_status?: MappingReviewStatus | "";
}

/**
 * Instructor-only: Question-Case Mapping API (T-3A read, T-3B write)
 */
export const mappingAPI = {
  /** GET /api/quiz/question-case-mappings — instructor + admin only */
  getMappings: async (filters?: MappingFilters): Promise<QuestionCaseMappingsResponse> => {
    const params = new URLSearchParams();
    if (filters?.question_id?.trim()) params.set("question_id", filters.question_id.trim());
    if (filters?.case_id?.trim()) params.set("case_id", filters.case_id.trim());
    if (filters?.mapping_type) params.set("mapping_type", filters.mapping_type);
    if (filters?.review_status) params.set("review_status", filters.review_status);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const response = await apiClient.get(`/api/quiz/question-case-mappings${suffix}`);
    return response.data as QuestionCaseMappingsResponse;
  },

  /** POST /api/quiz/instructor/question-case-mappings — returns 201 Created */
  createMapping: async (payload: CreateMappingPayload): Promise<QuestionCaseMappingItem> => {
    const response = await apiClient.post("/api/quiz/instructor/question-case-mappings", payload);
    return response.data as QuestionCaseMappingItem;
  },


  /** DELETE /api/quiz/instructor/question-case-mappings/{id} — returns 204 No Content */
  deleteMapping: async (mappingId: number): Promise<void> => {
    await apiClient.delete(`/api/quiz/instructor/question-case-mappings/${mappingId}`);
  },

  getQuestionBank: async (
    filters: QuestionBankFilters = {},
  ): Promise<QuestionBankEntry[]> => {
    const sp = new URLSearchParams();
    if (filters.topic && filters.topic !== "Tümü")
      sp.set("topic", filters.topic);
    if (filters.difficulty) sp.set("difficulty", filters.difficulty);
    if (filters.question_type) sp.set("question_type", filters.question_type);
    if (filters.bloom_level) sp.set("bloom_level", filters.bloom_level);
    if (filters.search) sp.set("search", filters.search);
    const qs = sp.toString();
    const response = await apiClient.get(
      `/api/quiz/student/question-bank${qs ? `?${qs}` : ""}`,
    );
    return response.data as QuestionBankEntry[];
  },
};

// ── Case Rubric API (T-3C) ────────────────────────────────────────────────

export interface DecisionPoint {
  target_action: string;
  score: number;
  rule_outcome: string;
  is_critical: boolean;
  safety_category: string | null;
  competency_tags: string[];
  rubric_level: "critical" | "standard" | "penalty";
}

export interface CaseRubric {
  case_id: string;
  total_max_score: number;
  critical_count: number;
  positive_count: number;
  penalty_count: number;
  computed_at: string;
  decision_points: DecisionPoint[];
}

export const caseRubricAPI = {
  getAllRubrics: async (): Promise<CaseRubric[]> => {
    const response = await apiClient.get("/api/quiz/case-rubrics");
    return response.data as CaseRubric[];
  },
  getRubric: async (caseId: string): Promise<CaseRubric> => {
    const response = await apiClient.get(`/api/quiz/case-rubrics/${encodeURIComponent(caseId)}`);
    return response.data as CaseRubric;
  },
  getCaseIds: async (): Promise<string[]> => {
    const response = await apiClient.get("/api/quiz/case-rubrics-index");
    return response.data as string[];
  },
};


// -- Rubric Version API (T-4B) --

export interface RubricVersionItem {
  id: number;
  question_id: number;
  version: number;
  rubric_guide: string;
  model_answer_outline: string;
  change_notes: string | null;
  created_by: string;
  created_at: string;
}

export const rubricVersionAPI = {
  publishSnapshot: async (
    questionId: number,
    payload: { rubric_guide: string; model_answer_outline: string; change_notes?: string }
  ): Promise<RubricVersionItem> => {
    const response = await apiClient.post(
      `/api/quiz/instructor/questions/${questionId}/rubric-snapshot`,
      payload
    );
    return response.data as RubricVersionItem;
  },

  getVersions: async (questionId: number): Promise<RubricVersionItem[]> => {
    const response = await apiClient.get(
      `/api/quiz/instructor/questions/${questionId}/rubric-versions`
    );
    return response.data as RubricVersionItem[];
  },

  getVersion: async (versionId: number): Promise<RubricVersionItem> => {
    const response = await apiClient.get(
      `/api/quiz/instructor/rubric-versions/${versionId}`
    );
    return response.data as RubricVersionItem;
  },
};


// -- Mini-Case API (T-5B) --

export interface MiniCaseListItem {
  id: number;
  mini_case_id: string;
  title: string;
  difficulty: string;
  linked_topic_ids: string[];
  question_count: number;
}

export interface MiniCaseDetail {
  id: number;
  mini_case_id: string;
  title: string;
  clinical_vignette: string;
  key_findings: string[];
  question_ids: string[];
  learning_objectives: string[];
  linked_topic_ids: string[];
  difficulty: string;
}

export const miniCaseAPI = {
  getAll: async (): Promise<MiniCaseListItem[]> => {
    const response = await apiClient.get('/api/mini-cases');
    return response.data as MiniCaseListItem[];
  },
  getById: async (miniCaseId: string): Promise<MiniCaseDetail> => {
    const response = await apiClient.get(`/api/mini-cases/${encodeURIComponent(miniCaseId)}`);
    return response.data as MiniCaseDetail;
  },
};

export interface NotificationItem {
  id: number;
  type: string;
  payload: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export const notificationAPI = {
  getAll: async (unreadOnly = false): Promise<NotificationItem[]> => {
    const response = await apiClient.get('/api/notifications', { params: { unread_only: unreadOnly } });
    return response.data as NotificationItem[];
  },
  getUnreadCount: async (): Promise<number> => {
    const response = await apiClient.get('/api/notifications/unread-count');
    return (response.data as { count: number }).count;
  },
  markAsRead: async (id: number): Promise<void> => {
    await apiClient.patch(`/api/notifications/${id}/read`);
  },
  markAllAsRead: async (): Promise<void> => {
    await apiClient.patch('/api/notifications/read-all');
  },
};

// ── S10-A: Reinforcement types ────────────────────────────────────────────────

export interface ReinforcementQuestion {
  question_id: string;
  topic_id: string;
  question_text: string;
}

export interface ChatApiResponse {
  session_id: number | null;
  ai_response: string;
  final_feedback: string | null;
  state_updates: Record<string, unknown>;
  revealed_findings: string[];
  reinforcement_questions: ReinforcementQuestion[];
}

// ── S10-B: "Why this score?" explanation types ────────────────────────────────

export interface RubricVersionSnapshot {
  version: number;
  rubric_guide: string;
  model_answer_outline: string;
  created_at: string | null;
}

export interface AnswerExplanationResponse {
  answer_id: number;
  question_id: string;
  question_text: string;
  question_type: string;
  topic_id: string;
  student_response: string;
  auto_score: number | null;
  instructor_score: number | null;
  ai_score_suggestion: number | null;
  ai_score_rationale: string | null;
  max_score: number;
  grading_status: string;
  rubric_guide: string | null;
  rubric_version_snapshot: RubricVersionSnapshot | null;
}

export const explanationAPI = {
  getAnswerExplanation: async (
    attemptId: number,
    answerId: number
  ): Promise<AnswerExplanationResponse> => {
    const response = await apiClient.get(
      `/api/quiz/my-attempts/${attemptId}/answers/${answerId}/explanation`
    );
    return response.data as AnswerExplanationResponse;
  },
};

// ── S10-C: Spaced repetition review schedule ──────────────────────────────────

export interface ReviewScheduleItem {
  id: number;
  question_id: string;
  question_text: string;
  topic_id: string;
  due_date: string;
  interval_days: number;
  ease_factor: number;
  repetitions: number;
  last_reviewed_at: string | null;
}

export interface SubmitReviewResult {
  id: number;
  next_due_date: string;
  next_interval_days: number;
  repetitions: number;
}

export const reviewScheduleAPI = {
  getDueItems: async (): Promise<ReviewScheduleItem[]> => {
    const response = await apiClient.get('/api/quiz/my-review-schedule');
    return response.data as ReviewScheduleItem[];
  },
  submitResult: async (itemId: number, rating: number): Promise<SubmitReviewResult> => {
    const response = await apiClient.post(
      `/api/quiz/my-review-schedule/${itemId}/result`,
      { rating }
    );
    return response.data as SubmitReviewResult;
  },
};

// ==================== S11-A: Research Snapshots ====================

export interface SnapshotSummary {
  id: number;
  label: string;
  created_by: string;
  notes: string | null;
  git_commit_hash: string | null;
  questions_count: number;
  cases_count: number;
  bundle_size_bytes: number | null;
  created_at: string;
}

export interface SnapshotDetail extends SnapshotSummary {
  scoring_config_payload: Record<string, unknown>;
  llm_config_payload: Record<string, unknown>;
}

export interface SnapshotCreateRequest {
  label: string;
  notes?: string;
}

export const researchAPI = {
  createSnapshot: async (body: SnapshotCreateRequest): Promise<SnapshotSummary> => {
    const response = await apiClient.post('/api/research/snapshots', body);
    return response.data as SnapshotSummary;
  },
  listSnapshots: async (): Promise<SnapshotSummary[]> => {
    const response = await apiClient.get('/api/research/snapshots');
    return response.data as SnapshotSummary[];
  },
  getSnapshot: async (id: number): Promise<SnapshotDetail> => {
    const response = await apiClient.get(`/api/research/snapshots/${id}`);
    return response.data as SnapshotDetail;
  },
  getExportUrl: (id: number): string => `${API_URL}/api/research/snapshots/${id}/export`,
};
