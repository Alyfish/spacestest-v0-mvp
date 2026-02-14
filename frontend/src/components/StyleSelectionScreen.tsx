'use client';

import {
    Check,
    Sparkles,
    RefreshCw,
    Home,
    Leaf,
    Building2,
    Palette,
    Crown,
    Minimize2,
    Trees,
    Flower2,
    Gem,
    Zap,
} from 'lucide-react';
import { useState } from 'react';
import { useApplyStyle, useSkipStyleAnalysis } from '@/lib/api';

interface DesignStyle {
    name: string;
    description: string;
    icon: React.ReactNode;
    mood: string;
}

interface StyleSelectionScreenProps {
    projectId: string;
    currentDesignStyle?: {
        style_name?: string;
    };
    styleAnalysis?: Record<string, any>;
    styleAnalysisSkipped?: boolean;
}

const designStyles: DesignStyle[] = [
    {
        name: "Let AI Decide",
        description: "AI chooses the optimal style for your space",
        icon: <Sparkles className="w-5 h-5" />,
        mood: "Personalized",
    },
    {
        name: "Bohemian",
        description: "Eclectic, free-spirited, globally inspired",
        icon: <Flower2 className="w-5 h-5" />,
        mood: "Creative & Vibrant",
    },
    {
        name: "Scandinavian",
        description: "Bright, airy, functional minimalism",
        icon: <Leaf className="w-5 h-5" />,
        mood: "Calm & Cozy",
    },
    {
        name: "Modern",
        description: "Clean lines, contemporary aesthetics",
        icon: <Building2 className="w-5 h-5" />,
        mood: "Sleek & Current",
    },
    {
        name: "Art Deco",
        description: "Glamorous, bold geometric patterns",
        icon: <Gem className="w-5 h-5" />,
        mood: "Luxurious & Bold",
    },
    {
        name: "Contemporary",
        description: "Always evolving, of-the-moment design",
        icon: <Zap className="w-5 h-5" />,
        mood: "Fresh & Sophisticated",
    },
    {
        name: "Mid-Century Modern",
        description: "Retro-futuristic, organic shapes",
        icon: <Palette className="w-5 h-5" />,
        mood: "Warm & Iconic",
    },
    {
        name: "Industrial",
        description: "Raw, urban, exposed materials",
        icon: <Building2 className="w-5 h-5" />,
        mood: "Edgy & Masculine",
    },
    {
        name: "Traditional",
        description: "Classic elegance, timeless pieces",
        icon: <Crown className="w-5 h-5" />,
        mood: "Formal & Refined",
    },
    {
        name: "Minimalist",
        description: "Less is more, essential design",
        icon: <Minimize2 className="w-5 h-5" />,
        mood: "Serene & Uncluttered",
    },
    {
        name: "Farmhouse",
        description: "Rustic charm meets modern comfort",
        icon: <Home className="w-5 h-5" />,
        mood: "Cozy & Welcoming",
    },
    {
        name: "French Country",
        description: "Romantic, vintage European charm",
        icon: <Trees className="w-5 h-5" />,
        mood: "Soft & Elegant",
    },
];

