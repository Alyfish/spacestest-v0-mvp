"use client";

import { useHealthCheck, useRootEndpoint } from "@/lib/api";

export default function Home() {
  const healthQuery = useHealthCheck();
  const rootQuery = useRootEndpoint();

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
        </main>
      </div>
    </div>
  );
}
