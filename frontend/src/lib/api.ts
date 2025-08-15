import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000/api";

// Helper function to get image URL
export const getProjectImageUrl = (projectId: string) =>
  `${API_BASE_URL}/projects/${projectId}/base-image`;

// Helper function to get labelled image URL
export const getProjectLabelledImageUrl = (projectId: string) =>
  `${API_BASE_URL}/projects/${projectId}/labelled-image`;

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

  async uploadFile<T>(endpoint: string, file: File): Promise<T> {
    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
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

export interface ProjectsListResponse {
  projects: Record<
    string,
    {
      status: string;
      created_at: string;
      context: Record<string, any>;
    }
  >;
  total_count: number;
}

export interface ImageUploadResponse {
  project_id: string;
  image_path: string;
  status: string;
  message: string;
}

export interface SpaceTypeRequest {
  space_type: string;
}

export interface SpaceTypeResponse {
  project_id: string;
  space_type: string;
  status: string;
  message: string;
}

export interface ImprovementMarker {
  id: string;
  position: { x: number; y: number };
  description: string;
  color: string; // Required since it's always added by backend
}

export interface ImprovementMarkersRequest {
  markers: ImprovementMarker[];
}

export interface ImprovementMarkersResponse {
  project_id: string;
  markers: ImprovementMarker[];
  labelled_image_path: string;
  status: string;
  message: string;
}

export interface MarkerRecommendationsResponse {
  project_id: string;
  space_type: string;
  recommendations: string[];
  status: string;
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

export const useGetAllProjects = () => {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.get<ProjectsListResponse>("/projects"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUploadProjectImage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, file }: { projectId: string; file: File }) =>
      apiClient.uploadFile<ImageUploadResponse>(
        `/projects/${projectId}/upload-image`,
        file
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSelectSpaceType = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      spaceType,
    }: {
      projectId: string;
      spaceType: string;
    }) =>
      apiClient.post<SpaceTypeResponse>(`/projects/${projectId}/space-type`, {
        space_type: spaceType,
      }),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSaveImprovementMarkers = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      markers,
    }: {
      projectId: string;
      markers: ImprovementMarker[];
    }) =>
      apiClient.post<ImprovementMarkersResponse>(
        `/projects/${projectId}/improvement-markers`,
        { markers }
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useGetMarkerRecommendations = (projectId: string) => {
  return useQuery({
    queryKey: ["marker-recommendations", projectId],
    queryFn: () =>
      apiClient.get<MarkerRecommendationsResponse>(
        `/projects/${projectId}/marker-recommendations`
      ),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
