interface ProjectContextProps {
  context: Record<string, any>;
}

export function ProjectContext({ context }: ProjectContextProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Project Context
      </h2>
      <div className="space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-300">
            Context Items:
          </span>
          <span className="font-medium">
            {Object.keys(context).length} items
          </span>
        </div>
        {Object.keys(context).length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>No context data yet</p>
            <p className="text-sm mt-1">
              Context will be added as you interact with the project
            </p>
          </div>
        ) : (
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <pre className="text-xs overflow-auto">
              {JSON.stringify(context, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
