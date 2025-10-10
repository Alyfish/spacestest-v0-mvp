"use client";

import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

interface AffiliateProduct {
  original_url: string;
  affiliate_url: string;
  product_id: string;
  product_name?: string;
}

interface RetailerCart {
  retailer: string;
  retailer_display_name: string;
  products: AffiliateProduct[];
  cart_url: string;
  product_count: number;
}

interface AffiliateCartResponse {
  carts: RetailerCart[];
  total_products: number;
  total_retailers: number;
  status: string;
  message: string;
}

export default function AffiliateCartPage() {
  const [urlsText, setUrlsText] = useState("");
  const [carts, setCarts] = useState<RetailerCart[]>([]);

  const generateCartMutation = useMutation({
    mutationFn: async (urls: string[]) => {
      const response = await fetch("http://localhost:8000/api/affiliate/generate-cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_urls: urls }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate affiliate cart");
      }

      return response.json() as Promise<AffiliateCartResponse>;
    },
    onSuccess: (data) => {
      setCarts(data.carts);
    },
  });

  const handleGenerate = () => {
    // Split by newlines and filter out empty lines
    const urls = urlsText
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url.length > 0);

    if (urls.length === 0) {
      alert("Please enter at least one product URL");
      return;
    }

    generateCartMutation.mutate(urls);
  };

  const handleClear = () => {
    setUrlsText("");
    setCarts([]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🛒 Affiliate Cart Generator
          </h1>
          <p className="text-gray-600">
            Paste product URLs below (one per line) to generate affiliate cart links
          </p>
        </div>

        {/* Input Section */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Product URLs
          </label>
          <textarea
            value={urlsText}
            onChange={(e) => setUrlsText(e.target.value)}
            placeholder="https://www.amazon.com/product/...&#10;https://www.ikea.com/product/...&#10;https://www.wayfair.com/product/..."
            className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono text-sm"
          />

          <div className="flex gap-3 mt-4">
            <button
              onClick={handleGenerate}
              disabled={generateCartMutation.isPending || !urlsText.trim()}
              className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {generateCartMutation.isPending ? "Generating..." : "Generate Affiliate Carts"}
            </button>
            <button
              onClick={handleClear}
              className="px-6 py-3 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
            >
              Clear
            </button>
          </div>

          {generateCartMutation.isError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">
                ❌ Error: {(generateCartMutation.error as Error).message}
              </p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {carts.length > 0 && (
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-900 font-medium">
                ✅ Generated {carts.length} cart(s) with{" "}
                {carts.reduce((sum, cart) => sum + cart.product_count, 0)} product(s)
              </p>
            </div>

            {carts.map((cart, index) => (
              <div
                key={index}
                className="bg-white rounded-xl shadow-lg overflow-hidden"
              >
                {/* Retailer Header */}
                <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
                  <h2 className="text-2xl font-bold text-white">
                    {cart.retailer_display_name}
                  </h2>
                  <p className="text-blue-100 text-sm">
                    {cart.product_count} product{cart.product_count !== 1 ? "s" : ""}
                  </p>
                </div>

                {/* Products List */}
                <div className="p-6">
                  <div className="space-y-3 mb-6">
                    {cart.products.map((product, pIndex) => (
                      <div
                        key={pIndex}
                        className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg"
                      >
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                          {pIndex + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-600 mb-1">Product ID: {product.product_id}</p>
                          <a
                            href={product.affiliate_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-sm break-all"
                          >
                            {product.affiliate_url}
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add All to Cart Button */}
                  <a
                    href={cart.cart_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full bg-green-600 text-white text-center px-6 py-4 rounded-lg font-bold text-lg hover:bg-green-700 transition-colors"
                  >
                    🛒 Add All {cart.product_count} Item{cart.product_count !== 1 ? "s" : ""} to {cart.retailer_display_name} Cart
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {carts.length === 0 && !generateCartMutation.isPending && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="text-6xl mb-4">🛍️</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              No carts generated yet
            </h3>
            <p className="text-gray-500">
              Paste product URLs above and click "Generate Affiliate Carts" to get started
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

