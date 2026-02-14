"use client";

import { ColorPaletteScreen } from "@/components/ColorPaletteScreen";
import { GeneratedImageDisplay } from "@/components/GeneratedImageDisplay";
import { ImprovementModeSelector } from "@/components/ImprovementModeSelector";
import { PreferredStoresScreen } from "@/components/PreferredStoresScreen";
import { StyleSelectionScreen } from "@/components/StyleSelectionScreen";
import { ImageMarkerInterface } from "@/components/ImageMarkerInterface";
import { ImageUploadSection } from "@/components/ImageUploadSection";
import { InspirationImageUpload } from "@/components/InspirationImageUpload";
import { InspirationRecommendations } from "@/components/InspirationRecommendations";
import { InspirationRedesignDisplay } from "@/components/InspirationRedesignDisplay";
import { LabelledImageDisplay } from "@/components/LabelledImageDisplay";
import { MarkerRecommendations } from "@/components/MarkerRecommendations";
import { NextActionBar } from "@/components/NextActionBar";
import { ProductRecommendations } from "@/components/ProductRecommendations";
import { ProductSearchResults } from "@/components/ProductSearchResults";
import { ProjectContext } from "@/components/ProjectContext";
import { ProjectDetails } from "@/components/ProjectDetails";
import { ProjectHeader } from "@/components/ProjectHeader";
import { SpaceTypeDisplay } from "@/components/SpaceTypeDisplay";
import { SpaceTypeSelection } from "@/components/SpaceTypeSelection";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import type { WorkflowStep } from "@/components/WorkflowStepper";
import {
  useGenerateMarkerRecommendations,
  useGenerateInspirationRecommendations,
  useGetProject,
  useSetImprovementMode,
} from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;
  const projectQuery = useGetProject(projectId);
  const generateMarkerRecs = useGenerateMarkerRecommendations();
  const generateInspirationRecs = useGenerateInspirationRecommendations();
  const setImprovementMode = useSetImprovementMode();

  // Helper function to determine if we've reached or passed a certain status
  const hasReachedStatus = (targetStatus: string, currentStatus: string) => {
    const statusOrder = [
      "NEW",
      "BASE_IMAGE_UPLOADED",
      "SPACE_TYPE_SELECTED",
      "IMPROVEMENT_MARKERS_SAVED",
      "MARKER_RECOMMENDATIONS_READY",
      "INSPIRATION_IMAGES_UPLOADED",
      "INSPIRATION_RECOMMENDATIONS_READY",
      "PRODUCT_RECOMMENDATIONS_READY",
      "PRODUCT_RECOMMENDATION_SELECTED",
      "PRODUCT_SEARCH_COMPLETE",
      "PRODUCT_SELECTED",
      "IMAGE_GENERATED",
      "INSPIRATION_REDESIGN_COMPLETE",
    ];

    const targetIndex = statusOrder.indexOf(targetStatus);
    const currentIndex = statusOrder.indexOf(currentStatus);

    return currentIndex >= targetIndex;
  };

  if (projectQuery.isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">Loading project...</p>
        </div>
      </div>
    );
  }

  if (projectQuery.isError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="bg-red-100 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h1 className="text-2xl font-bold text-red-800 dark:text-red-200 mb-2">
              Project Not Found
            </h1>
            <p className="text-red-600 dark:text-red-300 mb-4">
              {projectQuery.error?.message ||
                "The project you're looking for doesn't exist or couldn't be loaded."}
            </p>
            <Link
              href="/"
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!projectQuery.data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Project Not Found
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            The project with ID &quot;{projectId}&quot; could not be found.
          </p>
          <Link
            href="/"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  const project = projectQuery.data;
  const isRoomEmpty = project.context.is_base_image_empty_room === true;
  const colorSkipped = Boolean(project.context.color_analysis_skipped);
  const styleSkipped = Boolean(project.context.style_analysis_skipped);
  const inspirationSkipped = Boolean(project.context.inspiration_images_skipped);
  const hasColorContext = Boolean(project.context.color_analysis) || colorSkipped;
  const hasStyleContext = Boolean(project.context.style_analysis) || styleSkipped;
  const hasInspirationContext =
    (project.context.inspiration_recommendations || []).length > 0 ||
    inspirationSkipped;
  const canGenerateMarkerRecs =
    hasColorContext &&
    hasStyleContext &&
    Boolean(project.context.preferred_stores && project.context.preferred_stores.length);
  const canGenerateInspirationRecs =
    project.status === "INSPIRATION_IMAGES_UPLOADED" &&
    hasColorContext &&
    hasStyleContext &&
    (project.context.inspiration_images || []).length > 0;
  const selectedRecommendations = project.context.selected_product_recommendations || [];
  const selectedProducts = project.context.selected_products || [];
  const hasPreferredStores = Boolean(project.context.preferred_stores?.length);
  const hasProductRecommendations =
    (project.context.product_recommendations || []).length > 0;
  const hasTrendingSelections =
    (project.context.selected_trending_products || []).length > 0;
  const hasBaseImage = hasReachedStatus("BASE_IMAGE_UPLOADED", project.status);
  const hasSpaceSetup = hasReachedStatus("SPACE_TYPE_SELECTED", project.status);
  const hasPreferences = hasColorContext && hasStyleContext && hasPreferredStores;
  const hasRecommendations =
    hasReachedStatus("MARKER_RECOMMENDATIONS_READY", project.status) ||
    (project.context.inspiration_recommendations || []).length > 0 ||
    hasProductRecommendations;
  const hasProductFlow =
    hasTrendingSelections ||
    hasReachedStatus("PRODUCT_SEARCH_COMPLETE", project.status) ||
    selectedRecommendations.length > 0 ||
    selectedProducts.length > 0;
  const hasVisualization =
    project.status === "IMAGE_GENERATED" ||
    project.status === "INSPIRATION_REDESIGN_COMPLETE";
  const primaryRecommendation = selectedRecommendations[0] || "";
  const steps: WorkflowStep[] = [
    {
      id: "step-upload",
      label: "Upload Room",
      hint: "Add your base room image to begin.",
      completed: hasBaseImage,
    },
    {
      id: "step-space",
      label: "Define Space",
      hint: "Pick mode, room type, and mark areas to improve.",
      completed: hasSpaceSetup,
    },
    {
      id: "step-preferences",
      label: "Set Preferences",
      hint: "Choose colors, style, and preferred stores.",
      completed: hasPreferences,
    },
    {
      id: "step-recommendations",
      label: "Get Recommendations",
      hint: "Generate AI recommendations from your inputs.",
      completed: hasRecommendations,
    },
    {
      id: "step-products",
      label: "Pick Products",
      hint: "Find and save products to include in the design.",
      completed: hasProductFlow,
    },
    {
      id: "step-visualize",
      label: "Visualize",
      hint: "Generate and refine the final AI redesign.",
      completed: hasVisualization,
    },
  ];
  const nextStep = steps.find((step) => !step.completed);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <ProjectHeader projectId={project.project_id} />

        <main className="max-w-4xl mx-auto pb-28">
          <div className="mt-6">
            <WorkflowStepper steps={steps} />
          </div>

          <div className="mt-6 grid md:grid-cols-2 gap-6">
            <ProjectDetails
              projectId={project.project_id}
              status={project.status}
              createdAt={project.created_at}
            />
            <ProjectContext context={project.context} />
          </div>

          <section id="step-upload">
            <ImageUploadSection
              projectId={project.project_id}
              status={project.status}
              context={project.context}
            />
          </section>

          <section id="step-space">
            {project.status === "BASE_IMAGE_UPLOADED" &&
              !project.context.improvement_mode && (
                <div className="mt-8 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                  <ImprovementModeSelector
                    onSelect={(mode) => {
                      setImprovementMode.mutate({
                        projectId: project.project_id,
                        mode,
                      });
                    }}
                  />
                </div>
              )}

            {project.status === "BASE_IMAGE_UPLOADED" &&
              project.context.improvement_mode && (
                <SpaceTypeSelection projectId={project.project_id} />
              )}

            {project.status === "SPACE_TYPE_SELECTED" &&
              project.context.space_type && (
                <SpaceTypeDisplay spaceType={project.context.space_type} />
              )}

            {project.status === "SPACE_TYPE_SELECTED" && isRoomEmpty && (
              <div className="mt-8 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/20">
                    <svg
                      className="h-8 w-8 text-green-600 dark:text-green-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <h2 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
                    Project Setup Complete!
                  </h2>
                  <p className="mb-4 text-gray-600 dark:text-gray-300">
                    Your {project.context.space_type} space is ready for AI
                    recommendations.
                  </p>
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      Since your room is empty, the AI can provide comprehensive
                      design recommendations for furnishing and decorating your{" "}
                      {project.context.space_type}.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {project.status === "SPACE_TYPE_SELECTED" && !isRoomEmpty && (
              <ImageMarkerInterface projectId={project.project_id} />
            )}
          </section>

          <section id="step-preferences">
            {hasReachedStatus("SPACE_TYPE_SELECTED", project.status) && (
              <ColorPaletteScreen
                projectId={project.project_id}
                currentColorScheme={project.context.color_scheme}
                colorAnalysis={project.context.color_analysis}
                colorAnalysisSkipped={colorSkipped}
              />
            )}

            {hasReachedStatus("SPACE_TYPE_SELECTED", project.status) && (
              <StyleSelectionScreen
                projectId={project.project_id}
                currentDesignStyle={project.context.design_style}
                styleAnalysis={project.context.style_analysis}
                styleAnalysisSkipped={styleSkipped}
              />
            )}

            {hasReachedStatus("SPACE_TYPE_SELECTED", project.status) && (
              <PreferredStoresScreen
                projectId={project.project_id}
                currentPreferredStores={project.context.preferred_stores}
              />
            )}
          </section>

          <section id="step-recommendations">
            {hasReachedStatus("IMPROVEMENT_MARKERS_SAVED", project.status) && (
              <>
                <LabelledImageDisplay
                  projectId={project.project_id}
                  markers={project.context.improvement_markers || []}
                />
                {project.status === "MARKER_RECOMMENDATIONS_READY" ? (
                  <MarkerRecommendations projectId={project.project_id} enabled />
                ) : (
                  <div className="mt-8 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                    <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
                      Complete or skip color/style, then set preferred stores
                    </h3>
                    <p className="text-gray-600 dark:text-gray-300">
                      AI design recommendations will appear after your preferences
                      are set.
                    </p>
                    <div className="mt-4">
                      <button
                        disabled={!canGenerateMarkerRecs || generateMarkerRecs.isPending}
                        onClick={() => generateMarkerRecs.mutate(project.project_id)}
                        className="rounded-xl bg-indigo-600 px-4 py-2 text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {generateMarkerRecs.isPending
                          ? "Generating..."
                          : "Generate Marker Recommendations"}
                      </button>
                      {!canGenerateMarkerRecs && (
                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                          Select or skip color and style, and choose preferred
                          stores to enable generation.
                        </p>
                      )}
                      {generateMarkerRecs.isError && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                          {generateMarkerRecs.error?.message ||
                            "Failed to generate recommendations."}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            {hasReachedStatus("SPACE_TYPE_SELECTED", project.status) && (
              <InspirationImageUpload
                projectId={project.project_id}
                inspirationImages={project.context.inspiration_images || []}
                inspirationSkipped={inspirationSkipped}
              />
            )}

            {hasReachedStatus("INSPIRATION_IMAGES_UPLOADED", project.status) && (
              <InspirationRecommendations
                projectId={project.project_id}
                recommendations={project.context.inspiration_recommendations || []}
                spaceType={project.context.space_type || "unknown"}
                colorAnalysis={project.context.color_analysis}
                styleAnalysis={project.context.style_analysis}
                colorAnalysisSkipped={colorSkipped}
                styleAnalysisSkipped={styleSkipped}
                onGenerate={() => generateInspirationRecs.mutate(project.project_id)}
                canGenerate={canGenerateInspirationRecs}
                isGenerating={generateInspirationRecs.isPending}
                errorMessage={
                  generateInspirationRecs.isError
                    ? generateInspirationRecs.error?.message ||
                      "Failed to generate inspiration recommendations"
                    : undefined
                }
              />
            )}
          </section>

          <section id="step-products">
            {(hasReachedStatus("INSPIRATION_RECOMMENDATIONS_READY", project.status) ||
              hasInspirationContext) && (
              <ProductRecommendations
                projectId={project.project_id}
                recommendations={project.context.product_recommendations || []}
                spaceType={project.context.space_type || "unknown"}
                selectedRecommendations={selectedRecommendations}
              />
            )}

            {(project.status === "INSPIRATION_REDESIGN_COMPLETE" ||
              hasReachedStatus("PRODUCT_SEARCH_COMPLETE", project.status)) && (
              <ProductSearchResults
                projectId={project.project_id}
                selectedRecommendation={primaryRecommendation}
                products={project.context.product_search_results || []}
              />
            )}
          </section>

          <section id="step-visualize">
            {hasReachedStatus("PRODUCT_RECOMMENDATION_SELECTED", project.status) && (
              <InspirationRedesignDisplay
                projectId={project.project_id}
                generatedImageBase64={project.context.inspiration_generated_image_base64}
                inspirationPrompt={project.context.inspiration_generation_prompt}
                hasRecommendations={
                  selectedRecommendations.length > 0 ||
                  (project.context.inspiration_recommendations || []).length > 0
                }
                selectedTrendingProducts={project.context.selected_trending_products || []}
                modelUsed={project.context.inspiration_model_used}
              />
            )}

            {hasReachedStatus("PRODUCT_SELECTED", project.status) &&
              selectedProducts.length > 0 && (
                <GeneratedImageDisplay
                  projectId={project.project_id}
                  selectedProduct={selectedProducts[0]}
                  generatedImageBase64={
                    project.status === "IMAGE_GENERATED"
                      ? project.context.generated_image_base64
                      : undefined
                  }
                  generationPrompt={project.context.generation_prompt}
                  colorScheme={project.context.color_scheme}
                  designStyle={project.context.design_style}
                  modelUsed={project.context.generation_model_used}
                />
              )}

            {project.status === "IMAGE_GENERATED" && (
              <div className="mt-8 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 p-6 shadow-lg dark:from-purple-900/20 dark:to-pink-900/20">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900/20">
                    <svg
                      className="h-8 w-8 text-purple-600 dark:text-purple-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <h2 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
                    Project Complete! 🎨✨
                  </h2>
                  <p className="mb-6 text-gray-600 dark:text-gray-300">
                    Your AI-generated product visualization is ready! You&apos;ve
                    successfully completed the entire design workflow.
                  </p>
                  <Link href="/projects">
                    <button className="rounded-lg bg-purple-600 px-6 py-3 font-medium text-white transition-colors hover:bg-purple-700">
                      View All Projects
                    </button>
                  </Link>
                </div>
              </div>
            )}

            {project.status === "PRODUCT_SEARCH_COMPLETE" && (
              <div className="mt-8 rounded-lg bg-gradient-to-r from-green-50 to-blue-50 p-6 shadow-lg dark:from-green-900/20 dark:to-blue-900/20">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/20">
                    <svg
                      className="h-8 w-8 text-green-600 dark:text-green-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <h2 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
                    Project Complete! 🎉
                  </h2>
                  <p className="mb-4 text-gray-600 dark:text-gray-300">
                    Your {project.context.space_type} design project is complete
                    with product recommendations. You now have specific products
                    to transform your space based on AI analysis of your style
                    preferences.
                  </p>
                  <div className="flex items-center justify-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <svg
                        className="h-4 w-4 text-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span>Style Analysis Complete</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <svg
                        className="h-4 w-4 text-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span>Products Found</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <svg
                        className="h-4 w-4 text-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span>Ready to Shop</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </main>
      </div>
      <NextActionBar nextStep={nextStep} />
    </div>
  );
}
