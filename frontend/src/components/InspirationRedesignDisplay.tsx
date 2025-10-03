"use client";

import { useClipSearch, useGenerateInspirationRedesign } from "@/lib/api";
import { useRef, useState } from "react";

interface InspirationRedesignDisplayProps {
  projectId: string;
  generatedImageBase64?: string;
  inspirationPrompt?: string;
  hasRecommendations: boolean;
}

export function InspirationRedesignDisplay({
  projectId,
  generatedImageBase64,
  inspirationPrompt,
  hasRecommendations,
}: InspirationRedesignDisplayProps) {
  const generateRedesign = useGenerateInspirationRedesign();
  const [imageError, setImageError] = useState(false);
  
  // CLIP clip-search functionality
  const clipSearch = useClipSearch();
  const imgContainerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  const [currentPos, setCurrentPos] = useState<{ x: number; y: number } | null>(null);
  const [clipResults, setClipResults] = useState<{
    search_query: string;
    products: any[];
  } | null>(null);

  const handleGenerate = () => {
    generateRedesign.mutate(projectId, {
      onError: (error) => {
        console.error("Failed to generate inspiration redesign:", error);
        alert("Failed to generate inspiration redesign. Please try again.");
      },
    });
  };

  // Mouse event handlers for clip-search
  const onMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imgContainerRef.current) return;
    const rect = imgContainerRef.current.getBoundingClientRect();
    setIsDragging(true);
    setClipResults(null);
    setStartPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setCurrentPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging || !imgContainerRef.current) return;
    const rect = imgContainerRef.current.getBoundingClientRect();
    setCurrentPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const onMouseUp = () => {
    if (!isDragging || !imgContainerRef.current || !startPos || !currentPos) return;
    setIsDragging(false);
    const rect = imgContainerRef.current.getBoundingClientRect();
    const x1 = Math.max(0, Math.min(startPos.x, currentPos.x));
    const y1 = Math.max(0, Math.min(startPos.y, currentPos.y));
    const x2 = Math.min(rect.width, Math.max(startPos.x, currentPos.x));
    const y2 = Math.min(rect.height, Math.max(startPos.y, currentPos.y));
    const width = rect.width;
    const height = rect.height;

    const normRect = {
      x: x1 / width,
      y: y1 / height,
      width: Math.max(1, x2 - x1) / width,
      height: Math.max(1, y2 - y1) / height,
    };

    // Use inspiration generated image for clip search
    clipSearch.mutate(
      { projectId, rect: normRect, useInspirationImage: true },
      {
        onSuccess: (data) => {
          setClipResults({ search_query: data.search_query, products: data.products });
        },
        onError: (err) => {
          console.error("Clip search failed", err);
          alert("Clip search failed. Try selecting a clear product region.");
        },
      }
    );
  };

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Inspiration-based Redesign
      </h2>

      {!generatedImageBase64 && (
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-300">
            Generate a new image that applies your inspiration recommendations to
            the original room image while preserving its structure.
          </p>
          <button
            onClick={handleGenerate}
            disabled={
              generateRedesign.isPending || !hasRecommendations
            }
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generateRedesign.isPending
              ? "Generating..."
              : "Generate Inspiration Redesign"}
          </button>
          {!hasRecommendations && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Add inspiration images and generate recommendations first.
            </p>
          )}
        </div>
      )}

      {generatedImageBase64 && (
        <div className="mt-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
            AI Redesigned Room
          </h3>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 italic">
              💡 Tip: Click and drag on the image to identify furniture with AI
            </p>
            {!imageError ? (
              <div
                ref={imgContainerRef}
                className="relative w-full h-64 rounded-lg overflow-hidden cursor-crosshair"
                onMouseDown={onMouseDown}
                onMouseMove={onMouseMove}
                onMouseUp={onMouseUp}
              >
                <img
                  src={`data:image/png;base64,${generatedImageBase64}`}
                  alt="Inspiration Redesign"
                  className="w-full h-full object-cover"
                  onError={() => setImageError(true)}
                />
                {isDragging && startPos && currentPos && (
                  <div
                    className="absolute border-2 border-purple-500 bg-purple-500/20"
                    style={{
                      left: Math.min(startPos.x, currentPos.x),
                      top: Math.min(startPos.y, currentPos.y),
                      width: Math.abs(currentPos.x - startPos.x),
                      height: Math.abs(currentPos.y - startPos.y),
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="w-full h-64 bg-gray-200 dark:bg-gray-600 rounded-lg mb-3 flex items-center justify-center">
                <div className="text-center">
                  <svg
                    className="w-12 h-12 text-gray-400 mx-auto mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    Failed to load redesign image
                  </p>
                </div>
              </div>
            )}
            <p className="font-medium text-gray-900 dark:text-white text-sm mt-3">
              Generated by Gemini AI using your inspiration
            </p>
          </div>

          {/* CLIP Search Results */}
          {(clipSearch.isPending || clipResults) && (
            <div className="mt-4">
              {clipSearch.isPending && (
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  🔍 Analyzing furniture with AI vision...
                </p>
              )}
              {clipResults && (
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-gray-900 dark:text-white">
                      Products for: <span className="italic">{clipResults.search_query}</span>
                    </h4>
                    {(clipResults as any).analysis_method === 'clip' && (
                      <span className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 rounded-full">
                        ⚡ AI Enhanced
                      </span>
                    )}
                  </div>
                  
                  {/* CLIP Analysis Details */}
                  {(clipResults as any).clip_analysis && (
                    <div className="mb-4 p-3 bg-white dark:bg-gray-800 rounded border border-purple-200 dark:border-purple-800">
                      <p className="text-xs font-semibold text-purple-900 dark:text-purple-300 mb-2">
                        🤖 CLIP AI Analysis
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {(clipResults as any).clip_analysis.furniture_type && (
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Type:</span>{" "}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {(clipResults as any).clip_analysis.furniture_type}
                            </span>
                            {(clipResults as any).clip_analysis.furniture_confidence && (
                              <span className="ml-1 text-gray-500">
                                ({Math.round((clipResults as any).clip_analysis.furniture_confidence * 100)}%)
                              </span>
                            )}
                          </div>
                        )}
                        {(clipResults as any).clip_analysis.style && (
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Style:</span>{" "}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {(clipResults as any).clip_analysis.style}
                            </span>
                          </div>
                        )}
                        {(clipResults as any).clip_analysis.material && (
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Material:</span>{" "}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {(clipResults as any).clip_analysis.material}
                            </span>
                          </div>
                        )}
                        {(clipResults as any).clip_analysis.color && (
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Color:</span>{" "}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {(clipResults as any).clip_analysis.color}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {clipResults.products.length === 0 ? (
                    <p className="text-sm text-gray-600 dark:text-gray-300">No products found. Try selecting a different region.</p>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {clipResults.products.slice(0, 6).map((p, idx) => (
                        <a
                          key={idx}
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition p-2"
                        >
                          {p.images && p.images[0] && (
                            <img
                              src={p.images[0]}
                              alt={p.title}
                              className="w-full h-28 object-cover rounded"
                              onError={(e) => {
                                const t = e.target as HTMLImageElement;
                                t.src = `https://images.weserv.nl/?url=${encodeURIComponent(p.images[0])}&w=300&h=200&fit=cover`;
                              }}
                            />
                          )}
                          <div className="mt-2">
                            <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">{p.title}</p>
                            {p.price_str && (
                              <p className="text-sm text-gray-700 dark:text-gray-300">{p.price_str}</p>
                            )}
                          </div>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {inspirationPrompt && (
        <div className="mt-6 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
          <h4 className="font-medium text-indigo-900 dark:text-indigo-200 mb-2">
            Prompt Used:
          </h4>
          <p className="text-indigo-800 dark:text-indigo-300 text-sm">
            {inspirationPrompt}
          </p>
        </div>
      )}
    </div>
  );
}



