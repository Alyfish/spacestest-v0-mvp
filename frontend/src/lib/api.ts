import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000/api";

// Helper function to get image URL
export const getProjectImageUrl = (projectId: string) =>
  `${API_BASE_URL}/projects/${projectId}/base-image`;

// Helper function to get labelled image URL
export const getProjectLabelledImageUrl = (projectId: string) =>
  `${API_BASE_URL}/projects/${projectId}/labelled-image`;

// Helper function to get generated image URL
export const getProjectGeneratedImageUrl = (projectId: string) =>
  `${API_BASE_URL}/projects/${projectId}/generated-image`;

// API client functions
export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE_URL}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  },

  async post<T>(endpoint: string, data?: any): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: data ? JSON.stringify(data) : undefined,
      });
      
      if (!response.ok) {
        let message = response.statusText;
        try {
          const err = await response.json();
          // FastAPI returns { detail: "..." }
          if (err && (err.detail || err.message)) {
            message = err.detail || err.message;
          }
        } catch { }
        throw new Error(`(${response.status}) ${message}`);
      }
      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE_URL}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  },

  async uploadFile<T>(endpoint: string, file: File): Promise<T> {
    try {
      const formData = new FormData();
      formData.append("image", file);

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE_URL}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  },

  async uploadFiles<T>(endpoint: string, files: File[]): Promise<T> {
    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("images", file);
      });

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE_URL}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  },

  async delete(endpoint: string): Promise<void> {
    try {
      console.log(`Deleting endpoint: ${API_BASE_URL}${endpoint}`);
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "DELETE",
        credentials: "include",
      });
      
      if (!response.ok) {
        let message = response.statusText;
        try {
          const err = await response.json();
          if (err && (err.detail || err.message)) {
            message = err.detail || err.message;
          }
        } catch { }
        throw new Error(`(${response.status}) ${message}`);
      }
      // Attempt to parse JSON response but don't fail if void is expected
      try {
        await response.json();
      } catch { }
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE_URL}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
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

export interface InspirationImageUploadResponse {
  project_id: string;
  image_path: string;
  status: string;
  message: string;
}

export interface InspirationImagesBatchUploadResponse {
  project_id: string;
  image_paths: string[];
  uploaded_count: number;
  status: string;
  message: string;
}

export interface InspirationRecommendationsResponse {
  project_id: string;
  space_type: string;
  recommendations: string[];
  status: string;
  message: string;
}

export interface ProductRecommendationsResponse {
  project_id: string;
  space_type: string;
  recommendations: string[];
  status: string;
  message: string;
}

export interface ProductRecommendationSelectionRequest {
  selected_recommendation: string;
}

export interface ProductRecommendationSelectionResponse {
  project_id: string;
  selected_recommendations: string[];
  status: string;
  message: string;
}

export interface ProductSearchResponse {
  project_id: string;
  selected_recommendation: string;
  search_query: string;
  products: Array<{
    url: string;
    title: string;
    store_name: string;
    price: string;
    original_price?: string;
    discount?: string;
    availability: string;
    shipping: string;
    materials: string[];
    colors: string[];
    dimensions: string[];
    features: string[];
    rating?: string;
    reviews_count?: string;
    relevance_score: number;
    extract: string;
    is_product_page: boolean;
    images: string[];
    source_api?: string; // "exa" or "serp"
    search_method?: string; // "Provider-Specific" or "Google Shopping"
  }>;
  total_found: number;
  status: string;
  message: string;
}

export interface ProductSelectionRequest {
  product_url: string;
  product_title: string;
  product_image_url: string;
  generation_prompt?: string;
}

export interface ProductSelectionResponse {
  project_id: string;
  selected_products: Array<{
    url: string;
    title: string;
    image_url: string;
    selected_at: string;
  }>;
  status: string;
  message: string;
}

export interface ImageGenerationResponse {
  project_id: string;
  selected_products: Array<{
    url: string;
    title: string;
    image_url: string;
    selected_at: string;
  }>;
  generated_image_base64: string; // Changed from URL to base64
  generation_prompt: string;
  status: string;
  message: string;
  model_used?: string; // The Gemini model used for generation
}

