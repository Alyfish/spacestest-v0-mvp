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
          <span className="font-medium">{status}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-300">Created:</span>
          <span>{createdAt}</span>
        </div>
      </div>
    </div>
  );
}
