/**
 * API Client Configuration
 * ========================
 * Axios instance configured for FastAPI backend communication.
 * Automatically handles JWT token attachment and error responses.
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

// API base URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  getCurrentUser: async () => {
    const response = await apiClient.get("/api/auth/me");
    return response.data;
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
