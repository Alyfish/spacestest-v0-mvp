"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  apiClient,
  useProcessFurnitureSelection,
  SelectedFurnitureProduct,
  ProcessFurnitureSelectionResponse,
} from "@/lib/api";

interface FurnitureSelection {
  id: string;
  x: number; // percentage (0-1)
  y: number; // percentage (0-1)
  label?: string;
}

interface BedComponentProducts {
  bed_frame: any[];
  bedding: any[];
  throw: any[];
  pillows: any[];
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
    is_bed?: boolean;
    bed_components?: BedComponentProducts;
  }>;
  overall_analysis: string;
  total_items: number;
}

const BED_COMPONENT_LABELS: Record<string, { label: string; emoji: string }> = {
  bed_frame: { label: "Bed Frame", emoji: "🛏️" },
  bedding: { label: "Bedding", emoji: "🛌" },
  throw: { label: "Throws", emoji: "🧶" },
  pillows: { label: "Pillows", emoji: "🛋️" },
};

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

  // Product selection state for "Process Selected" feature
  const [selectedProducts, setSelectedProducts] = useState<Map<string, Set<number>>>(new Map());
  const [processingResults, setProcessingResults] = useState<ProcessFurnitureSelectionResponse | null>(null);
  const [showRetailerCarts, setShowRetailerCarts] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);

  // Process furniture selection mutation
  const processFurniture = useProcessFurnitureSelection();

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
      setPanelError(null);
      setAnalysisResults(data);
      setIsSelecting(false);
      if (data.selections.length > 0) {
        setSelectedTab(data.selections[0].id);
      }
    },
    onError: (error) => {
      console.error("Failed to analyze furniture:", error);
      setPanelError(
        error instanceof Error
          ? error.message
          : "Failed to analyze furniture. Please try again."
      );
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
    setPanelError(null);
  };

  const handleAnalyze = () => {
    if (selections.length === 0) {
      setPanelError("Select at least one furniture item to analyze.");
      return;
    }
    setPanelError(null);
    analyzeFurniture.mutate(selections);
  };

  // Toggle product selection for processing
  const toggleProductSelection = (furnitureId: string, productIdx: number) => {
    setSelectedProducts((prev) => {
      const newMap = new Map(prev);
      const furnitureSet = newMap.get(furnitureId) || new Set();

      if (furnitureSet.has(productIdx)) {
        furnitureSet.delete(productIdx);
      } else {
        furnitureSet.add(productIdx);
      }

      if (furnitureSet.size === 0) {
        newMap.delete(furnitureId);
      } else {
        newMap.set(furnitureId, furnitureSet);
      }

      return newMap;
    });
  };

  // Get total count of selected products
  const getTotalSelectedCount = () => {
    let count = 0;
    selectedProducts.forEach((set) => {
      count += set.size;
    });
    return count;
  };

  // Handle processing selected products
  const handleProcessSelected = () => {
    if (!analysisResults || getTotalSelectedCount() === 0) return;

    const productsToProcess: SelectedFurnitureProduct[] = [];

    analysisResults.selections.forEach((item) => {
      const selectedIndices = selectedProducts.get(item.id);
      if (selectedIndices) {
        selectedIndices.forEach((idx) => {
          const product = item.products[idx];
          if (product) {
            productsToProcess.push({
              url: product.url,
              title: product.title,
              image_url: product.image_url || product.images?.[0],
              store: product.store,
              price_str: product.price_str,
              price: product.price,
              furniture_id: item.id,
            });
          }
        });
      }
    });

    processFurniture.mutate(
      { projectId, selectedProducts: productsToProcess },
      {
        onSuccess: (data) => {
          setPanelError(null);
          setProcessingResults(data);
          setShowRetailerCarts(true);
        },
        onError: (error) => {
          console.error("Failed to process furniture selection:", error);
          setPanelError(
            error instanceof Error
              ? error.message
              : "Failed to process selection. Please try again."
          );
        },
      }
    );
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
                src={imageBase64?.startsWith('http') ? imageBase64 : `data:image/png;base64,${imageBase64}`}
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

            {panelError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
                {panelError}
              </div>
            )}
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
                    <li>3. Click &quot;Analyze&quot; to get AI recommendations</li>
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
                                  Search: &quot;{item.search_query}&quot;
                                </p>
                              </div>
                            </div>

                            {/* Bed Components - Show when bed is detected */}
                            {item.is_bed && item.bed_components && (
                              <div className="mt-4">
                                <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                                  🛏️ Bed Components
                                  <span className="text-xs font-normal text-gray-500">
                                    (4 products each)
                                  </span>
                                </h4>
                                <div className="space-y-4">
                                  {Object.entries(item.bed_components).map(([componentKey, products]) => {
                                    const config = BED_COMPONENT_LABELS[componentKey] || { label: componentKey, emoji: "📦" };
                                    return (
                                      <div key={componentKey} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                                        <h5 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                                          <span>{config.emoji}</span>
                                          {config.label}
                                          <span className="text-xs text-gray-500">
                                            ({(products as any[]).length} products)
                                          </span>
                                        </h5>
                                        {(products as any[]).length === 0 ? (
                                          <p className="text-gray-500 text-sm">No products found</p>
                                        ) : (
                                          <div className="grid grid-cols-2 gap-2">
                                            {(products as any[]).slice(0, 4).map((product, idx) => (
                                              <a
                                                key={idx}
                                                href={product.url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="block p-2 bg-white dark:bg-gray-700 rounded-lg hover:shadow-md transition"
                                              >
                                                {(product.image_url || product.images?.[0] || product.thumbnail) && (
                                                  <img
                                                    src={product.image_url || product.images?.[0] || product.thumbnail}
                                                    alt={product.title}
                                                    className="w-full h-20 object-cover rounded mb-2"
                                                    onError={(e) => {
                                                      const t = e.target as HTMLImageElement;
                                                      const imgSrc = product.image_url || product.images?.[0] || product.thumbnail;
                                                      if (imgSrc) {
                                                        t.src = `https://images.weserv.nl/?url=${encodeURIComponent(
                                                          imgSrc
                                                        )}&w=100&h=80&fit=cover`;
                                                      }
                                                    }}
                                                  />
                                                )}
                                                <p className="text-xs font-medium text-gray-900 dark:text-white line-clamp-2">
                                                  {product.title}
                                                </p>
                                                <div className="flex items-center justify-between mt-1">
                                                  {product.price_str && (
                                                    <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                                                      {product.price_str}
                                                    </p>
                                                  )}
                                                  {product.store && (
                                                    <p className="text-xs text-gray-500 truncate max-w-[60px]">
                                                      {product.store}
                                                    </p>
                                                  )}
                                                </div>
                                              </a>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Product Recommendations (non-bed or general products) */}
                            {!item.is_bed && (
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
                                    {item.products.slice(0, 5).map((product, idx) => {
                                      const isSelected = selectedProducts.get(item.id)?.has(idx) || false;
                                      return (
                                      <div
                                        key={idx}
                                        className={`p-3 rounded-lg transition border-2 ${
                                          isSelected
                                            ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                                            : "border-transparent bg-gray-50 dark:bg-gray-800 hover:shadow-md"
                                        }`}
                                      >
                                        <div className="flex gap-3">
                                          {/* Selection Checkbox */}
                                          <div className="flex items-center">
                                            <input
                                              type="checkbox"
                                              checked={isSelected}
                                              onChange={() => toggleProductSelection(item.id, idx)}
                                              className="w-5 h-5 accent-green-600 cursor-pointer"
                                            />
                                          </div>
                                          {(product.image_url || product.images?.[0] || product.thumbnail) && (
                                            <img
                                              src={product.image_url || product.images?.[0] || product.thumbnail}
                                              alt={product.title}
                                              className="w-16 h-16 object-cover rounded"
                                              onError={(e) => {
                                                const t = e.target as HTMLImageElement;
                                                const imgUrl = product.image_url || product.images?.[0] || product.thumbnail;
                                                if (imgUrl) {
                                                  t.src = `https://images.weserv.nl/?url=${encodeURIComponent(
                                                    imgUrl
                                                  )}&w=64&h=64&fit=cover`;
                                                }
                                              }}
                                            />
                                          )}
                                          <div className="flex-1">
                                            <div className="flex items-start justify-between">
                                              <a
                                                href={product.url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 hover:text-blue-600 dark:hover:text-blue-400"
                                              >
                                                {product.title}
                                              </a>
                                              {/* Show similarity score if available */}
                                              {product.similarity_score !== undefined && (
                                                <span className={`text-xs px-1.5 py-0.5 rounded ml-1 flex-shrink-0 ${
                                                  product.similarity_score >= 0.85
                                                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                                                    : product.similarity_score >= 0.70
                                                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                                                    : "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300"
                                                }`}>
                                                  {Math.round(product.similarity_score * 100)}%
                                                </span>
                                              )}
                                            </div>
                                            <div className="flex items-center gap-2 mt-1">
                                              {product.price_str && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                                  {product.price_str}
                                                </p>
                                              )}
                                              {/* Show store trust badge for high-trust stores */}
                                              {product.store_trust !== undefined && product.store_trust >= 0.85 && (
                                                <span className="text-xs text-emerald-600 dark:text-emerald-400">
                                                  ✓
                                                </span>
                                              )}
                                            </div>
                                            {product.store && (
                                              <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                                                {product.store}
                                              </p>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    );
                                    })}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  )}

                  {/* Process Selected Button */}
                  <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h4 className="font-semibold text-gray-900 dark:text-white">
                            Process Selected Products
                          </h4>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {getTotalSelectedCount()} product{getTotalSelectedCount() !== 1 ? "s" : ""} selected
                          </p>
                        </div>
                        <button
                          onClick={handleProcessSelected}
                          disabled={getTotalSelectedCount() === 0 || processFurniture.isPending}
                          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                        >
                          {processFurniture.isPending ? (
                            <span className="flex items-center gap-2">
                              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                              Processing...
                            </span>
                          ) : (
                            `Process ${getTotalSelectedCount()} Selected`
                          )}
                        </button>
                      </div>

                      {/* Retailer Carts Display */}
                      {showRetailerCarts && processingResults && (
                        <div className="mt-4 space-y-4">
                          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                            <p className="text-sm text-green-700 dark:text-green-300">
                              ✓ {processingResults.message}
                            </p>
                          </div>

                          {processingResults.retailer_carts.map((cart) => (
                            <div
                              key={cart.retailer}
                              className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div>
                                  <h5 className="font-semibold text-gray-900 dark:text-white">
                                    {cart.retailer_display_name}
                                  </h5>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {cart.product_count} item{cart.product_count !== 1 ? "s" : ""}
                                  </p>
                                </div>
                                {cart.cart_url && (
                                  <a
                                    href={cart.cart_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition"
                                  >
                                    Add All to Cart
                                  </a>
                                )}
                              </div>

                              {/* Individual product affiliate links */}
                              <div className="space-y-2">
                                {cart.products.map((product, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-center justify-between text-sm"
                                  >
                                    <span className="text-gray-600 dark:text-gray-400 truncate max-w-[70%]">
                                      {product.product_id || "Product"}
                                    </span>
                                    <a
                                      href={product.affiliate_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-blue-600 dark:text-blue-400 hover:underline"
                                    >
                                      View →
                                    </a>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {processFurniture.isError && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                          <p className="text-sm text-red-600 dark:text-red-400">
                            Failed to process selection. Please try again.
                          </p>
                        </div>
                      )}
                    </div>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
