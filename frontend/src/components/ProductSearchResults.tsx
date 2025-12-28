"use client";

import { useSearchProducts, useSelectProduct } from "@/lib/api";
import { ImageLightbox } from "@/components/ImageLightbox";
import React, { useState } from "react";
import ColorSchemeSelector from "./ColorSchemeSelector";
import { StyleSelector } from "./StyleSelector";

interface Product {
  url: string;
  title: string;
  store_name: string;
  price: string;
  original_price?: string;
  discount?: string;
  availability: string;
  shipping: string;
  materials: string[];
  colors: string[];
  dimensions: string[];
  features: string[];
  rating?: string;
  reviews_count?: string;
  relevance_score: number;
  extract: string;
  is_product_page: boolean;
  images: string[];
  source_api?: string; // "exa" or "serp"
  search_method?: string; // "Provider-Specific" or "Google Shopping"
}

interface ProductSearchResultsProps {
  projectId: string;
  selectedRecommendation: string;
  products: Product[];
  searchQuery?: string;
}

export function ProductSearchResults({
  projectId,
  selectedRecommendation,
  products,
  searchQuery,
}: ProductSearchResultsProps) {
  const searchMutation = useSearchProducts();
  const selectProductMutation = useSelectProduct();
  const [expandedProduct, setExpandedProduct] = useState<number | null>(null);
  const [selectedProductIndex, setSelectedProductIndex] = useState<
    number | null
  >(null);
  const [generationPrompt, setGenerationPrompt] = useState("");
  const [showColorSelector, setShowColorSelector] = useState(false);
  const [showStyleSelector, setShowStyleSelector] = useState(false);
  const [pendingProductIndex, setPendingProductIndex] = useState<number | null>(null);
  const [selectedColorScheme, setSelectedColorScheme] = useState<any>(null);
  const [lightboxImage, setLightboxImage] = useState<{
    src: string;
    alt: string;
  } | null>(null);

  // Debug logging for pendingProductIndex changes
  React.useEffect(() => {
    console.log("🔄 pendingProductIndex changed to:", pendingProductIndex);
  }, [pendingProductIndex]);

  const handleSearchProducts = () => {
    searchMutation.mutate(projectId);
  };

  const handleSelectProduct = (productIndex: number) => {
    const product = products[productIndex];
    if (!product.images || product.images.length === 0) {
      alert("This product doesn't have an image available for generation.");
      return;
    }

    // Show color selector first
    setPendingProductIndex(productIndex);
    setShowColorSelector(true);
  };

  const handleColorSchemeConfirm = (colorPalette: any) => {
    // Save color scheme and move to style selection
    setSelectedColorScheme(colorPalette);
    setShowColorSelector(false);
    setShowStyleSelector(true);
  };

  const handleStyleConfirm = (style: any) => {
    console.log("🎨 handleStyleConfirm called with:", style);
    console.log("📦 pendingProductIndex:", pendingProductIndex);
    
    if (pendingProductIndex === null) {
      console.error("❌ pendingProductIndex is null!");
      return;
    }
    
    const product = products[pendingProductIndex];
    console.log("🛍️ Selected product:", product.title);
    
    const productSelection = {
      product_url: product.url,
      product_title: product.title,
      product_image_url: product.images[0], // Use first image
      generation_prompt: generationPrompt || undefined,
      color_scheme: selectedColorScheme ? {
        palette_name: selectedColorScheme.name,
        colors: selectedColorScheme.colors,
        keep_original: false
      } : null,
      design_style: style ? {
        style_name: style.style_name,
        keep_original: style.keep_original || false
      } : null,
    };
    
    console.log("📤 Sending productSelection:", productSelection);

    selectProductMutation.mutate(
      { projectId, productSelection },
      {
        onSuccess: () => {
          setSelectedProductIndex(pendingProductIndex);
          setGenerationPrompt("");
          setPendingProductIndex(null);
          setShowStyleSelector(false);
          setSelectedColorScheme(null);
        },
        onError: (error) => {
          console.error("Failed to select product:", error);
          alert("Failed to select product. Please try again.");
          setPendingProductIndex(null);
          setShowStyleSelector(false);
          setSelectedColorScheme(null);
        },
      }
    );
  };

  // Show search button if no products yet
  if (products.length === 0) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Product Search
        </h2>
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Search for Products
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-2">
            Ready to find products for:{" "}
            <span className="font-semibold capitalize">
              {selectedRecommendation}
            </span>
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            We'll search across top furniture retailers to find products that
            match your project requirements.
          </p>
          <button
            onClick={handleSearchProducts}
            disabled={searchMutation.isPending}
            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {searchMutation.isPending ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Searching Products...</span>
              </div>
            ) : (
              "Find Products"
            )}
          </button>
          {searchMutation.isError && (
            <p className="text-red-600 dark:text-red-400 text-sm mt-2">
              Error:{" "}
              {searchMutation.error?.message || "Failed to search for products"}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Show search results
  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Product Search Results
        </h2>
        <button
          onClick={handleSearchProducts}
          disabled={searchMutation.isPending}
          className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {searchMutation.isPending ? "Searching..." : "Refresh Search"}
        </button>
      </div>

      <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <p className="text-sm text-gray-600 dark:text-gray-300">
          <strong>Search for:</strong>{" "}
          <span className="capitalize">{selectedRecommendation}</span>
        </p>
        {searchQuery && (
          <p className="text-sm text-gray-600 dark:text-gray-300">
            <strong>Query used:</strong> "{searchQuery}"
          </p>
        )}
        <div className="flex items-center justify-between mt-2">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            <strong>Found:</strong> {products.length} products total
          </p>
          <div className="flex items-center space-x-3">
            {/* SERP Results Count */}
            <span className="text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full">
              {products.length} Google Shopping Results
            </span>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product, index) => (
          <div
            key={index}
            className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
          >
            {/* Product Image */}
            {product.images && product.images.length > 0 && (
              <div className="relative w-full h-48 bg-gray-100 dark:bg-gray-700">
                <img
                  src={product.images[0]}
                  alt={product.title}
                  className="w-full h-full object-cover cursor-zoom-in"
                  loading="lazy"
                  onError={(e) => {
                    // Try image proxy if direct URL fails (fixes CAPTCHA issues)
                    const originalSrc = product.images[0];
                    const proxySrc = `https://images.weserv.nl/?url=${encodeURIComponent(
                      originalSrc
                    )}&w=400&h=300&fit=cover&output=webp`;

                    if (e.currentTarget.src !== proxySrc) {
                      console.log(
                        `🔄 Trying proxy for blocked image: ${originalSrc}`
                      );
                      e.currentTarget.src = proxySrc;
                    } else {
                      // Both original and proxy failed, hide image
                      console.log(
                        `❌ Both direct and proxy failed for: ${originalSrc}`
                      );
                      e.currentTarget.style.display = "none";
                    }
                  }}
                  onClick={(event) =>
                    setLightboxImage({
                      src: event.currentTarget.src,
                      alt: product.title,
                    })
                  }
                />
                <div className="absolute top-2 right-2">
                  <span className="text-xs bg-white/90 dark:bg-gray-800/90 text-gray-800 dark:text-gray-200 px-2 py-1 rounded-full">
                    {product.store_name}
                  </span>
                </div>
              </div>
            )}

            {/* No Image Placeholder */}
            {(!product.images || product.images.length === 0) && (
              <div className="relative w-full h-48 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                <div className="text-center">
                  <svg
                    className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    No image available
                  </p>
                </div>
                <div className="absolute top-2 right-2">
                  <span className="text-xs bg-white/90 dark:bg-gray-800/90 text-gray-800 dark:text-gray-200 px-2 py-1 rounded-full">
                    {product.store_name}
                  </span>
                </div>
              </div>
            )}

            {/* Additional Images Indicator */}
            {product.images && product.images.length > 1 && (
              <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  +{product.images.length - 1} more image
                  {product.images.length > 2 ? "s" : ""} available
                </p>
              </div>
            )}

            {/* Product Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 flex-1">
                  {product.title}
                </h3>
                <span className="text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full ml-2">
                  {Math.round(product.relevance_score * 100)}% match
                </span>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {product.store_name}
                </p>
                {/* Google Shopping Badge */}
                <span className="text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full">
                  Google Shopping
                </span>
              </div>
            </div>

            {/* Product Details */}
            <div className="p-4 space-y-3">
              {/* Price */}
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-lg text-gray-900 dark:text-white">
                  {product.price}
                </span>
                {product.original_price && (
                  <span className="text-sm text-gray-500 line-through">
                    {product.original_price}
                  </span>
                )}
                {product.discount && (
                  <span className="text-xs bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200 px-2 py-1 rounded">
                    {product.discount}
                  </span>
                )}
              </div>

              {/* Availability & Shipping */}
              <div className="flex flex-wrap gap-2 text-xs">
                <span
                  className={`px-2 py-1 rounded ${
                    product.availability.toLowerCase().includes("stock")
                      ? "bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200"
                      : "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200"
                  }`}
                >
                  {product.availability}
                </span>
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded">
                  {product.shipping}
                </span>
              </div>

              {/* Materials & Colors */}
              {(product.materials.length > 0 || product.colors.length > 0) && (
                <div className="space-y-1">
                  {product.materials.length > 0 && (
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      <strong>Materials:</strong> {product.materials.join(", ")}
                    </p>
                  )}
                  {product.colors.length > 0 && (
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      <strong>Colors:</strong> {product.colors.join(", ")}
                    </p>
                  )}
                </div>
              )}

              {/* Rating */}
              {product.rating && (
                <div className="flex items-center space-x-1">
                  <div className="flex text-yellow-400">
                    {Array.from({
                      length: Math.floor(parseFloat(product.rating)),
                    }).map((_, i) => (
                      <svg
                        key={i}
                        className="w-3 h-3 fill-current"
                        viewBox="0 0 20 20"
                      >
                        <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                      </svg>
                    ))}
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {product.rating}{" "}
                    {product.reviews_count &&
                      `(${product.reviews_count} reviews)`}
                  </span>
                </div>
              )}

              {/* Extract */}
              {product.extract && (
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                    {product.extract}
                  </p>
                  <button
                    onClick={() =>
                      setExpandedProduct(
                        expandedProduct === index ? null : index
                      )
                    }
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
                  >
                    {expandedProduct === index ? "Show less" : "Show more"}
                  </button>
                  {expandedProduct === index && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                      {product.extract}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
              <div className="flex gap-2">
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  View Product
                  <svg
                    className="w-4 h-4 ml-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>

                <button
                  onClick={() => handleSelectProduct(index)}
                  disabled={
                    selectProductMutation.isPending ||
                    selectedProductIndex === index
                  }
                  className={`flex-1 inline-flex items-center justify-center px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
                    selectedProductIndex === index
                      ? "bg-green-600 text-white"
                      : "bg-purple-600 text-white hover:bg-purple-700"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {selectProductMutation.isPending ? (
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Selecting...
                    </div>
                  ) : selectedProductIndex === index ? (
                    <div className="flex items-center">
                      <svg
                        className="w-4 h-4 mr-2"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Selected for Generation
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <svg
                        className="w-4 h-4 mr-2"
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
                      Generate with AI
                    </div>
                  )}
                </button>
              </div>

              {/* Custom prompt input - only show when this product is selected for expansion */}
              {expandedProduct === index && selectedProductIndex !== index && (
                <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Custom Generation Prompt (Optional)
                  </label>
                  <textarea
                    value={generationPrompt}
                    onChange={(e) => setGenerationPrompt(e.target.value)}
                    placeholder="e.g., Show this product in a modern, minimalist bedroom with natural lighting..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                    rows={3}
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Describe how you'd like the AI to visualize this product in
                    your space
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {products.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">                                        
          <p className="text-blue-800 dark:text-blue-200 text-sm">
            💡 <strong>Tip:</strong> Products are sorted by relevance to your
            project. Click "View Product" to see full details and purchase
            options on the retailer's website.
          </p>
        </div>
      )}

      {/* Color Scheme Selector Modal */}
      <ColorSchemeSelector
        isOpen={showColorSelector}
        onClose={() => {
          setShowColorSelector(false);
          setPendingProductIndex(null);
        }}
        onConfirm={handleColorSchemeConfirm}
      />

      {/* Style Selector Modal */}
      {showStyleSelector && (
        <StyleSelector
          onClose={() => {
            setShowStyleSelector(false);
            setPendingProductIndex(null);
            setSelectedColorScheme(null);
          }}
          onConfirm={handleStyleConfirm}
        />
      )}
      <ImageLightbox
        isOpen={Boolean(lightboxImage)}
        src={lightboxImage?.src || ""}
        alt={lightboxImage?.alt || "Image preview"}
        onClose={() => setLightboxImage(null)}
      />
    </div>
  );
}
