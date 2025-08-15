"use client";

import ProjectsList from "@/components/ProjectsList";
import { useCreateProject, useHealthCheck, useRootEndpoint } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function Home() {
  const healthQuery = useHealthCheck();
  const rootQuery = useRootEndpoint();
  const createProjectMutation = useCreateProject();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            AI Interior Design Agent
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Intelligent design recommendations for your space
          </p>
        </header>

        <main className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Health Check Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                API Health Status
              </h2>
              <div className="space-y-3">
                {healthQuery.isLoading && (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-gray-600 dark:text-gray-300">
                      Checking health...
                    </span>
                  </div>
                )}
                {healthQuery.isError && (
                  <div className="text-red-600 dark:text-red-400">
                    Error:{" "}
                    {healthQuery.error?.message ||
                      "Failed to fetch health status"}
                  </div>
                )}
                {healthQuery.isSuccess && (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          healthQuery.data.status === "healthy"
                            ? "bg-green-500"
                            : "bg-red-500"
                        }`}
                      ></div>
                      <span className="text-gray-900 dark:text-white font-medium">
                        Status: {healthQuery.data.status}
                      </span>
                    </div>
                    <p className="text-gray-600 dark:text-gray-300 text-sm">
                      {healthQuery.data.message}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Root Endpoint Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                API Root Endpoint
              </h2>
              <div className="space-y-3">
                {rootQuery.isLoading && (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-gray-600 dark:text-gray-300">
                      Loading...
                    </span>
                  </div>
                )}
                {rootQuery.isError && (
                  <div className="text-red-600 dark:text-red-400">
                    Error:{" "}
                    {rootQuery.error?.message ||
                      "Failed to fetch root endpoint"}
                  </div>
                )}
                {rootQuery.isSuccess && (
                  <div className="space-y-2">
                    <p className="text-gray-900 dark:text-white">
                      {rootQuery.data.message}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Connection Status */}
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Connection Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-300">
                  Backend URL:
                </span>
                <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
                  http://localhost:8000
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-300">
                  API Prefix:
                </span>
                <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
                  /api
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-300">
                  Frontend URL:
                </span>
                <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
                  http://localhost:3000
                </code>
              </div>
            </div>
          </div>

          {/* Project Management */}
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Create New Project
            </h2>

            <div className="space-y-4">
              {/* Create Project */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => {
                    createProjectMutation.mutate(undefined, {
                      onSuccess: (data) => {
                        router.push(`/projects/${data.project_id}`);
                      },
                    });
                  }}
                  disabled={createProjectMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {createProjectMutation.isPending
                    ? "Creating..."
                    : "Create New Project"}
                </button>

                {createProjectMutation.isSuccess && (
                  <span className="text-green-600 dark:text-green-400 text-sm">
                    Project created: {createProjectMutation.data?.project_id}
                  </span>
                )}

                {createProjectMutation.isError && (
                  <span className="text-red-600 dark:text-red-400 text-sm">
                    Error: {createProjectMutation.error?.message}
                  </span>
                )}
              </div>

              {/* Project Creation Info */}
              <div className="border-t pt-4">
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Click "Create New Project" to start a new AI Interior Design
                  project. You'll be redirected to the project page where you
                  can interact with the AI agent.
                </p>
              </div>
            </div>
          </div>

          {/* Projects List */}
          <div className="mt-8">
            <ProjectsList />
          </div>
        </main>
      </div>
    </div>
  );
}
