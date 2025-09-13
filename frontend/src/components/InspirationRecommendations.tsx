"use client";

import { useGenerateInspirationRecommendations } from "@/lib/api";

interface InspirationRecommendationsProps {
  projectId: string;
  recommendations: string[];
  spaceType: string;
}

export function InspirationRecommendations({
  projectId,
  recommendations,
  spaceType,
}: InspirationRecommendationsProps) {
  const generateMutation = useGenerateInspirationRecommendations();

  const handleGenerateRecommendations = () => {
    generateMutation.mutate(projectId);
  };

  if (recommendations.length > 0) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Inspiration-Based Recommendations
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            AI-generated recommendations based on your inspiration images for
            your {spaceType}
          </p>
        </div>

        {/* Recommendations List */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Design Recommendations:
          </h3>
          <ul className="space-y-3">
            {recommendations.map((recommendation, index) => (
              <li
                key={index}
                className="flex items-start space-x-3 p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg border border-purple-200 dark:border-purple-800"
              >
                <div className="w-6 h-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 mt-0.5">
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
        <div className="mt-6 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <svg
              className="w-5 h-5 text-purple-600 dark:text-purple-400"
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
            <span className="text-purple-800 dark:text-purple-200 font-medium">
              Inspiration recommendations generated successfully!
            </span>
          </div>
          <p className="text-purple-700 dark:text-purple-300 text-sm mt-1">
            These recommendations are tailored to your inspiration images and
            space type.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/20 dark:to-pink-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
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
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Generate Inspiration Recommendations
        </h3>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Upload inspiration images above, then generate AI recommendations
          based on your design inspiration.
        </p>
        <button
          onClick={handleGenerateRecommendations}
          disabled={generateMutation.isPending}
          className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {generateMutation.isPending
            ? "Generating..."
            : "Generate Recommendations"}
        </button>

        {generateMutation.isError && (
          <div className="mt-4 text-red-600 dark:text-red-400 text-sm">
            Error: {generateMutation.error?.message}
          </div>
        )}
      </div>
    </div>
  );
}
