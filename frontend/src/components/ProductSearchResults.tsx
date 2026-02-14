"use client";

import { useSearchProducts, useSelectProduct, useAutoSelectProduct } from "@/lib/api";
import { ImageLightbox } from "@/components/ImageLightbox";
import React, { useState, useEffect } from "react";
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
  source_api?: string;
  search_method?: string;
  similarity_score?: number;
  combined_score?: number;
  store_trust?: number;
  filter_reason?: string;
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
  const autoSelectMutation = useAutoSelectProduct();

  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [selectionReason, setSelectionReason] = useState<string>("");
  const [alternativeProducts, setAlternativeProducts] = useState<Product[]>([]);
  const [isAutoSelecting, setIsAutoSelecting] = useState(false);

  const [showColorSelector, setShowColorSelector] = useState(false);
  const [showStyleSelector, setShowStyleSelector] = useState(false);
  const [selectedColorScheme, setSelectedColorScheme] = useState<any>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [lightboxImage, setLightboxImage] = useState<{
    src: string;
    alt: string;
  } | null>(null);

  // Filter products: only show those with valid images, limit to 4
  const filteredProducts = products
    .filter((p) => p.images && p.images.length > 0 && p.images[0].length > 10)
    .slice(0, 4);

  // Auto-select best product when products are loaded
  useEffect(() => {
    if (filteredProducts.length > 0 && !selectedProduct && !isAutoSelecting) {
      setIsAutoSelecting(true);
      autoSelectMutation.mutate(projectId, {
        onSuccess: (data) => {
          setSelectedProduct(data.selected_product as unknown as Product);
          setSelectionReason(data.selection_reason);
          setAlternativeProducts(data.alternatives as unknown as Product[]);
          setIsAutoSelecting(false);
        },
        onError: () => {
          // Fallback: use first product as selected
          setSelectedProduct(filteredProducts[0]);
          setSelectionReason("best match");
          setAlternativeProducts(filteredProducts.slice(1, 4));
          setIsAutoSelecting(false);
        },
      });
    }
  }, [filteredProducts.length, projectId]);

  const handleSearchProducts = () => {
    setSelectionError(null);
    setSelectedProduct(null);
    setAlternativeProducts([]);
    searchMutation.mutate(projectId);
  };

  const handleOverrideSelection = (product: Product) => {
    // Move current selected to alternatives, set new selection
    if (selectedProduct) {
      const newAlternatives = [selectedProduct, ...alternativeProducts.filter(p => p.url !== product.url)].slice(0, 3);
      setAlternativeProducts(newAlternatives);
    }
    setSelectedProduct(product);
    setSelectionReason("manually selected");
  };

  const handleProceedWithSelection = () => {
    if (!selectedProduct) return;
    setShowColorSelector(true);
  };

  const handleColorSchemeConfirm = (colorPalette: any) => {
    setSelectedColorScheme(colorPalette);
    setShowColorSelector(false);
    setShowStyleSelector(true);
  };

  const handleStyleConfirm = (style: any) => {
    if (!selectedProduct) return;
    setSelectionError(null);

    const productSelection = {
      product_url: selectedProduct.url,
      product_title: selectedProduct.title,
      product_image_url: selectedProduct.images[0],
      generation_prompt: undefined,
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

    selectProductMutation.mutate(
      { projectId, productSelection },
      {
        onSuccess: () => {
          setShowStyleSelector(false);
          setSelectedColorScheme(null);
        },
        onError: (error) => {
          console.error("Failed to select product:", error);
          setSelectionError("Failed to save product selection. Please try again.");
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
            We&apos;ll search across top furniture retailers to find products that
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

  // Loading state while auto-selecting
  if (isAutoSelecting || autoSelectMutation.isPending) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Product Search Results
        </h2>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">
            AI is selecting the best product for your room...
          </p>
        </div>
      </div>
    );
  }

  // Show search results with AI-selected product at top
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
            <strong>Query used:</strong> &quot;{searchQuery}&quot;
          </p>
        )}
      </div>

      {selectionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
          {selectionError}
        </div>
      )}

      {/* AI Selected Product - Featured Card */}
      {selectedProduct && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-full text-sm font-medium">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              AI Selected
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectionReason}
            </span>
          </div>

          <div className="border-2 border-purple-500 bg-purple-50 dark:bg-purple-900/10 rounded-xl overflow-hidden">
            <div className="md:flex">
              {/* Large Product Image */}
              <div className="md:w-1/2 relative">
                {selectedProduct.images && selectedProduct.images.length > 0 && (
                  <img
                    src={selectedProduct.images[0]}
                    alt={selectedProduct.title}
                    className="w-full h-64 md:h-full object-cover cursor-zoom-in"
                    onError={(e) => {
                      const originalSrc = selectedProduct.images[0];
                      const proxySrc = `https://images.weserv.nl/?url=${encodeURIComponent(originalSrc)}&w=600&h=400&fit=cover`;
                      if (e.currentTarget.src !== proxySrc) {
                        e.currentTarget.src = proxySrc;
                      }
                    }}
                    onClick={() => setLightboxImage({
                      src: selectedProduct.images[0],
                      alt: selectedProduct.title,
                    })}
                  />
                )}
                <div className="absolute top-3 left-3">
                  <span className="px-3 py-1 bg-white/95 dark:bg-gray-800/95 text-gray-800 dark:text-gray-200 rounded-full text-sm font-medium shadow">
                    {selectedProduct.store_name}
                  </span>
                </div>
              </div>

              {/* Product Details */}
              <div className="md:w-1/2 p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  {selectedProduct.title}
                </h3>

                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl font-bold text-gray-900 dark:text-white">
                    {selectedProduct.price}
                  </span>
                  {selectedProduct.original_price && (
                    <span className="text-lg text-gray-500 line-through">
                      {selectedProduct.original_price}
                    </span>
                  )}
                  {selectedProduct.discount && (
                    <span className="px-2 py-1 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded text-sm">
                      {selectedProduct.discount}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    selectedProduct.availability?.toLowerCase().includes("stock")
                      ? "bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300"
                      : "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300"
                  }`}>
                    {selectedProduct.availability}
                  </span>
                  {selectedProduct.store_trust && selectedProduct.store_trust >= 0.85 && (
                    <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 rounded-full text-sm">
                      Trusted Retailer
                    </span>
                  )}
                </div>

                {selectedProduct.rating && (
                  <div className="flex items-center gap-2 mb-4">
                    <div className="flex text-yellow-400">
                      {Array.from({ length: Math.floor(parseFloat(selectedProduct.rating)) }).map((_, i) => (
                        <svg key={i} className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                          <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                        </svg>
                      ))}
                    </div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {selectedProduct.rating} {selectedProduct.reviews_count && `(${selectedProduct.reviews_count} reviews)`}
                    </span>
                  </div>
                )}

                <div className="flex gap-3 mt-6">
                  <a
                    href={selectedProduct.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 inline-flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    View Product
                    <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                  <button
                    onClick={handleProceedWithSelection}
                    disabled={selectProductMutation.isPending}
                    className="flex-1 inline-flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium disabled:opacity-50"
                  >
                    {selectProductMutation.isPending ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        Generate Room Image
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Alternative Products */}
      {alternativeProducts.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Alternative Options
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Click on any product below to select it instead
          </p>

          <div className="grid md:grid-cols-3 gap-4">
            {alternativeProducts.map((product, index) => (
              <div
                key={index}
                onClick={() => handleOverrideSelection(product)}
                className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden hover:border-purple-400 hover:shadow-md transition-all cursor-pointer"
              >
                {product.images && product.images.length > 0 && (
                  <div className="relative w-full h-36 bg-gray-100 dark:bg-gray-700">
                    <img
                      src={product.images[0]}
                      alt={product.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      onError={(e) => {
                        const originalSrc = product.images[0];
                        const proxySrc = `https://images.weserv.nl/?url=${encodeURIComponent(originalSrc)}&w=300&h=200&fit=cover`;
                        if (e.currentTarget.src !== proxySrc) {
                          e.currentTarget.src = proxySrc;
                        }
                      }}
                    />
                    <div className="absolute top-2 right-2">
                      <span className="text-xs bg-white/90 dark:bg-gray-800/90 px-2 py-1 rounded-full">
                        {product.store_name}
                      </span>
                    </div>
                  </div>
                )}
                <div className="p-3">
                  <h4 className="font-medium text-gray-900 dark:text-white text-sm line-clamp-2 mb-2">
                    {product.title}
                  </h4>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {product.price}
                    </span>
                    <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                      Click to select
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Color Scheme Selector Modal */}
      <ColorSchemeSelector
        isOpen={showColorSelector}
        onClose={() => {
          setShowColorSelector(false);
        }}
        onConfirm={handleColorSchemeConfirm}
      />

      {/* Style Selector Modal */}
      {showStyleSelector && (
        <StyleSelector
          onClose={() => {
            setShowStyleSelector(false);
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
