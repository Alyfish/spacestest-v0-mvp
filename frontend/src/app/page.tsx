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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-gray-900 dark:to-gray-800">
      {/* Sticky Top Bar */}
      <header className="sticky top-0 z-50 h-[60px] bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-slate-200 dark:border-gray-700">
        <div className="container mx-auto px-5 h-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-extrabold text-gray-900 dark:text-white tracking-tight">
              Spaces<span className="text-rose-500">.</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="/affiliate-cart"
              className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              Cart
            </a>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-rose-400 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
              U
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-5 py-8">
        {/* Section Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            Design your space
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            AI-powered interior design recommendations
          </p>
        </div>

        <main className="max-w-4xl">
          <div className="grid md:grid-cols-2 gap-5">
            {/* Health Check Card */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-md transition-shadow p-6 border border-slate-100 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                API health status
              </h2>
              <div className="space-y-3">
                {healthQuery.isLoading && (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-rose-500"></div>
                    <span className="text-gray-500 dark:text-gray-400 text-sm">
                      Checking health...
                    </span>
                  </div>
                )}
                {healthQuery.isError && (
                  <div className="text-red-600 dark:text-red-400 text-sm">
                    Error:{" "}
                    {healthQuery.error?.message ||
                      "Failed to fetch health status"}
                  </div>
                )}
                {healthQuery.isSuccess && (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          healthQuery.data.status === "healthy"
                            ? "bg-emerald-500"
                            : "bg-red-500"
                        }`}
                      ></div>
                      <span className="text-gray-900 dark:text-white font-medium text-sm">
                        Status: {healthQuery.data.status}
                      </span>
                    </div>
                    <p className="text-gray-500 dark:text-gray-400 text-sm">
                      {healthQuery.data.message}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Root Endpoint Card */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-md transition-shadow p-6 border border-slate-100 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                API root endpoint
              </h2>
              <div className="space-y-3">
                {rootQuery.isLoading && (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-rose-500"></div>
                    <span className="text-gray-500 dark:text-gray-400 text-sm">
                      Loading...
                    </span>
                  </div>
                )}
                {rootQuery.isError && (
                  <div className="text-red-600 dark:text-red-400 text-sm">
                    Error:{" "}
                    {rootQuery.error?.message ||
                      "Failed to fetch root endpoint"}
                  </div>
                )}
                {rootQuery.isSuccess && (
                  <div className="space-y-2">
                    <p className="text-gray-900 dark:text-white text-sm">
                      {rootQuery.data.message}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Connection Status */}
          <div className="mt-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Connection status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-500 dark:text-gray-400">
                  Backend URL
                </span>
                <code className="bg-slate-100 dark:bg-gray-700 px-2 py-1 rounded text-xs font-mono">
                  localhost:8000
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500 dark:text-gray-400">
                  API prefix
                </span>
                <code className="bg-slate-100 dark:bg-gray-700 px-2 py-1 rounded text-xs font-mono">
                  /api
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500 dark:text-gray-400">
                  Frontend URL
                </span>
                <code className="bg-slate-100 dark:bg-gray-700 px-2 py-1 rounded text-xs font-mono">
                  localhost:3000
                </code>
              </div>
            </div>
          </div>

          {/* Project Management */}
          <div className="mt-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6 border border-slate-100 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Create new project
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
                  className="px-5 py-2.5 bg-rose-500 text-white rounded-xl font-medium hover:bg-rose-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {createProjectMutation.isPending
                    ? "Creating..."
                    : "New project"}
                </button>

                {createProjectMutation.isSuccess && (
                  <span className="text-emerald-600 dark:text-emerald-400 text-sm">
                    Created: {createProjectMutation.data?.project_id}
                  </span>
                )}

                {createProjectMutation.isError && (
                  <span className="text-red-600 dark:text-red-400 text-sm">
                    Error: {createProjectMutation.error?.message}
                  </span>
                )}
              </div>

              {/* Project Creation Info */}
              <div className="border-t border-slate-100 dark:border-gray-700 pt-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Click "New project" to start a new AI interior design
                  project. You'll be redirected to the project page.
                </p>
              </div>
            </div>
          </div>

          {/* Projects List */}
          <div className="mt-6">
            <ProjectsList />
          </div>
        </main>
      </div>
    </div>
  );
}
