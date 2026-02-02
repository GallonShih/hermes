import React from 'react';

/**
 * Base skeleton element with shimmer animation
 */
const Skeleton = ({ className = '', variant = 'rectangular' }) => {
    const baseClasses = 'animate-pulse bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:200%_100%]';

    const variantClasses = {
        rectangular: 'rounded-lg',
        circular: 'rounded-full',
        text: 'rounded h-4',
    };

    return (
        <div
            className={`${baseClasses} ${variantClasses[variant] || variantClasses.rectangular} ${className}`}
            aria-hidden="true"
        />
    );
};

/**
 * Skeleton for text content
 */
export const SkeletonText = ({ lines = 3, className = '' }) => {
    return (
        <div className={`space-y-3 ${className}`}>
            {Array.from({ length: lines }).map((_, i) => (
                <Skeleton
                    key={i}
                    variant="text"
                    className={`h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
                />
            ))}
        </div>
    );
};

/**
 * Skeleton for stat cards
 */
export const SkeletonStatCard = ({ className = '' }) => {
    return (
        <div className={`glass-card rounded-2xl p-6 ${className}`}>
            <Skeleton className="h-5 w-32 mb-4" />
            <Skeleton className="h-10 w-24 mb-2" />
            <Skeleton variant="text" className="h-3 w-20" />
        </div>
    );
};

/**
 * Skeleton for table rows
 */
export const SkeletonTableRow = ({ columns = 4 }) => {
    return (
        <div className="flex items-center gap-4 py-3 border-b border-gray-100">
            {Array.from({ length: columns }).map((_, i) => (
                <Skeleton
                    key={i}
                    className={`h-5 ${i === 0 ? 'w-20' : 'flex-1'}`}
                />
            ))}
        </div>
    );
};

/**
 * Skeleton for table
 */
export const SkeletonTable = ({ rows = 5, columns = 4 }) => {
    return (
        <div>
            {/* Header */}
            <div className="flex items-center gap-4 py-3 border-b-2 border-gray-200 mb-2">
                {Array.from({ length: columns }).map((_, i) => (
                    <Skeleton key={i} className="h-4 flex-1" />
                ))}
            </div>
            {/* Rows */}
            {Array.from({ length: rows }).map((_, i) => (
                <SkeletonTableRow key={i} columns={columns} />
            ))}
        </div>
    );
};

/**
 * Skeleton for word cloud
 */
export const SkeletonWordCloud = ({ className = '' }) => {
    const sizes = ['w-16 h-6', 'w-24 h-8', 'w-12 h-5', 'w-20 h-7', 'w-14 h-5', 'w-28 h-9', 'w-10 h-4', 'w-18 h-6'];

    return (
        <div className={`flex flex-wrap gap-3 items-center justify-center p-8 ${className}`}>
            {Array.from({ length: 15 }).map((_, i) => (
                <Skeleton
                    key={i}
                    className={`${sizes[i % sizes.length]} rounded-full`}
                />
            ))}
        </div>
    );
};

/**
 * Skeleton for chart
 */
export const SkeletonChart = ({ className = '' }) => {
    return (
        <div className={`${className}`}>
            {/* Y-axis labels */}
            <div className="flex h-full">
                <div className="flex flex-col justify-between py-4 pr-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <Skeleton key={i} className="w-8 h-3" />
                    ))}
                </div>
                {/* Chart area */}
                <div className="flex-1 flex items-end justify-around gap-2 pb-8 border-l border-b border-gray-200">
                    {Array.from({ length: 12 }).map((_, i) => (
                        <Skeleton
                            key={i}
                            className="w-6 rounded-t"
                            style={{ height: `${30 + Math.random() * 60}%` }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

/**
 * Skeleton for list items
 */
export const SkeletonListItem = ({ hasAvatar = false }) => {
    return (
        <div className="flex items-center gap-3 py-3">
            {hasAvatar && <Skeleton variant="circular" className="w-10 h-10 flex-shrink-0" />}
            <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
            </div>
        </div>
    );
};

/**
 * Skeleton for message list
 */
export const SkeletonMessageList = ({ count = 5 }) => {
    return (
        <div className="space-y-1">
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="flex items-start gap-3 py-2 px-3">
                    <Skeleton className="w-16 h-4 flex-shrink-0" />
                    <Skeleton className="w-20 h-4 flex-shrink-0" />
                    <Skeleton className={`h-4 flex-1 ${i % 3 === 0 ? 'w-full' : i % 3 === 1 ? 'w-3/4' : 'w-1/2'}`} />
                </div>
            ))}
        </div>
    );
};

export default Skeleton;
