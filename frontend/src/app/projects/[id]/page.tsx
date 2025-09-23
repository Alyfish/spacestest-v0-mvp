"use client";

import { GeneratedImageDisplay } from "@/components/GeneratedImageDisplay";
import { ImageMarkerInterface } from "@/components/ImageMarkerInterface";
import { ImageUploadSection } from "@/components/ImageUploadSection";
import { InspirationImageUpload } from "@/components/InspirationImageUpload";
import { InspirationRecommendations } from "@/components/InspirationRecommendations";
import { LabelledImageDisplay } from "@/components/LabelledImageDisplay";
import { MarkerRecommendations } from "@/components/MarkerRecommendations";
import { ProductRecommendations } from "@/components/ProductRecommendations";
import { ProductSearchResults } from "@/components/ProductSearchResults";
import { ProjectContext } from "@/components/ProjectContext";
import { ProjectDetails } from "@/components/ProjectDetails";
import { ProjectHeader } from "@/components/ProjectHeader";
import { SpaceTypeDisplay } from "@/components/SpaceTypeDisplay";
import { SpaceTypeSelection } from "@/components/SpaceTypeSelection";
import { useGetProject } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;
  const projectQuery = useGetProject(projectId);

  // Helper function to determine if we've reached or passed a certain status
  const hasReachedStatus = (targetStatus: string, currentStatus: string) => {
    const statusOrder = [
      "NEW",
      "BASE_IMAGE_UPLOADED",
      "SPACE_TYPE_SELECTED",
      "MARKER_RECOMMENDATIONS_READY",
      "INSPIRATION_IMAGES_UPLOADED",
      "INSPIRATION_RECOMMENDATIONS_READY",
      "PRODUCT_RECOMMENDATIONS_READY",
      "PRODUCT_RECOMMENDATION_SELECTED",
      "PRODUCT_SEARCH_COMPLETE",
      "PRODUCT_SELECTED",
      "IMAGE_GENERATED",
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
            The project with ID "{projectId}" could not be found.
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <ProjectHeader projectId={project.project_id} />

        <main className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6">
            <ProjectDetails
              projectId={project.project_id}
              status={project.status}
              createdAt={project.created_at}
            />
            <ProjectContext context={project.context} />
          </div>

          <ImageUploadSection
            projectId={project.project_id}
            status={project.status}
            context={project.context}
          />

          {project.status === "BASE_IMAGE_UPLOADED" && (
            <SpaceTypeSelection projectId={project.project_id} />
          )}

          {project.status === "SPACE_TYPE_SELECTED" &&
            project.context.space_type && (
              <SpaceTypeDisplay spaceType={project.context.space_type} />
            )}

          {project.status === "SPACE_TYPE_SELECTED" && isRoomEmpty && (
            <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-green-600 dark:text-green-400"
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
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Project Setup Complete!
                </h2>
                <p className="text-gray-600 dark:text-gray-300 mb-4">
                  Your {project.context.space_type} space is ready for AI
                  recommendations.
                </p>
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <p className="text-blue-800 dark:text-blue-200 text-sm">
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

          {hasReachedStatus("MARKER_RECOMMENDATIONS_READY", project.status) && (
            <>
              <LabelledImageDisplay
                projectId={project.project_id}
                markers={project.context.improvement_markers || []}
              />
              <MarkerRecommendations projectId={project.project_id} />
            </>
          )}

          {hasReachedStatus("MARKER_RECOMMENDATIONS_READY", project.status) && (
            <InspirationImageUpload
              projectId={project.project_id}
              inspirationImages={project.context.inspiration_images || []}
            />
          )}

          {hasReachedStatus("INSPIRATION_IMAGES_UPLOADED", project.status) && (
            <InspirationRecommendations
              projectId={project.project_id}
              recommendations={
                project.context.inspiration_recommendations || []
              }
              spaceType={project.context.space_type || "unknown"}
            />
          )}

          {/* Product Recommendations Section */}
          {hasReachedStatus(
            "INSPIRATION_RECOMMENDATIONS_READY",
            project.status
          ) && (
            <ProductRecommendations
              projectId={project.project_id}
              recommendations={project.context.product_recommendations || []}
              spaceType={project.context.space_type || "unknown"}
            />
          )}

          {/* Product Search Results Section */}
          {hasReachedStatus(
            "PRODUCT_RECOMMENDATION_SELECTED",
            project.status
          ) && (
            <ProductSearchResults
              projectId={project.project_id}
              selectedRecommendation={
                project.context.selected_product_recommendation || ""
              }
              products={project.context.product_search_results || []}
            />
          )}

          {/* Generated Image Display Section */}
          {hasReachedStatus("PRODUCT_SELECTED", project.status) &&
            project.context.selected_product && (
              <GeneratedImageDisplay
                projectId={project.project_id}
                selectedProduct={project.context.selected_product}
                generatedImageBase64={
                  project.status === "IMAGE_GENERATED"
                    ? project.context.generated_image_base64
                    : undefined
                }
                generationPrompt={project.context.generation_prompt}
              />
            )}

          {/* Project Completion */}
          {project.status === "IMAGE_GENERATED" && (
            <div className="mt-8 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg shadow-lg p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-purple-600 dark:text-purple-400"
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
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  Project Complete! 🎨✨
                </h2>
                <p className="text-gray-600 dark:text-gray-300 mb-6">
                  Your AI-generated product visualization is ready! You've
                  successfully completed the entire design workflow.
                </p>
                <Link href="/projects">
                  <button className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium">
                    View All Projects
                  </button>
                </Link>
              </div>
            </div>
          )}

          {/* Legacy Project Completion */}
          {project.status === "PRODUCT_SEARCH_COMPLETE" && (
            <div className="mt-8 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg shadow-lg p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-green-600 dark:text-green-400"
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
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  Project Complete! 🎉
                </h2>
                <p className="text-gray-600 dark:text-gray-300 mb-4">
                  Your {project.context.space_type} design project is complete
                  with product recommendations. You now have specific products
                  to transform your space based on AI analysis of your style
                  preferences.
                </p>
                <div className="flex items-center justify-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center space-x-1">
                    <svg
                      className="w-4 h-4 text-green-600"
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
                      className="w-4 h-4 text-green-600"
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
                      className="w-4 h-4 text-green-600"
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
        </main>
      </div>
    </div>
  );
}
