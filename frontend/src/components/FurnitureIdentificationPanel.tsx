"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

interface FurnitureSelection {
  id: string;
  x: number; // percentage (0-1)
  y: number; // percentage (0-1)
  label?: string;
}

interface FurnitureAnalysisResult {
  selections: Array<{
    id: string;
    furniture_type: string;
    confidence: number;
    style: string;
    material: string;
    color: string;
    search_query: string;
    products: any[];
  }>;
  overall_analysis: string;
  total_items: number;
}

interface FurnitureIdentificationPanelProps {
  projectId: string;
  imageBase64: string;
  imageType: "product" | "inspiration";
  onClose?: () => void;
}

export function FurnitureIdentificationPanel({
  projectId,
  imageBase64,
  imageType,
  onClose,
}: FurnitureIdentificationPanelProps) {
  const [selections, setSelections] = useState<FurnitureSelection[]>([]);
  const [isSelecting, setIsSelecting] = useState(true);
  const [analysisResults, setAnalysisResults] = useState<FurnitureAnalysisResult | null>(null);
  const [selectedTab, setSelectedTab] = useState<string | null>(null);

  // Mutation for batch furniture analysis
  const analyzeFurniture = useMutation({
    mutationFn: async (selections: FurnitureSelection[]) => {
      const response = await apiClient.post<FurnitureAnalysisResult>(
        `/projects/${projectId}/analyze-furniture-batch`,
        {
          selections,
          image_type: imageType,
        }
      );
      return response;
    },
    onSuccess: (data) => {
      setAnalysisResults(data);
      setIsSelecting(false);
      if (data.selections.length > 0) {
        setSelectedTab(data.selections[0].id);
      }
    },
    onError: (error) => {
      console.error("Failed to analyze furniture:", error);
      alert("Failed to analyze furniture. Please try again.");
    },
  });

  const handleImageClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isSelecting) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    const newSelection: FurnitureSelection = {
      id: `item-${selections.length + 1}`,
      x,
      y,
      label: `Item ${selections.length + 1}`,
    };

    setSelections([...selections, newSelection]);
  };

  const removeSelection = (id: string) => {
    setSelections(selections.filter((s) => s.id !== id));
  };

  const clearSelections = () => {
    setSelections([]);
    setAnalysisResults(null);
    setIsSelecting(true);
  };

  const handleAnalyze = () => {
    if (selections.length === 0) {
      alert("Please select at least one furniture item to analyze.");
      return;
    }
    analyzeFurniture.mutate(selections);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                🔍 AI Furniture Identification
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {isSelecting
                  ? `Click on furniture items to mark them for analysis (${selections.length} selected)`
                  : `Analyzing ${selections.length} furniture items`}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
            >
              <svg
                className="w-6 h-6 text-gray-600 dark:text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Image with selections */}
          <div className="flex-1 p-6 overflow-auto">
            <div
              className="relative inline-block cursor-crosshair"
              onClick={handleImageClick}
            >
              <img
                src={`data:image/png;base64,${imageBase64}`}
                alt="Room"
                className="max-w-full h-auto rounded-lg"
                draggable={false}
              />
              
              {/* Selection markers */}
              {selections.map((selection) => (
                <div
                  key={selection.id}
                  className="absolute transform -translate-x-1/2 -translate-y-1/2"
                  style={{
                    left: `${selection.x * 100}%`,
                    top: `${selection.y * 100}%`,
                  }}
                >
                  <div className="relative">
                    {/* Pin */}
                    <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-lg">
                      {selection.id.split("-")[1]}
                    </div>
                    {/* Label */}
                    <div className="absolute top-10 left-1/2 transform -translate-x-1/2 bg-black/75 text-white px-2 py-1 rounded text-xs whitespace-nowrap">
                      {selection.label}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="mt-6 flex gap-3">
              {isSelecting && (
                <>
                  <button
                    onClick={handleAnalyze}
                    disabled={selections.length === 0 || analyzeFurniture.isPending}
                    className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                  >
                    {analyzeFurniture.isPending ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                        Analyzing with AI...
                      </span>
                    ) : (
                      `Analyze ${selections.length} Item${selections.length !== 1 ? "s" : ""}`
                    )}
                  </button>
                  <button
                    onClick={clearSelections}
                    disabled={selections.length === 0}
                    className="px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
                  >
                    Clear All
                  </button>
                </>
              )}
              {!isSelecting && (
                <button
                  onClick={clearSelections}
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Start New Analysis
                </button>
              )}
            </div>
          </div>

          {/* Right: Selection list or results */}
          <div className="w-96 border-l border-gray-200 dark:border-gray-700 p-6 overflow-auto">
            {isSelecting ? (
              /* Selection List */
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  Selected Items
                </h3>
                {selections.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    Click on furniture items in the image to mark them for analysis
                  </p>
                ) : (
                  <div className="space-y-2">
                    {selections.map((selection) => (
                      <div
                        key={selection.id}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold text-xs">
                            {selection.id.split("-")[1]}
                          </div>
                          <span className="text-gray-900 dark:text-white">
                            {selection.label}
                          </span>
                        </div>
                        <button
                          onClick={() => removeSelection(selection.id)}
                          className="text-red-500 hover:text-red-600"
                        >
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">
                    How to use:
                  </h4>
                  <ol className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                    <li>1. Click on each furniture item you want to identify</li>
                    <li>2. Review your selections in this panel</li>
                    <li>3. Click "Analyze" to get AI recommendations</li>
                    <li>4. View detailed analysis and product matches</li>
                  </ol>
                </div>
              </div>
            ) : (
              /* Analysis Results */
              analysisResults && (
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                    Analysis Results
                  </h3>

                  {/* Tabs for each item */}
                  <div className="flex gap-1 mb-4 overflow-x-auto">
                    {analysisResults.selections.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setSelectedTab(item.id)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
                          selectedTab === item.id
                            ? "bg-purple-600 text-white"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        {item.id.replace("-", " ")}
                      </button>
                    ))}
                  </div>

                  {/* Selected item details */}
                  {selectedTab && (
                    <div>
                      {analysisResults.selections
                        .filter((item) => item.id === selectedTab)
                        .map((item) => (
                          <div key={item.id} className="space-y-4">
                            {/* CLIP Analysis */}
                            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                              <h4 className="font-semibold text-purple-900 dark:text-purple-200 mb-3">
                                🤖 AI Analysis
                              </h4>
                              <div className="grid grid-cols-2 gap-3 text-sm">
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">Type:</span>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {item.furniture_type} ({Math.round(item.confidence * 100)}%)
                                  </p>
                                </div>
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">Style:</span>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {item.style}
                                  </p>
                                </div>
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">Material:</span>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {item.material}
                                  </p>
                                </div>
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">Color:</span>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {item.color}
                                  </p>
                                </div>
                              </div>
                              <div className="mt-3 pt-3 border-t border-purple-200 dark:border-purple-800">
                                <p className="text-sm text-purple-800 dark:text-purple-300">
                                  Search: "{item.search_query}"
                                </p>
                              </div>
                            </div>

                            {/* Product Recommendations */}
                            <div>
                              <h4 className="font-semibold text-gray-900 dark:text-white mb-3">
                                📦 Product Matches
                              </h4>
                              {item.products.length === 0 ? (
                                <p className="text-gray-500 dark:text-gray-400 text-sm">
                                  No products found for this item
                                </p>
                              ) : (
                                <div className="space-y-2 max-h-96 overflow-y-auto">
                                  {item.products.slice(0, 5).map((product, idx) => (
                                    <a
                                      key={idx}
                                      href={product.url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="block p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition"
                                    >
                                      <div className="flex gap-3">
                                        {product.images?.[0] && (
                                          <img
                                            src={product.images[0]}
                                            alt={product.title}
                                            className="w-16 h-16 object-cover rounded"
                                            onError={(e) => {
                                              const t = e.target as HTMLImageElement;
                                              t.src = `https://images.weserv.nl/?url=${encodeURIComponent(
                                                product.images[0]
                                              )}&w=64&h=64&fit=cover`;
                                            }}
                                          />
                                        )}
                                        <div className="flex-1">
                                          <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
                                            {product.title}
                                          </p>
                                          {product.price_str && (
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                              {product.price_str}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    </a>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