export interface ClipRect {
  x: number; // 0-1
  y: number; // 0-1
  width: number; // 0-1
  height: number; // 0-1
}

export interface ClipSearchRequest {
  rect: ClipRect;
}

export interface ClipSearchResponse {
  project_id: string;
  rect: ClipRect;
  search_query: string;
  products: ProductSearchResponse["products"];
  total_found: number;
  status: string;
  message: string;
  agent_notes?: Record<string, any>;
}

export interface InspirationImageGenerationResponse {
  project_id: string;
  generated_image_base64: string;
  inspiration_prompt: string;
  inspiration_recommendations: string[];
  status: string;
  message: string;
  model_used?: string; // The Gemini model used for generation
}

// ============================================================================
// Background Job Types (Supabase-backed)
// ============================================================================

export interface JobStartResponse {
  job_id: string;
  status: "queued";
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "processing" | "done" | "error" | "cancelled";
  progress_pct: number;
  phase: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  error_code: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface JobListResponse {
  project_id: string;
  jobs: Array<{
    job_id: string;
    job_type: string;
    status: string;
    progress_pct: number;
    phase: string | null;
    created_at: string | null;
  }>;
  total: number;
}

// Generate unique idempotency key
export const generateIdempotencyKey = (): string => {
  return crypto.randomUUID();
};

// Polling delays with backoff: 1s x5, 2s x2, 3s x2, then 5s
const POLL_DELAYS = [1000, 1000, 1000, 1000, 1000, 2000, 2000, 3000, 3000, 5000];

// Sleep helper
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Poll for job completion with progress callback
export async function waitForJob<T>(
  projectId: string,
  jobId: string,
  onProgress?: (progress: number, phase: string | null) => void,
  maxWaitMs: number = 120000 // 2 minutes default
): Promise<T> {
  const startTime = Date.now();
  let pollIndex = 0;

  while (Date.now() - startTime < maxWaitMs) {
    const job = await apiClient.get<JobStatusResponse>(
      `/projects/${projectId}/job-status/${jobId}`
    );

    if (job.status === "done") {
      return job.result as T;
    }

    if (job.status === "error") {
      throw new Error(job.error || "Job failed");
    }

    if (job.status === "cancelled") {
      throw new Error("Job was cancelled");
    }

    // Call progress callback
    if (onProgress) {
      onProgress(job.progress_pct, job.phase);
    }

    // Wait with backoff
    const delay = POLL_DELAYS[Math.min(pollIndex, POLL_DELAYS.length - 1)];
    await sleep(delay);
    pollIndex++;
  }

  throw new Error("Job timed out - still processing. Please refresh to check status.");
}

// Start a background job with idempotency key
export async function startBackgroundJob(
  endpoint: string,
  data?: Record<string, unknown>,
  idempotencyKey?: string
): Promise<JobStartResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (idempotencyKey) {
    headers["X-Idempotency-Key"] = idempotencyKey;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: data ? JSON.stringify(data) : undefined,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const err = await response.json();
      if (err && (err.detail || err.message)) {
        message = err.detail || err.message;
      }
    } catch {}
    throw new Error(`(${response.status}) ${message}`);
  }

  return response.json();
}

// Color Agent types
export interface ColorAssignment {
  element: string;
  color_hex: string;
  color_name: string;
  finish?: string;
  notes?: string;
}

export interface ColorAnalysis {
  space_summary: string;
  primary_colors: Array<{ hex: string; description: string }>;
  secondary_colors: Array<{ hex: string; description: string }>;
  accent_colors: Array<{ hex: string; description: string }>;
  color_theory_approach: string;
  color_theory_rationale: string;
  color_assignments: ColorAssignment[];
  lighting_notes: string;
  cohesion_tips: string;
  personalization_suggestions: string;
  palette_adaptations?: string;
}

export interface ApplyColorRequest {
  palette_name: string;
  colors: string[];
  let_ai_decide: boolean;
}

export interface ApplyColorResponse {
  project_id: string;
  palette_name: string;
  color_analysis: ColorAnalysis;
  status: string;
  message: string;
}

