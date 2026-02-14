import { useSelectSpaceType } from "@/lib/api";
import { useState } from "react";

interface SpaceTypeSelectionProps {
  projectId: string;
}

export function SpaceTypeSelection({ projectId }: SpaceTypeSelectionProps) {
  const selectSpaceTypeMutation = useSelectSpaceType();
  const [selectedSpaceType, setSelectedSpaceType] = useState<string>("");
  const [customSpaceType, setCustomSpaceType] = useState<string>("");

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Select Space Type
      </h2>

      <div className="space-y-4">
        <p className="text-gray-600 dark:text-gray-300">
          Choose the type of space you're designing to get personalized
          recommendations.
        </p>

        <div className="space-y-3">
          {["living room", "bedroom", "office"].map((spaceType) => (
            <label
              key={spaceType}
              className="flex items-center space-x-3 cursor-pointer"
            >
              <input
                type="radio"
                name="spaceType"
                value={spaceType}
                checked={selectedSpaceType === spaceType}
                onChange={(e) => {
                  setSelectedSpaceType(e.target.value);
                  setCustomSpaceType(""); // Clear custom input when selecting predefined option
                }}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-gray-900 dark:text-white capitalize">
                {spaceType}
              </span>
            </label>
          ))}

          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="radio"
              name="spaceType"
              value="custom"
              checked={selectedSpaceType === "custom"}
              onChange={(e) => setSelectedSpaceType(e.target.value)}
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
            />
            <span className="text-gray-900 dark:text-white">Custom</span>
          </label>
        </div>

        {selectedSpaceType === "custom" && (
          <div className="mt-4">
            <input
              type="text"
              placeholder="Enter custom space type..."
              value={customSpaceType}
              onChange={(e) => setCustomSpaceType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
          </div>
        )}

        <div className="flex items-center space-x-4">
          <button
            onClick={() => {
              const spaceType =
                selectedSpaceType === "custom"
                  ? customSpaceType
                  : selectedSpaceType;
              if (spaceType) {
                selectSpaceTypeMutation.mutate({
                  projectId,
                  spaceType,
                });
              }
            }}
            disabled={
              selectSpaceTypeMutation.isPending ||
              !selectedSpaceType ||
              (selectedSpaceType === "custom" && !customSpaceType.trim())
            }
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {selectSpaceTypeMutation.isPending
              ? "Saving..."
              : "Save Space Type"}
          </button>

          {selectSpaceTypeMutation.isSuccess && (
            <span className="text-green-600 dark:text-green-400 text-sm">
              Space type saved successfully!
            </span>
          )}

          {selectSpaceTypeMutation.isError && (
            <span className="text-red-600 dark:text-red-400 text-sm">
              Error: {selectSpaceTypeMutation.error?.message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