export function StyleSelectionScreen({
    projectId,
    currentDesignStyle,
    styleAnalysis,
    styleAnalysisSkipped,
}: StyleSelectionScreenProps) {
    const [selectedStyle, setSelectedStyle] = useState<DesignStyle | null>(
        currentDesignStyle?.style_name
            ? designStyles.find(s => s.name === currentDesignStyle.style_name) || null
            : null
    );

    const applyStyleMutation = useApplyStyle();
    const skipStyleMutation = useSkipStyleAnalysis();

    const handleSelectStyle = (style: DesignStyle) => {
        setSelectedStyle(style);
    };

    const handleClearSelection = () => {
        setSelectedStyle(null);
    };

    const handleApplyStyle = () => {
        if (!selectedStyle) return;

        applyStyleMutation.mutate({
            projectId,
            styleName: selectedStyle.name,
            letAiDecide: selectedStyle.name === "Let AI Decide",
        });
    };

    const isApplied = currentDesignStyle?.style_name === selectedStyle?.name;
    const isSkipped = Boolean(styleAnalysisSkipped);

    return (
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                        <Palette className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                            Choose Style
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Select an interior design style for your space
                        </p>
                    </div>
                </div>
                {selectedStyle && (
                    <button
                        onClick={handleClearSelection}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Clear
                    </button>
                )}
            </div>

            {/* Styles Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {designStyles.map((style) => (
                    <button
                        key={style.name}
                        onClick={() => handleSelectStyle(style)}
                        className={`p-4 rounded-xl border-2 transition-all text-left ${selectedStyle?.name === style.name
                                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                            }`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <div className={`p-2 rounded-lg ${selectedStyle?.name === style.name
                                    ? 'bg-indigo-500 text-white'
                                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                                }`}>
                                {style.icon}
                            </div>
                            {selectedStyle?.name === style.name && (
                                <div className="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center">
                                    <Check className="w-3 h-3 text-white" />
                                </div>
                            )}
                        </div>
                        <p className="font-medium text-gray-900 dark:text-white text-sm">
                            {style.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                            {style.description}
                        </p>
                    </button>
                ))}
            </div>

            {/* Apply Button */}
            {selectedStyle && (
                <div className="mt-6 flex items-center justify-between">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                        Selected: <span className="font-medium text-gray-900 dark:text-white">{selectedStyle.name}</span>
                        <span className="ml-2 text-indigo-600 dark:text-indigo-400">• {selectedStyle.mood}</span>
                    </div>
                    <button
                        onClick={handleApplyStyle}
                        disabled={applyStyleMutation.isPending || isApplied}
                        className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-colors ${isApplied
                                ? 'bg-green-600 text-white cursor-default'
                                : 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                            }`}
                    >
                        {applyStyleMutation.isPending ? (
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

            {!styleAnalysis && !isSkipped && (
                <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Style analysis is optional. You can skip and continue.
                    </p>
                    <button
                        onClick={() => skipStyleMutation.mutate(projectId)}
                        disabled={skipStyleMutation.isPending}
                        className="px-4 py-2 text-sm text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {skipStyleMutation.isPending ? "Skipping..." : "Skip for now"}
                    </button>
                </div>
            )}

            {isSkipped && !styleAnalysis && (
                <div className="mt-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                        Style analysis skipped. You can choose a style anytime to add style guidance.
                    </p>
                </div>
            )}

            {/* Style Analysis Results */}
            {styleAnalysis && (
                <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                        Style Analysis: {styleAnalysis.style_name}
                    </h3>

                    <div className="space-y-4">
                        {/* Overview */}
                        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                            <p className="text-sm text-gray-700 dark:text-gray-300">
                                {styleAnalysis.style_overview}
                            </p>
                        </div>

                        {/* Materials & Colors */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
                                <p className="text-sm font-medium text-indigo-800 dark:text-indigo-200 mb-2">
                                    Key Materials
                                </p>
                                <div className="flex flex-wrap gap-1">
                                    {styleAnalysis.materials?.slice(0, 5).map((material: string, idx: number) => (
                                        <span key={idx} className="text-xs bg-indigo-100 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-200 px-2 py-1 rounded">
                                            {material}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                                <p className="text-sm font-medium text-purple-800 dark:text-purple-200 mb-2">
                                    Anchor Pieces
                                </p>
                                <ul className="text-sm text-purple-700 dark:text-purple-300 space-y-1">
                                    {styleAnalysis.anchor_pieces?.slice(0, 2).map((piece: string, idx: number) => (
                                        <li key={idx}>• {piece}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Furniture Recommendations */}
                        {styleAnalysis.furniture_recommendations && styleAnalysis.furniture_recommendations.length > 0 && (
                            <div>
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Recommended Furniture:
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {styleAnalysis.furniture_recommendations.slice(0, 4).map((rec: any, idx: number) => (
                                        <div
                                            key={idx}
                                            className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
                                        >
                                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                                                {rec.item_type}
                                            </p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                                                {rec.description}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Styling Tips */}
                        {styleAnalysis.styling_tips && styleAnalysis.styling_tips.length > 0 && (
                            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                                <p className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                                    Pro Styling Tips
                                </p>
                                <ul className="text-sm text-green-700 dark:text-green-300 space-y-1">
                                    {styleAnalysis.styling_tips.slice(0, 3).map((tip: string, idx: number) => (
                                        <li key={idx}>✓ {tip}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Error Handling */}
            {applyStyleMutation.isError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                        Failed to apply style: {applyStyleMutation.error?.message}
                    </p>
                </div>
            )}
            {skipStyleMutation.isError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                        Failed to skip style analysis: {skipStyleMutation.error?.message}
                    </p>
                </div>
            )}
        </div>
    );
}
