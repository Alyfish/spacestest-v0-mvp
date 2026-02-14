"use client";

import { useGetMarkerRecommendations } from "@/lib/api";

interface MarkerRecommendationsProps {
  projectId: string;
  enabled: boolean;
}

export function MarkerRecommendations({
  projectId,
  enabled,
}: MarkerRecommendationsProps) {
  const recommendationsQuery = useGetMarkerRecommendations(
    projectId,
    enabled
  );

  if (recommendationsQuery.isLoading) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
          <span className="text-gray-600 dark:text-gray-300">
            Generating AI recommendations...
          </span>
        </div>
      </div>
    );
  }

  if (recommendationsQuery.isError) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-600 dark:text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Unable to Load Recommendations
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            {recommendationsQuery.error?.message ||
              "There was an error loading the AI recommendations."}
          </p>
        </div>
      </div>
    );
  }

  if (!recommendationsQuery.data) {
    return null;
  }

  const { recommendations, space_type } = recommendationsQuery.data;

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          AI Design Recommendations
        </h2>
        <p className="text-gray-600 dark:text-gray-300">
          Personalized recommendations for your {space_type} based on your
          improvement markers
        </p>
      </div>

      {/* Recommendations List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Specific Recommendations:
        </h3>
        <ul className="space-y-3">
          {recommendations.map((recommendation, index) => (
            <li
              key={index}
              className="flex items-start space-x-3 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
            >
              <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 mt-0.5">
                {index + 1}
              </div>
              <span className="text-gray-700 dark:text-gray-300">
                {recommendation}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Success Message */}
      <div className="mt-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-green-600 dark:text-green-400"
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
          <span className="text-green-800 dark:text-green-200 font-medium">
            AI recommendations generated successfully!
          </span>
        </div>
        <p className="text-green-700 dark:text-green-300 text-sm mt-1">
          These recommendations are tailored to your specific space and
          improvement goals.
        </p>
      </div>
    </div>
  );
}
