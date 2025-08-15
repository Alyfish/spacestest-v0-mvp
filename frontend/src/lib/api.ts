import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: data ? JSON.stringify(data) : undefined,
    });
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

export interface ProjectCreateResponse {
  project_id: string;
  status: string;
  message: string;
}

export interface ProjectResponse {
  project_id: string;
  status: string;
  created_at: string;
  context: Record<string, any>;
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

export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.post<ProjectCreateResponse>("/projects"),
    onSuccess: () => {
      // Invalidate projects list if we add one later
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
};

export const useGetProject = (projectId: string) => {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiClient.get<ProjectResponse>(`/projects/${projectId}`),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
