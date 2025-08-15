"use client";

import { ImageMarkerInterface } from "@/components/ImageMarkerInterface";
import { ImageUploadSection } from "@/components/ImageUploadSection";
import { LabelledImageDisplay } from "@/components/LabelledImageDisplay";
import { MarkerRecommendations } from "@/components/MarkerRecommendations";
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

          {project.status === "MARKER_RECOMMENDATIONS_READY" && (
            <>
              <LabelledImageDisplay
                projectId={project.project_id}
                markers={project.context.improvement_markers || []}
              />
              <MarkerRecommendations projectId={project.project_id} />
            </>
          )}
        </main>
      </div>
    </div>
  );
}
