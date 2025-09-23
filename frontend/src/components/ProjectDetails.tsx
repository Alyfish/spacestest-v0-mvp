interface ProjectDetailsProps {
  projectId: string;
  status: string;
  createdAt: string;
}

export function ProjectDetails({
  projectId,
  status,
  createdAt,
}: ProjectDetailsProps) {
  const getStatusDisplay = (status: string) => {
    const statusMap: Record<string, { text: string; color: string }> = {
      NEW: { text: "New Project", color: "text-gray-600" },
      BASE_IMAGE_UPLOADED: { text: "Image Uploaded", color: "text-blue-600" },
      SPACE_TYPE_SELECTED: {
        text: "Space Type Selected",
        color: "text-green-600",
      },
      MARKER_RECOMMENDATIONS_READY: {
        text: "Markers & Recommendations Ready",
        color: "text-purple-600",
      },
      INSPIRATION_IMAGES_UPLOADED: {
        text: "Inspiration Images Uploaded",
        color: "text-pink-600",
      },
      INSPIRATION_RECOMMENDATIONS_READY: {
        text: "Complete with Inspiration",
        color: "text-indigo-600",
      },
      PRODUCT_RECOMMENDATIONS_READY: {
        text: "Product Recommendations Ready",
        color: "text-purple-600",
      },
      PRODUCT_RECOMMENDATION_SELECTED: {
        text: "Product Recommendation Selected",
        color: "text-pink-600",
      },
      PRODUCT_SEARCH_COMPLETE: {
        text: "Product Search Complete",
        color: "text-green-600",
      },
      PRODUCT_SELECTED: {
        text: "Product Selected for Generation",
        color: "text-purple-600",
      },
      IMAGE_GENERATED: {
        text: "AI Image Generated",
        color: "text-purple-800",
      },
    };

    return statusMap[status] || { text: status, color: "text-gray-600" };
  };

  const statusDisplay = getStatusDisplay(status);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Project Details
      </h2>
      <div className="space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-300">Project ID:</span>
          <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
            {projectId}
          </code>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-300">Status:</span>
          <span className={`font-medium ${statusDisplay.color}`}>
            {statusDisplay.text}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-300">Created:</span>
          <span>{createdAt}</span>
        </div>
      </div>
    </div>
  );
}
