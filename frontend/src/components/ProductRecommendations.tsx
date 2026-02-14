"use client";

import {
  useGenerateProductRecommendations,
  useSelectProductRecommendation,
  useSearchRecommendations,
  useSetSelectedTrendingProducts,
  PreSearchedCategory,
  PreSearchedProduct,
  SelectedTrendingProduct,
} from "@/lib/api";
import { useState, useEffect } from "react";

interface ProductRecommendationsProps {
  projectId: string;
  recommendations: string[];
  spaceType: string;
  selectedRecommendations?: string[];
  onTrendingProductsSelected?: (products: SelectedTrendingProduct[]) => void;
}

export function ProductRecommendations({
  projectId,
  recommendations,
  spaceType,
  selectedRecommendations: initialSelected = [],
  onTrendingProductsSelected,
}: ProductRecommendationsProps) {
  const generateMutation = useGenerateProductRecommendations();
  const selectMutation = useSelectProductRecommendation();
  const searchMutation = useSearchRecommendations();
  const saveSelectedTrendingMutation = useSetSelectedTrendingProducts();

  // Local state
  const [localSelected, setLocalSelected] = useState<string[]>(initialSelected);
  const [trendingCategories, setTrendingCategories] = useState<PreSearchedCategory[]>([]);
  const [selectedTrendingProducts, setSelectedTrendingProducts] = useState<SelectedTrendingProduct[]>([]);
  const [activeCategory, setActiveCategory] = useState<number>(0);
  const [showTrendingPanel, setShowTrendingPanel] = useState(false);

  // Sync with props when they change
  useEffect(() => {
    setLocalSelected(initialSelected);
  }, [initialSelected]);

  const handleGenerateRecommendations = () => {
    generateMutation.mutate(projectId);
  };

  const handleToggleRecommendation = (recommendation: string) => {
    const newSelected = localSelected.includes(recommendation)
      ? localSelected.filter((r) => r !== recommendation)
      : [...localSelected, recommendation];
    setLocalSelected(newSelected);

    selectMutation.mutate({
      projectId,
      selectedRecommendation: recommendation,
    });
  };

  const handleFindTrendingProducts = () => {
    if (localSelected.length === 0) return;

    searchMutation.mutate(
      { projectId, recommendations: localSelected },
      {
        onSuccess: (data) => {
          setTrendingCategories(data.categories);
          setShowTrendingPanel(true);
          setActiveCategory(0);
        },
      }
    );
  };

  const handleSelectTrendingProduct = (product: PreSearchedProduct, category: string) => {
    const trendingProduct: SelectedTrendingProduct = {
      category,
      url: product.url,
      title: product.title,
      image_url: product.image_url,
      store: product.store,
      price_str: product.price_str,
    };

    setSelectedTrendingProducts((prev) => {
      // Check if this exact product is already selected
      const existingIndex = prev.findIndex((p) => p.url === product.url);
      if (existingIndex >= 0) {
        // Deselect it
        return prev.filter((p) => p.url !== product.url);
      }

      // Check if we already have a product from this category
      const categoryIndex = prev.findIndex((p) => p.category === category);
      if (categoryIndex >= 0) {
        // Replace the existing category selection
        const newSelection = [...prev];
        newSelection[categoryIndex] = trendingProduct;
        return newSelection;
      }

      // Add new selection
      return [...prev, trendingProduct];
    });
  };

  const isProductSelected = (productUrl: string) => {
    return selectedTrendingProducts.some((p) => p.url === productUrl);
  };

  const getSelectedForCategory = (category: string) => {
    return selectedTrendingProducts.find((p) => p.category === category);
  };

  const handleSaveSelectedTrendingProducts = () => {
    saveSelectedTrendingMutation.mutate(
      { projectId, products: selectedTrendingProducts },
      {
        onSuccess: () => {
          if (onTrendingProductsSelected) {
            onTrendingProductsSelected(selectedTrendingProducts);
          }
        },
      }
    );
  };

  // Show generate button if no recommendations yet
  if (recommendations.length === 0) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Product Recommendations
        </h2>
        <div className="text-center">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-blue-600 dark:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Ready for Product Recommendations
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Get AI-powered product recommendations based on your {spaceType}{" "}
            design project. We&apos;ll analyze your style preferences and suggest
            specific items to transform your space.
          </p>
          <button
            onClick={handleGenerateRecommendations}
            disabled={generateMutation.isPending}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {generateMutation.isPending ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Generating Recommendations...</span>
              </div>
            ) : (
              "Get Product Recommendations"
            )}
          </button>
          {generateMutation.isError && (
            <p className="text-red-600 dark:text-red-400 text-sm mt-2">
              Error:{" "}
              {generateMutation.error?.message ||
                "Failed to generate recommendations"}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Product Recommendations Panel */}
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Product Recommendations
          </h2>
          {localSelected.length > 0 && (
            <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
              {localSelected.length} selected
            </span>
          )}
        </div>
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-300">
            Based on your {spaceType} design project, here are specific
            recommendations to transform your space:
          </p>

          <div className="grid md:grid-cols-2 gap-4">
            {recommendations.map((recommendation, index) => {
              const isSelected = localSelected.includes(recommendation);
              return (
                <div
                  key={index}
                  className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${isSelected
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600"
                    }`}
                  onClick={() => handleToggleRecommendation(recommendation)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center border-2 ${isSelected
                            ? "bg-blue-500 border-blue-500 text-white"
                            : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                          }`}
                      >
                        {isSelected ? (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <span className="text-gray-500 dark:text-gray-400">{index + 1}</span>
                        )}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
                          {recommendation}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Click to {isSelected ? "deselect" : "select"}
                        </p>
                      </div>
                    </div>
                    {selectMutation.isPending && (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {selectMutation.isError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-800 dark:text-red-200 text-sm">
                Error:{" "}
                {selectMutation.error?.message ||
                  "Failed to select recommendation"}
              </p>
            </div>
          )}

          {/* Find Trending Products Button */}
          {localSelected.length > 0 && (
            <div className="pt-4">
              <button
                onClick={handleFindTrendingProducts}
                disabled={searchMutation.isPending}
                className="w-full py-4 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-semibold text-lg hover:from-pink-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
              >
                {searchMutation.isPending ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Finding Trending Products...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center space-x-2">
                    <span>Find Trending Products for {localSelected.length} Recommendation{localSelected.length !== 1 ? "s" : ""}</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </div>
                )}
              </button>
            </div>
          )}

          {searchMutation.isError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-800 dark:text-red-200 text-sm">
                Error: {searchMutation.error?.message || "Failed to search for products"}
              </p>
            </div>
          )}

          {/* Guidance */}
          {localSelected.length === 0 && (
            <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
              <p className="text-blue-800 dark:text-blue-200 text-sm">
                Select one or more recommendations above, then click &quot;Find Trending Products&quot; to discover popular items for your design.
              </p>
            </div>
          )}

          {/* Regenerate Option */}
          <div className="flex justify-end">
            <button
              onClick={handleGenerateRecommendations}
              disabled={generateMutation.isPending}
              className="text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 underline transition-colors"
            >
              {generateMutation.isPending ? "Regenerating..." : "Regenerate Recommendations"}
            </button>
          </div>
        </div>
      </div>

      {/* Trending Products Panel - Always visible below when we have categories */}
      {showTrendingPanel && trendingCategories.length > 0 && (
        <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Trending Products
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Select one product from each category to include in your design
              </p>
            </div>
            <div className="flex items-center gap-3">
              {selectedTrendingProducts.length > 0 && (
                <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm font-medium">
                  {selectedTrendingProducts.length} of {trendingCategories.length} selected
                </span>
              )}
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {trendingCategories.map((cat, idx) => {
              const selectedProduct = getSelectedForCategory(cat.recommendation);
              return (
                <button
                  key={idx}
                  onClick={() => setActiveCategory(idx)}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
                    activeCategory === idx
                      ? "bg-purple-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {cat.recommendation}
                  {selectedProduct && (
                    <span className={`w-5 h-5 rounded-full text-xs flex items-center justify-center ${
                      activeCategory === idx
                        ? "bg-white/20 text-white"
                        : "bg-green-500 text-white"
                    }`}>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Products Grid */}
          {trendingCategories[activeCategory] && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                  {trendingCategories[activeCategory].recommendation}
                </h3>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {trendingCategories[activeCategory].products.length} trending products
                </span>
              </div>

              {trendingCategories[activeCategory].status === "error" ? (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <p className="text-red-600 dark:text-red-400">
                    Failed to load products: {trendingCategories[activeCategory].error_message}
                  </p>
                </div>
              ) : trendingCategories[activeCategory].products.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  No trending products found for this category
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {trendingCategories[activeCategory].products.map((product, idx) => {
                    const isSelected = isProductSelected(product.url);
                    return (
                      <div
                        key={idx}
                        className={`relative border-2 rounded-xl overflow-hidden transition-all cursor-pointer ${
                          isSelected
                            ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20 ring-2 ring-purple-500"
                            : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600"
                        }`}
                        onClick={() => handleSelectTrendingProduct(product, trendingCategories[activeCategory].recommendation)}
                      >
                        {/* Store Badge */}
                        <div className="absolute top-2 left-2 z-10">
                          <span className="px-2 py-1 bg-white/90 dark:bg-gray-800/90 rounded text-xs font-medium text-gray-700 dark:text-gray-300 shadow-sm">
                            {product.store}
                          </span>
                        </div>

                        {/* Selection Check */}
                        <div className="absolute top-2 right-2 z-10">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                              isSelected
                                ? "bg-purple-500 text-white"
                                : "bg-white/80 dark:bg-gray-800/80 text-gray-400"
                            }`}
                          >
                            {isSelected ? (
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                              </svg>
                            )}
                          </div>
                        </div>

                        {/* Product Image */}
                        <div className="aspect-square bg-gray-100 dark:bg-gray-700">
                          {product.image_url ? (
                            <img
                              src={product.image_url}
                              alt={product.title}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.src = `https://images.weserv.nl/?url=${encodeURIComponent(product.image_url)}&w=200&h=200&fit=cover`;
                              }}
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                            </div>
                          )}
                        </div>

                        {/* Product Info */}
                        <div className="p-3">
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 mb-1">
                            {product.title}
                          </h4>
                          {product.price_str && (
                            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                              {product.price_str}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Selected Products Summary */}
          {selectedTrendingProducts.length > 0 && (
            <div className="mt-6 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <h4 className="font-semibold text-purple-900 dark:text-purple-200 mb-3">
                Selected Products for Your Design:
              </h4>
              <div className="flex flex-wrap gap-3">
                {selectedTrendingProducts.map((product, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg p-2 pr-3 shadow-sm"
                  >
                    <img
                      src={product.image_url}
                      alt={product.title}
                      className="w-10 h-10 rounded object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = `https://images.weserv.nl/?url=${encodeURIComponent(product.image_url)}&w=40&h=40&fit=cover`;
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {product.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {product.category}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTrendingProducts((prev) =>
                          prev.filter((p) => p.url !== product.url)
                        );
                      }}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSaveSelectedTrendingProducts}
              disabled={saveSelectedTrendingMutation.isPending || selectedTrendingProducts.length === 0}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                selectedTrendingProducts.length > 0
                  ? "bg-purple-600 text-white hover:bg-purple-700"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed"
              }`}
            >
              {saveSelectedTrendingMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Saving...
                </>
              ) : (
                <>
                  Save {selectedTrendingProducts.length} Product{selectedTrendingProducts.length !== 1 ? "s" : ""} for Design
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </>
              )}
            </button>
          </div>

          {saveSelectedTrendingMutation.isError && (
            <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <p className="text-red-600 dark:text-red-400 text-sm">
                Error: {saveSelectedTrendingMutation.error?.message || "Failed to save selected products"}
              </p>
            </div>
          )}

          {saveSelectedTrendingMutation.isSuccess && (
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Products saved! They will appear in your generated design.
              </p>
            </div>
          )}
        </div>
      )}
    </>
  );
}
