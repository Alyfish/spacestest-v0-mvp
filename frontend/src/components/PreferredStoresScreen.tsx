'use client';

import { Check, ShoppingBag, Sparkles, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { useUpdatePreferredStores } from '@/lib/api';

interface Retailer {
    id: string;
    name: string;
}

interface PreferredStoresScreenProps {
    projectId: string;
    currentPreferredStores?: string[];
}

const retailers: Retailer[] = [
    { id: 'walmart', name: 'Walmart' },
    { id: 'amazon', name: 'Amazon' },
    { id: 'ikea', name: 'IKEA' },
    { id: 'ashley', name: 'Ashley Homestore' },
    { id: 'crateandbarrel', name: 'Crate & Barrel' },
    { id: 'wayfair', name: 'Wayfair' },
    { id: 'other', name: 'Other' },
    { id: 'target', name: 'Target' },
    { id: 'westelm', name: 'West Elm' },
    { id: 'potterybarn', name: 'Pottery Barn' },
    { id: 'homedepot', name: 'Home Depot' },
    { id: 'lowes', name: 'Lowes' },
];

export function PreferredStoresScreen({
    projectId,
    currentPreferredStores = [],
}: PreferredStoresScreenProps) {
    const [selectedStores, setSelectedStores] = useState<string[]>(currentPreferredStores);

    const updatePreferredStoresMutation = useUpdatePreferredStores();

    const toggleStore = (storeName: string) => {
        setSelectedStores((prev) =>
            prev.includes(storeName)
                ? prev.filter((s) => s !== storeName)
                : [...prev, storeName]
        );
    };

    const handleClearAll = () => {
        setSelectedStores([]);
    };

    const handleSavePreferences = () => {
        updatePreferredStoresMutation.mutate({
            projectId,
            stores: selectedStores,
        });
    };

    const hasChanged =
        JSON.stringify([...selectedStores].sort()) !==
        JSON.stringify([...currentPreferredStores].sort());

    const isApplied = !hasChanged && selectedStores.length > 0;

    return (
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-pink-100 dark:bg-pink-900/30 rounded-lg">
                        <ShoppingBag className="w-6 h-6 text-pink-600 dark:text-pink-400" />
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                            Preferred Store(s)
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Select your favorite retailers for product recommendations
                        </p>
                    </div>
                </div>
                {selectedStores.length > 0 && (
                    <button
                        onClick={handleClearAll}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Clear All
                    </button>
                )}
            </div>

            {/* Stores Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {retailers.map((store) => (
                    <button
                        key={store.id}
                        onClick={() => toggleStore(store.name)}
                        className={`p-6 rounded-xl border-2 transition-all flex flex-col items-center justify-center text-center gap-3 h-32 ${selectedStores.includes(store.name)
                            ? 'border-pink-500 bg-pink-50 dark:bg-pink-900/20'
                            : 'border-gray-100 dark:border-gray-700 hover:border-gray-200 dark:hover:border-gray-600'
                            }`}
                    >
                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${selectedStores.includes(store.name)
                            ? 'bg-pink-500 border-pink-500'
                            : 'border-gray-300 dark:border-gray-600'
                            }`}>
                            {selectedStores.includes(store.name) && (
                                <Check className="w-4 h-4 text-white" />
                            )}
                        </div>
                        <span className={`text-sm font-medium transition-colors ${selectedStores.includes(store.name)
                            ? 'text-pink-600 dark:text-pink-400'
                            : 'text-gray-600 dark:text-gray-300'
                            }`}>
                            {store.name}
                        </span>
                    </button>
                ))}
            </div>

            {/* Save Button */}
            <div className="mt-8 flex items-center justify-end">
                <button
                    onClick={handleSavePreferences}
                    disabled={updatePreferredStoresMutation.isPending || (selectedStores.length === 0 && currentPreferredStores.length === 0) || isApplied}
                    className={`flex items-center gap-2 px-8 py-3 rounded-lg font-medium transition-colors ${isApplied
                        ? 'bg-green-600 text-white cursor-default'
                        : 'bg-pink-600 hover:bg-pink-700 text-white disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg'
                        }`}
                >
                    {updatePreferredStoresMutation.isPending ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            Saving...
                        </>
                    ) : isApplied ? (
                        <>
                            <Check className="w-4 h-4" />
                            Preferences Saved
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-4 h-4" />
                            Save Preferences
                        </>
                    )}
                </button>
            </div>

            {/* Error Handling */}
            {updatePreferredStoresMutation.isError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                        Failed to save preferences: {updatePreferredStoresMutation.error?.message}
                    </p>
                </div>
            )}
        </div>
    );
}