// Style Agent types
export interface FurnitureRecommendation {
  item_type: string;
  description: string;
  materials: string[];
  colors: string[];
  placement_notes?: string;
}

export interface StyleAnalysis {
  style_name: string;
  style_overview: string;
  materials: string[];
  color_palette: string[];
  furniture_characteristics: string;
  patterns_textures: string;
  lighting_style: string;
  decor_accessories: string;
  layout_principles: string;
  styling_tips: string[];
  common_mistakes: string[];
  furniture_recommendations: FurnitureRecommendation[];
  anchor_pieces: string[];
  statement_accessory: string;
  room_transformation: string;
  related_styles: string[];
  style_adaptations?: string;
}

export interface ApplyStyleRequest {
  style_name: string;
  let_ai_decide: boolean;
}
export interface ApplyStyleResponse {
  project_id: string;
  style_name: string;
  style_analysis: StyleAnalysis;
  status: string;
  message: string;
}

export interface SkipStepResponse {
  project_id: string;
  status: string;
  skipped_step: string;
  message: string;
}

// User Preference types
export interface PreferredStoresRequest {
  stores: string[];
}

export interface PreferredStoresResponse {
  project_id: string;
  stores: string[];
  status: string;
  message: string;
}

// React Query hooks
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<HealthResponse>("/health"),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false,
  });
};

export const useRootEndpoint = () => {
  return useQuery({
    queryKey: ["root"],
    queryFn: () => apiClient.get<RootResponse>("/"),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false,
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
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false,
  });
};

export const useDeleteProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => apiClient.delete(`/projects/${projectId}`),
    onSuccess: async () => {
      console.log("Delete successful, invalidating queries...");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      console.log("Queries invalidated.");
    },
    onError: (error) => {
      console.error("Delete project failed:", error);
      alert(`Failed to delete project: ${error.message}`);
    },
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

interface ImprovementModeResponse {
  project_id: string;
  mode: string;
  status: string;
  message: string;
}

export const useSetImprovementMode = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      mode,
    }: {
      projectId: string;
      mode: "iterative" | "complete_revamp";
    }) =>
      apiClient.post<ImprovementModeResponse>(
        `/projects/${projectId}/improvement-mode`,
        { mode }
      ),
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

export const useGetMarkerRecommendations = (projectId: string, enabled: boolean) => {
  return useQuery({
    queryKey: ["marker-recommendations", projectId],
    queryFn: () =>
      apiClient.get<MarkerRecommendationsResponse>(
        `/projects/${projectId}/marker-recommendations`
      ),
    enabled: !!projectId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useGenerateMarkerRecommendations = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<MarkerRecommendationsResponse>(
        `/projects/${projectId}/marker-recommendations`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
      queryClient.invalidateQueries({ queryKey: ["marker-recommendations", data.project_id] });
    },
  });
};

