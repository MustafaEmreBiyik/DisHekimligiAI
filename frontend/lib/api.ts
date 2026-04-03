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
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("student_id");
        localStorage.removeItem("name");

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
  sendMessage: async (message: string, case_id: string) => {
    const response = await apiClient.post("/api/chat/send", {
      message,
      case_id,
    });
    return response.data;
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

export interface RecommendationItem {
  case_id: string;
  title: string;
  difficulty: string;
  estimated_duration_minutes: number;
  competency_tags: string[];
  reason_code: string;
  reason_text: string;
  priority_score: number;
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
  /**
   * Get personalized recommendations for authenticated student
   */
  getMyRecommendations: async (): Promise<RecommendationResponse> => {
    const response = await apiClient.get("/api/recommendations/me");
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

/**
 * Quiz API
 */
export const quizAPI = {
    /**
     * Get all questions (optionally filtered by topic)
     */
    getQuestions: async (topic?: string) => {
        const params = topic && topic !== 'Tümü' ? `?topic=${encodeURIComponent(topic)}` : '';
        const response = await apiClient.get(`/api/quiz/questions${params}`);
        return response.data;
    },

    /**
     * Get available topics
     */
    getTopics: async () => {
        const response = await apiClient.get('/api/quiz/topics');
        return response.data;
    },
};

export default apiClient;
