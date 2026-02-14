interface SpaceTypeDisplayProps {
  spaceType: string;
}

export function SpaceTypeDisplay({ spaceType }: SpaceTypeDisplayProps) {
  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Space Type Selected
      </h2>

      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="text-green-600 dark:text-green-400 font-medium">
            Space type: {spaceType}
          </span>
        </div>

        <p className="text-gray-600 dark:text-gray-300">
          Your space has been identified as a <strong>{spaceType}</strong>. The
          AI agent is ready to provide personalized design recommendations.
        </p>
      </div>
    </div>
  );
}
