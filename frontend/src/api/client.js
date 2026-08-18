import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
});

// Normalize axios errors into our own ApiError shape, so callers
// never need to know axios is involved - they just check err.status.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with a non-2xx status
      const message = error.response.data?.detail ?? error.response.statusText;
      throw new ApiError(error.response.status, message);
    }
    // Network error, timeout, no response received at all
    throw new ApiError(0, error.message);
  },
);

/**
 * Low-level request helper. Not called directly by pages/components -
 * resource-specific modules (documents.js, conversations.js) wrap this.
 *
 * @param {string} path - e.g. '/projects/1/documents'
 * @param {import('axios').AxiosRequestConfig} config
 */
export async function request(path, config = {}) {
  const response = await apiClient.request({ url: path, ...config });
  return response.data;
}