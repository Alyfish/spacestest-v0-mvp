'use client';

import { Check, Palette, RefreshCw, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useApplyColorScheme, useSkipColorAnalysis } from '@/lib/api';

interface ColorPalette {
    name: string;
    colors: string[];
    description: string;
}

interface ColorPaletteScreenProps {
    projectId: string;
    currentColorScheme?: {
        palette_name?: string;
        colors?: string[];
    };
    colorAnalysis?: Record<string, any>;
    colorAnalysisSkipped?: boolean;
}

const predefinedPalettes: ColorPalette[] = [
    {
        name: "Let us Decide",
        colors: ["#A8DADC", "#457B9D", "#D4A574", "#E8E8E8", "#2D3E50"],
        description: "AI chooses the optimal colors for your space"
    },
    {
        name: "Deep Blues",
        colors: ["#CAF0F8", "#90E0EF", "#00B4D8", "#0077B6", "#03045E"],
        description: "Cool and sophisticated blues"
    },
    {
        name: "Greens",
        colors: ["#D4E09B", "#A4C3A2", "#6B9080", "#4A7C59", "#2D3E40"],
        description: "Natural and calming greens"
    },
    {
        name: "High Reds",
        colors: ["#FFCDB2", "#FFB4A2", "#E5989B", "#B5838D", "#6D6875"],
        description: "Warm and energetic reds"
    },
    {
        name: "Warm Neutrals",
        colors: ["#F5F0E6", "#E8DCC8", "#C8B896", "#A08060", "#6B4423"],
        description: "Cozy earth-inspired tones"
    },
    {
        name: "Modern Grays",
        colors: ["#F8F9FA", "#E9ECEF", "#ADB5BD", "#6C757D", "#212529"],
        description: "Contemporary neutral palette"
    },
];