export const useUploadInspirationImage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, file }: { projectId: string; file: File }) =>
      apiClient.uploadFile<InspirationImageUploadResponse>(
        `/projects/${projectId}/inspiration-image`,
        file
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useUploadInspirationImagesBatch = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, files }: { projectId: string; files: File[] }) =>
      apiClient.uploadFiles<InspirationImagesBatchUploadResponse>(
        `/projects/${projectId}/inspiration-images-batch`,
        files
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useGenerateInspirationRecommendations = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<InspirationRecommendationsResponse>(
        `/projects/${projectId}/inspiration-recommendations`
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Helper function to get inspiration image URL
export const getInspirationImageUrl = (projectId: string, imageIndex: number) =>
  `${API_BASE_URL}/projects/${projectId}/inspiration-image/${imageIndex}`;

export const useGenerateProductRecommendations = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<ProductRecommendationsResponse>(
        `/projects/${projectId}/product-recommendations`
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSelectProductRecommendation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      selectedRecommendation,
    }: {
      projectId: string;
      selectedRecommendation: string;
    }) =>
      apiClient.post<ProductRecommendationSelectionResponse>(
        `/projects/${projectId}/product-recommendation-selection`,
        { selected_recommendation: selectedRecommendation }
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSearchProducts = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<ProductSearchResponse>(
        `/projects/${projectId}/product-search`
      ),
    onSuccess: (data) => {
      // Invalidate the project query to refresh the data
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

interface AutoSelectProductResponse {
  project_id: string;
  selected_product: {
    url: string;
    title: string;
    store_name: string;
    price: string;
    images: string[];
    similarity_score?: number;
    store_trust?: number;
    [key: string]: unknown;
  };
  selection_reason: string;
  alternatives: Array<{
    url: string;
    title: string;
    store_name: string;
    price: string;
    images: string[];
    [key: string]: unknown;
  }>;
  status: string;
  message: string;
}

export const useAutoSelectProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<AutoSelectProductResponse>(
        `/projects/${projectId}/auto-select-product`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSelectProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      productSelection,
    }: {
      projectId: string;
      productSelection: ProductSelectionRequest;
    }) =>
      apiClient.post<ProductSelectionResponse>(
        `/projects/${projectId}/product-selection`,
        productSelection
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Background job version - returns job_id, caller must poll
export const useStartGenerateImage = () => {
  return useMutation({
    mutationFn: async ({
      projectId,
      idempotencyKey,
    }: {
      projectId: string;
      idempotencyKey?: string;
    }) => {
      return startBackgroundJob(
        `/projects/${projectId}/generate-image`,
        undefined,
        idempotencyKey || generateIdempotencyKey()
      );
    },
  });
};

// Full flow: start job + poll until complete
export const useGenerateImage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      onProgress,
    }: {
      projectId: string;
      onProgress?: (progress: number, phase: string | null) => void;
    }) => {
      // Start the job
      const { job_id } = await startBackgroundJob(
        `/projects/${projectId}/generate-image`,
        undefined,
        generateIdempotencyKey()
      );

      // Poll until complete
      const result = await waitForJob<{
        project_id: string;
        selected_products: Array<{
          url: string;
          title: string;
          image_url: string;
          selected_at: string;
        }>;
        generation_prompt: string;
        status: string;
        message: string;
        model_used?: string;
        has_generated_image: boolean;
      }>(projectId, job_id, onProgress);

      return { ...result, project_id: projectId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Background job version - returns job_id, caller must poll
export const useStartInspirationRedesign = () => {
  return useMutation({
    mutationFn: async ({
      projectId,
      idempotencyKey,
    }: {
      projectId: string;
      idempotencyKey?: string;
    }) => {
      return startBackgroundJob(
        `/projects/${projectId}/inspiration-redesign`,
        undefined,
        idempotencyKey || generateIdempotencyKey()
      );
    },
  });
};

// Full flow: start job + poll until complete
export const useGenerateInspirationRedesign = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      onProgress,
    }: {
      projectId: string;
      onProgress?: (progress: number, phase: string | null) => void;
    }) => {
      // Start the job
      const { job_id } = await startBackgroundJob(
        `/projects/${projectId}/inspiration-redesign`,
        undefined,
        generateIdempotencyKey()
      );

      // Poll until complete
      const result = await waitForJob<{
        project_id: string;
        inspiration_prompt: string;
        inspiration_recommendations: string[];
        status: string;
        message: string;
        model_used?: string;
        has_generated_image: boolean;
      }>(projectId, job_id, onProgress);

      return { ...result, project_id: projectId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useRetryRedesign = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      feedback,
    }: {
      projectId: string;
      feedback: string;
    }) =>
      apiClient.post<InspirationImageGenerationResponse>(
        `/projects/${projectId}/retry-redesign`,
        { feedback }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useClipSearch = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      rect,
      useInspirationImage = false,
    }: {
      projectId: string;
      rect: ClipRect;
      useInspirationImage?: boolean;
    }) =>
      apiClient.post<ClipSearchResponse>(
        `/projects/${projectId}/clip-search`,
        { rect, use_inspiration_image: useInspirationImage }
      ),
    onSuccess: (data) => {
      // Refresh project to capture any future state effects if added
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Auto detection (YOLO when available)
export const useAutoDetect = () => {
  return useMutation({
    mutationFn: ({ projectId, imageType = "product" }: { projectId: string; imageType?: "product" | "inspiration" }) =>
      apiClient.get<{ project_id: string; detections: Array<{ label: string; rect: { x: number; y: number; width: number; height: number }; center: { x: number; y: number } }> }>(
        `/projects/${projectId}/auto-detect?image_type=${imageType}`
      ),
  });
};

// Color Agent - Apply color scheme with AI analysis
export const useApplyColorScheme = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      paletteName,
      colors,
      letAiDecide = false,
    }: {
      projectId: string;
      paletteName: string;
      colors: string[];
      letAiDecide?: boolean;
    }) =>
      apiClient.post<ApplyColorResponse>(
        `/projects/${projectId}/apply-color-scheme`,
        {
          palette_name: paletteName,
          colors: colors,
          let_ai_decide: letAiDecide,
        }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Style Agent - Apply design style with AI analysis
export const useApplyStyle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      styleName,
      letAiDecide = false,
    }: {
      projectId: string;
      styleName: string;
      letAiDecide?: boolean;
    }) =>
      apiClient.post<ApplyStyleResponse>(
        `/projects/${projectId}/apply-style`,
        {
          style_name: styleName,
          let_ai_decide: letAiDecide,
        }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSkipColorAnalysis = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<SkipStepResponse>(
        `/projects/${projectId}/skip-color-analysis`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSkipStyleAnalysis = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<SkipStepResponse>(
        `/projects/${projectId}/skip-style-analysis`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useSkipInspirationImages = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<SkipStepResponse>(
        `/projects/${projectId}/skip-inspiration-images`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// User Preference - Update preferred stores
export const useUpdatePreferredStores = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      stores,
    }: {
      projectId: string;
      stores: string[];
    }) =>
      apiClient.post<PreferredStoresResponse>(
        `/projects/${projectId}/preferred-stores`,
        { stores }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// ============================================================================
// "Like These?" Product Suggestions Feature
// ============================================================================

export interface PreSearchedProduct {
  url: string;
  title: string;
  image_url: string;
  store: string;
  price_str?: string;
  price?: number;
  similarity_score?: number;
}

export interface PreSearchedCategory {
  recommendation: string;
  search_query: string;
  status: "pending" | "complete" | "error";
  products: PreSearchedProduct[];
  searched_at?: string;
  error_message?: string;
}

export interface SearchRecommendationsResponse {
  project_id: string;
  categories: PreSearchedCategory[];
  total_products: number;
  status: string;
  message: string;
}

export interface ProductSuggestionsResponse {
  project_id: string;
  categories: PreSearchedCategory[];
  total_products: number;
  overall_status: string;
  message: string;
}

export interface FavoriteProduct {
  category: string;
  url: string;
  title: string;
  image_url: string;
  store: string;
  price_str?: string;
}

export interface FavoriteProductsResponse {
  project_id: string;
  favorites_count: number;
  favorites_by_category: Record<string, number>;
  status: string;
  message: string;
}

// Background job version - returns job_id, caller must poll
export const useStartSearchRecommendations = () => {
  return useMutation({
    mutationFn: async ({
      projectId,
      recommendations,
      idempotencyKey,
    }: {
      projectId: string;
      recommendations: string[];
      idempotencyKey?: string;
    }) => {
      return startBackgroundJob(
        `/projects/${projectId}/search-recommendations`,
        { recommendations },
        idempotencyKey || generateIdempotencyKey()
      );
    },
  });
};

// Full flow: start job + poll until complete
export const useSearchRecommendations = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      recommendations,
      onProgress,
    }: {
      projectId: string;
      recommendations: string[];
      onProgress?: (progress: number, phase: string | null) => void;
    }) => {
      // Start the job
      const { job_id } = await startBackgroundJob(
        `/projects/${projectId}/search-recommendations`,
        { recommendations },
        generateIdempotencyKey()
      );

      // Poll until complete
      const result = await waitForJob<{
        project_id: string;
        categories: PreSearchedCategory[];
        total_products: number;
        status: string;
        message: string;
      }>(projectId, job_id, onProgress);

      return { ...result, project_id: projectId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
      queryClient.invalidateQueries({ queryKey: ["product-suggestions", data.project_id] });
    },
  });
};

