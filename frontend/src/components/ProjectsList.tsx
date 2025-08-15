"use client";

import { useGetAllProjects } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";

export default function ProjectsList() {
  const projectsQuery = useGetAllProjects();
  const router = useRouter();

  const getStatusDisplay = (status: string) => {
    const statusMap: Record<string, { label: string; color: string }> = {
      NEW: { label: "New", color: "bg-gray-100 text-gray-800" },
      BASE_IMAGE_UPLOADED: {
        label: "Image Uploaded",
        color: "bg-blue-100 text-blue-800",
      },
      SPACE_TYPE_SELECTED: {
        label: "Space Type Selected",
        color: "bg-yellow-100 text-yellow-800",
      },
      IMPROVEMENT_MARKERS_ADDED: {
        label: "Markers Added",
        color: "bg-green-100 text-green-800",
      },
    };
    return (
      statusMap[status] || { label: status, color: "bg-gray-100 text-gray-800" }
    );
  };

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`);
  };

  if (projectsQuery.isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Your Projects
        </h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-300">
            Loading projects...
          </span>
        </div>
      </div>
    );
  }

  if (projectsQuery.isError) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Your Projects
        </h2>
        <div className="text-red-600 dark:text-red-400">
          Error loading projects: {projectsQuery.error?.message}
        </div>
      </div>
    );
  }

  const projects = projectsQuery.data?.projects || {};
  const projectIds = Object.keys(projects);

  if (projectIds.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Your Projects
        </h2>
        <div className="text-center py-8">
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            No projects found. Create your first project to get started!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Your Projects ({projectsQuery.data?.total_count || 0})
      </h2>
      <div className="space-y-3">
        {projectIds.map((projectId) => {
          const project = projects[projectId];
          const statusInfo = getStatusDisplay(project.status);
          const createdDate = new Date(project.created_at);
          const timeAgo = formatDistanceToNow(createdDate, { addSuffix: true });

          return (
            <div
              key={projectId}
              onClick={() => handleProjectClick(projectId)}
              className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Project {projectId.slice(0, 8)}...
                    </h3>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      {statusInfo.label}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    Created {timeAgo}
                  </p>
                  {project.context.space_type && (
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Space Type: {project.context.space_type}
                    </p>
                  )}
                  {project.context.is_base_image_empty_room !== undefined && (
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Room Status:{" "}
                      {project.context.is_base_image_empty_room
                        ? "Empty"
                        : "Furnished"}
                    </p>
                  )}
                </div>
                <div className="text-gray-400 dark:text-gray-500">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
