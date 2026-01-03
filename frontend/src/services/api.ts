/**
 * API Client Service
 * Handles all HTTP requests to the backend API
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle authentication errors
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    
    // Handle other errors
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ==================== Authentication API ====================

export const authAPI = {
  /**
   * Login with email and password
   */
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    
    // Store tokens
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
    }
    
    return response.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
    
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
    }
    
    return response.data;
  },

  /**
   * Get current user information
   */
  getCurrentUser: () => api.get('/auth/me'),

  /**
   * Logout
   */
  logout: async () => {
    await api.post('/auth/logout');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// ==================== Accounts API ====================

export const accountsAPI = {
  /**
   * List all AWS accounts
   */
  list: () => api.get('/accounts/'),

  /**
   * Get account by ID
   */
  get: (accountId: string) => api.get(`/accounts/${accountId}`),

  /**
   * Create new AWS account
   */
  create: (data: {
    aws_account_id: string;
    aws_account_name: string;
    role_arn: string;
    external_id?: string;
    tags?: Record<string, any>;
  }) => api.post('/accounts/', data),

  /**
   * Update account
   */
  update: (accountId: string, data: any) => 
    api.patch(`/accounts/${accountId}`, data),

  /**
   * Delete account
   */
  delete: (accountId: string) => api.delete(`/accounts/${accountId}`),

  /**
   * Trigger account scan
   */
  scan: (accountId: string, scanType: string = 'full') => 
    api.post(`/accounts/${accountId}/scan`, null, { params: { scan_type: scanType } }),

  /**
   * Test AWS connection
   */
  testConnection: (accountId: string) => 
    api.post(`/accounts/${accountId}/test-connection`),
};

// ==================== Cost Analysis API ====================

export const costAPI = {
  /**
   * Get cost summary
   */
  getSummary: (accountId: string, days: number = 30) =>
    api.get(`/cost/${accountId}/summary`, { params: { days } }),

  /**
   * Get cost trend data
   */
  getTrend: (accountId: string, days: number = 30, groupBy: string = 'day') =>
    api.get(`/cost/${accountId}/trend`, { params: { days, group_by: groupBy } }),

  /**
   * Analyze costs and get recommendations
   */
  analyze: (accountId: string) => 
    api.post(`/cost/${accountId}/analyze`),

  /**
   * Sync cost data from AWS
   */
  sync: (accountId: string, days: number = 30) =>
    api.post(`/cost/${accountId}/sync`, null, { params: { days } }),

  /**
   * Get cost forecast
   */
  getForecast: (accountId: string, daysAhead: number = 30) =>
    api.get(`/cost/${accountId}/forecast`, { params: { days_ahead: daysAhead } }),
};

// ==================== Security API ====================

export const securityAPI = {
  /**
   * List security findings
   */
  listFindings: (
    accountId: string,
    params?: {
      severity?: string;
      status?: string;
      resource_type?: string;
      limit?: number;
      offset?: number;
    }
  ) => api.get(`/security/${accountId}/findings`, { params }),

  /**
   * Get security summary
   */
  getSummary: (accountId: string) => 
    api.get(`/security/${accountId}/summary`),

  /**
   * Run security scan
   */
  scan: (accountId: string, fullScan: boolean = true) =>
    api.post(`/security/${accountId}/scan`, null, { params: { full_scan: fullScan } }),

  /**
   * Get finding details
   */
  getFinding: (accountId: string, findingId: string) =>
    api.get(`/security/${accountId}/finding/${findingId}`),

  /**
   * Update finding status
   */
  updateFindingStatus: (
    accountId: string,
    findingId: string,
    status: string,
    reason?: string
  ) => api.patch(`/security/${accountId}/finding/${findingId}/status`, null, {
    params: { new_status: status, reason },
  }),

  /**
   * Get compliance report
   */
  getComplianceReport: (accountId: string, framework: string) =>
    api.get(`/security/${accountId}/compliance/${framework}`),

  /**
   * Export security report
   */
  exportReport: (accountId: string, format: string = 'json') =>
    api.get(`/security/${accountId}/export`, { params: { format } }),
};

// ==================== Recommendations API ====================

export const recommendationsAPI = {
  /**
   * List recommendations
   */
  list: (
    accountId: string,
    params?: {
      type?: string;
      priority?: string;
      status?: string;
      limit?: number;
      offset?: number;
    }
  ) => api.get(`/recommendations/${accountId}/recommendations`, { params }),

  /**
   * Get recommendations summary
   */
  getSummary: (accountId: string) =>
    api.get(`/recommendations/${accountId}/summary`),

  /**
   * Get recommendation details
   */
  get: (accountId: string, recommendationId: string) =>
    api.get(`/recommendations/${accountId}/recommendation/${recommendationId}`),

  /**
   * Update recommendation status
   */
  updateStatus: (
    accountId: string,
    recommendationId: string,
    status: string,
    reason?: string
  ) => api.patch(
    `/recommendations/${accountId}/recommendation/${recommendationId}/status`,
    null,
    { params: { new_status: status, reason } }
  ),

  /**
   * Execute recommendation
   */
  execute: (
    accountId: string,
    recommendationId: string,
    actionType: string,
    autoApprove: boolean = false
  ) => api.post(
    `/recommendations/${accountId}/recommendation/${recommendationId}/execute`,
    { action_type: actionType, auto_approve: autoApprove }
  ),

  /**
   * Rollback recommendation
   */
  rollback: (accountId: string, recommendationId: string) =>
    api.post(`/recommendations/${accountId}/recommendation/${recommendationId}/rollback`),

  /**
   * List execution logs
   */
  listLogs: (accountId: string, limit: number = 100, offset: number = 0) =>
    api.get(`/recommendations/${accountId}/execution-logs`, {
      params: { limit, offset },
    }),

  /**
   * Bulk approve recommendations
   */
  bulkApprove: (accountId: string, recommendationIds: string[]) =>
    api.post(`/recommendations/${accountId}/bulk-approve`, {
      recommendation_ids: recommendationIds,
    }),
};

// ==================== Health Check ====================

export const healthAPI = {
  /**
   * Check API health
   */
  check: () => api.get('/health', { baseURL: API_BASE_URL }),
};

// Export default API instance
export default api;