// Get pre-searched product suggestions
export const useGetProductSuggestions = (projectId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ["product-suggestions", projectId],
    queryFn: () =>
      apiClient.get<ProductSuggestionsResponse>(
        `/projects/${projectId}/product-suggestions`
      ),
    enabled: !!projectId && enabled,
    staleTime: 60 * 1000, // 1 minute
  });
};

// Save user's favorite products
export const useSetFavoriteProducts = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      favorites,
    }: {
      projectId: string;
      favorites: FavoriteProduct[];
    }) =>
      apiClient.post<FavoriteProductsResponse>(
        `/projects/${projectId}/favorite-products`,
        { favorites }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// Selected Trending Products for image generation
export interface SelectedTrendingProduct {
  category: string;
  url: string;
  title: string;
  image_url: string;
  store: string;
  price_str?: string;
}

export interface SelectedTrendingProductsResponse {
  project_id: string;
  products_count: number;
  products_by_category: Record<string, number>;
  status: string;
  message: string;
}

// Set selected trending products for image generation
export const useSetSelectedTrendingProducts = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      products,
    }: {
      projectId: string;
      products: SelectedTrendingProduct[];
    }) =>
      apiClient.post<SelectedTrendingProductsResponse>(
        `/projects/${projectId}/selected-trending-products`,
        { products }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

// ============================================================================
// Process Furniture Selection (URL Resolution + Affiliate Cart)
// ============================================================================

export interface SelectedFurnitureProduct {
  url: string;
  title: string;
  image_url?: string;
  store?: string;
  price_str?: string;
  price?: number;
  furniture_id?: string;
}

export interface ResolvedProduct {
  original_url: string;
  resolved_url: string;
  title: string;
  image_url?: string;
  store?: string;
  price_str?: string;
  was_google_shopping: boolean;
  affiliate_url?: string;
  product_id?: string;
}

export interface AffiliateProduct {
  original_url: string;
  affiliate_url: string;
  product_id: string;
  retailer: string;
}

export interface RetailerCart {
  retailer: string;
  retailer_display_name: string;
  products: AffiliateProduct[];
  cart_url: string | null;
  product_count: number;
}

export interface ProcessFurnitureSelectionResponse {
  project_id: string;
  resolved_products: ResolvedProduct[];
  retailer_carts: RetailerCart[];
  total_products: number;
  resolved_count: number;
  unresolved_count: number;
  status: string;
  message: string;
}

// Process selected furniture products (resolve URLs + generate affiliate carts)
export const useProcessFurnitureSelection = () => {
  return useMutation({
    mutationFn: ({
      projectId,
      selectedProducts,
    }: {
      projectId: string;
      selectedProducts: SelectedFurnitureProduct[];
    }) =>
      apiClient.post<ProcessFurnitureSelectionResponse>(
        `/projects/${projectId}/process-furniture-selection`,
        { selected_products: selectedProducts }
      ),
  });
};

// ============================================================================
// Job Management Hooks
// ============================================================================

// Get job status (for manual polling)
export const useGetJobStatus = (projectId: string, jobId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ["job-status", projectId, jobId],
    queryFn: () =>
      apiClient.get<JobStatusResponse>(
        `/projects/${projectId}/job-status/${jobId}`
      ),
    enabled: !!projectId && !!jobId && enabled,
    refetchInterval: (query) => {
      // Auto-refetch while job is running
      const data = query.state.data;
      if (data && (data.status === "queued" || data.status === "processing")) {
        return 1000; // Poll every 1s while running
      }
      return false; // Stop polling when done
    },
  });
};

// List jobs for a project
export const useGetProjectJobs = (projectId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ["project-jobs", projectId],
    queryFn: () =>
      apiClient.get<JobListResponse>(`/projects/${projectId}/jobs`),
    enabled: !!projectId && enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
};

// Cancel a job
export const useCancelJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      jobId,
    }: {
      projectId: string;
      jobId: string;
    }) =>
      apiClient.post<{ job_id: string; cancelled: boolean; message: string }>(
        `/projects/${projectId}/jobs/${jobId}/cancel`
      ),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["job-status", variables.projectId, variables.jobId],
      });
      queryClient.invalidateQueries({
        queryKey: ["project-jobs", variables.projectId],
      });
    },
  });
};
