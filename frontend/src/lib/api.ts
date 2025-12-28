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

  async uploadFiles<T>(endpoint: string, files: File[]): Promise<T> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("images", file);
    });

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }
    return response.json();
  },

  async delete(endpoint: string): Promise<void> {
    console.log(`Deleting endpoint: ${API_BASE_URL}${endpoint}`);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "DELETE",
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

export const useGenerateImage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<ImageGenerationResponse>(
        `/projects/${projectId}/generate-image`
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
    },
  });
};

export const useGenerateInspirationRedesign = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<InspirationImageGenerationResponse>(
        `/projects/${projectId}/inspiration-redesign`
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
