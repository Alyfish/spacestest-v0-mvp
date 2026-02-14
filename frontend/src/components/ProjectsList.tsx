"use client";

import { useDeleteProject, useGetAllProjects } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";

export default function ProjectsList() {
  const projectsQuery = useGetAllProjects();
  const deleteProjectMutation = useDeleteProject();
  const router = useRouter();

  const getStatusDisplay = (status: string) => {
    const statusMap: Record<string, { label: string; color: string }> = {
      NEW: { label: "New", color: "bg-slate-100 text-slate-700" },
      BASE_IMAGE_UPLOADED: {
        label: "Image uploaded",
        color: "bg-sky-100 text-sky-700",
      },
      SPACE_TYPE_SELECTED: {
        label: "Space selected",
        color: "bg-amber-100 text-amber-700",
      },
      IMPROVEMENT_MARKERS_ADDED: {
        label: "Markers added",
        color: "bg-emerald-100 text-emerald-700",
      },
    };
    return (
      statusMap[status] || { label: status, color: "bg-slate-100 text-slate-600" }
    );
  };

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`);
  };

  const handleDeleteProject = (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    if (
      window.confirm(
        "Are you sure you want to delete this project? This action cannot be undone."
      )
    ) {
      deleteProjectMutation.mutate(projectId);
    }
  };

  if (projectsQuery.isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Your projects
        </h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-rose-500"></div>
          <span className="ml-3 text-gray-500 dark:text-gray-400 text-sm">
            Loading projects...
          </span>
        </div>
      </div>
    );
  }

  if (projectsQuery.isError) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Your projects
        </h2>
        <div className="text-red-600 dark:text-red-400 text-sm">
          Error loading projects: {projectsQuery.error?.message}
        </div>
      </div>
    );
  }

  const projects = projectsQuery.data?.projects || {};
  const projectIds = Object.keys(projects);

  if (projectIds.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Your projects
        </h2>
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            No projects found. Create your first project to get started!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Your projects ({projectsQuery.data?.total_count || 0})
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
              className="cursor-pointer rounded-xl border border-slate-100 p-4 transition-colors hover:bg-slate-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                      Project {projectId.slice(0, 8)}...
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      {statusInfo.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Created {timeAgo}
                  </p>
                  {project.context.space_type && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {project.context.space_type}
                    </p>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={(e) => handleDeleteProject(e, projectId)}
                    className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-red-50 hover:text-red-500 dark:text-gray-400 dark:hover:bg-red-900/20"
                    aria-label={`Delete project ${projectId.slice(0, 8)}`}
                    title="Delete project"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                  <div className="text-gray-400 dark:text-gray-500">
                    <svg
                      className="w-4 h-4"
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