export function ColorPaletteScreen({
    projectId,
    currentColorScheme,
    colorAnalysis,
    colorAnalysisSkipped,
}: ColorPaletteScreenProps) {
    const [selectedPalette, setSelectedPalette] = useState<ColorPalette | null>(
        currentColorScheme?.palette_name
            ? predefinedPalettes.find(p => p.name === currentColorScheme.palette_name) || null
            : null
    );

    const applyColorSchemeMutation = useApplyColorScheme();
    const skipColorMutation = useSkipColorAnalysis();

    const handleSelectPalette = (palette: ColorPalette) => {
        setSelectedPalette(palette);
    };

    const handleClearSelection = () => {
        setSelectedPalette(null);
    };

    const handleApplyColors = () => {
        if (!selectedPalette) return;

        applyColorSchemeMutation.mutate({
            projectId,
            paletteName: selectedPalette.name,
            colors: selectedPalette.colors,
            letAiDecide: selectedPalette.name === "Let us Decide",
        });
    };

    const isApplied = currentColorScheme?.palette_name === selectedPalette?.name;
    const isSkipped = Boolean(colorAnalysisSkipped);
    const paletteAdaptations = colorAnalysis?.palette_adaptations;
    const showPaletteAdaptations =
        Boolean(paletteAdaptations) &&
        paletteAdaptations !== "Fallback analysis used due to response formatting.";

    return (
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                        <Palette className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                            Choose Colors
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Select a color palette to apply to your space
                        </p>
                    </div>
                </div>
                {selectedPalette && (
                    <button
                        onClick={handleClearSelection}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Clear All
                    </button>
                )}
            </div>

            {/* Color Palettes Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {predefinedPalettes.map((palette) => (
                    <button
                        key={palette.name}
                        onClick={() => handleSelectPalette(palette)}
                        className={`p-4 rounded-xl border-2 transition-all text-left ${selectedPalette?.name === palette.name
                                ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                            }`}
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${selectedPalette?.name === palette.name
                                        ? 'border-purple-500 bg-purple-500'
                                        : 'border-gray-300 dark:border-gray-600'
                                    }`}>
                                    {selectedPalette?.name === palette.name && (
                                        <Check className="w-3 h-3 text-white" />
                                    )}
                                </div>
                                <p className="font-medium text-gray-900 dark:text-white">
                                    {palette.name}
                                </p>
                            </div>
                            {palette.name === "Let us Decide" && (
                                <span className="flex items-center gap-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-2 py-1 rounded-full">
                                    <Sparkles className="w-3 h-3" />
                                    AI
                                </span>
                            )}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                            {palette.description}
                        </p>
                        <div className="flex gap-1">
                            {palette.colors.map((color, idx) => (
                                <div
                                    key={idx}
                                    className="flex-1 h-10 rounded-lg border border-gray-200 dark:border-gray-600"
                                    style={{ backgroundColor: color }}
                                />
                            ))}
                        </div>
                    </button>
                ))}
            </div>

            {/* Apply Button */}
            {selectedPalette && (
                <div className="mt-6 flex items-center justify-between">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                        Selected: <span className="font-medium text-gray-900 dark:text-white">{selectedPalette.name}</span>
                    </div>
                    <button
                        onClick={handleApplyColors}
                        disabled={applyColorSchemeMutation.isPending || isApplied}
                        className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-colors ${isApplied
                                ? 'bg-green-600 text-white cursor-default'
                                : 'bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                            }`}
                    >
                        {applyColorSchemeMutation.isPending ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                                Analyzing...
                            </>
                        ) : isApplied ? (
                            <>
                                <Check className="w-4 h-4" />
                                Applied
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4" />
                                Apply & Analyze
                            </>
                        )}
                    </button>
                </div>
            )}

            {!colorAnalysis && !isSkipped && (
                <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Color analysis is optional. You can skip and continue.
                    </p>
                    <button
                        onClick={() => skipColorMutation.mutate(projectId)}
                        disabled={skipColorMutation.isPending}
                        className="px-4 py-2 text-sm text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {skipColorMutation.isPending ? "Skipping..." : "Skip for now"}
                    </button>
                </div>
            )}

            {isSkipped && !colorAnalysis && (
                <div className="mt-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                        Color analysis skipped. You can choose a palette anytime to add color guidance.
                    </p>
                </div>
            )}

            {/* Color Analysis Results */}
            {colorAnalysis && (
                <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                        Color Analysis
                    </h3>

                    <div className="space-y-4">
                        {/* Space Summary */}
                        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                            <p className="text-sm text-gray-700 dark:text-gray-300">
                                {colorAnalysis.space_summary}
                            </p>
                        </div>

                        {/* Color Theory */}
                        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                            <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
                                Color Theory: {colorAnalysis.color_theory_approach}
                            </p>
                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                {colorAnalysis.color_theory_rationale}
                            </p>
                        </div>

                        {/* Color Assignments */}
                        {colorAnalysis.color_assignments && colorAnalysis.color_assignments.length > 0 && (
                            <div>
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Color Assignments:
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {colorAnalysis.color_assignments.slice(0, 6).map((assignment: any, idx: number) => (
                                        <div
                                            key={idx}
                                            className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
                                        >
                                            <div
                                                className="w-8 h-8 rounded-md border border-gray-200 dark:border-gray-600"
                                                style={{ backgroundColor: assignment.color_hex }}
                                            />
                                            <div>
                                                <p className="text-sm font-medium text-gray-900 dark:text-white">
                                                    {assignment.element}
                                                </p>
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    {assignment.color_name}
                                                    {assignment.finish && ` • ${assignment.finish}`}
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Palette Adaptations */}
                        {showPaletteAdaptations && (
                            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
                                <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                                    Design Adaptations
                                </p>
                                <p className="text-sm text-amber-700 dark:text-amber-300">
                                    {paletteAdaptations}
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Error Handling */}
            {applyColorSchemeMutation.isError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                        Failed to apply color scheme: {applyColorSchemeMutation.error?.message}
                    </p>
                </div>
            )}
            {skipColorMutation.isError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                        Failed to skip color analysis: {skipColorMutation.error?.message}
                    </p>
                </div>
            )}
        </div>
    );
}
