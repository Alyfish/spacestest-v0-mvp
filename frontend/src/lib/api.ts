import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000/api";

// API client functions
const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }
    return response.json();
  },
};

// API response types
export interface HealthResponse {
  status: string;
  message: string;
}

export interface RootResponse {
  message: string;
}

// React Query hooks
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<HealthResponse>("/health"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useRootEndpoint = () => {
  return useQuery({
    queryKey: ["root"],
    queryFn: () => apiClient.get<RootResponse>("/"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
