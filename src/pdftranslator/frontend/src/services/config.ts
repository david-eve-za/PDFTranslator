const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const config = {
  useMockData: USE_MOCK_DATA,
  apiBaseUrl: API_BASE_URL,
};
