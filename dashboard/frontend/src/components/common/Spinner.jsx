import React from 'react';

/**
 * Unified Spinner component for loading states
 *
 * @param {string} size - 'sm' | 'md' | 'lg' | 'xl' (default: 'md')
 * @param {string} color - 'primary' | 'white' | 'gray' (default: 'primary')
 * @param {string} className - Additional CSS classes
 */
const Spinner = ({ size = 'md', color = 'primary', className = '' }) => {
    const sizeClasses = {
        sm: 'w-4 h-4 border-2',
        md: 'w-8 h-8 border-3',
        lg: 'w-12 h-12 border-4',
        xl: 'w-16 h-16 border-4',
    };

    const colorClasses = {
        primary: 'border-indigo-200 border-t-indigo-600',
        white: 'border-white/30 border-t-white',
        gray: 'border-gray-200 border-t-gray-600',
        green: 'border-green-200 border-t-green-600',
        blue: 'border-blue-200 border-t-blue-600',
    };

    return (
        <div
            className={`
                ${sizeClasses[size] || sizeClasses.md}
                ${colorClasses[color] || colorClasses.primary}
                rounded-full animate-spin
                ${className}
            `}
            role="status"
            aria-label="載入中"
        >
            <span className="sr-only">載入中...</span>
        </div>
    );
};

/**
 * Full-page or container loading overlay
 */
export const LoadingOverlay = ({ message = '載入中...', transparent = false }) => {
    return (
        <div className={`absolute inset-0 flex flex-col items-center justify-center z-10 ${transparent ? 'bg-white/60' : 'bg-white/80'} backdrop-blur-sm rounded-2xl`}>
            <Spinner size="lg" />
            {message && (
                <p className="mt-4 text-gray-600 font-medium">{message}</p>
            )}
        </div>
    );
};

/**
 * Inline loading indicator with text
 */
export const LoadingText = ({ text = '載入中...', size = 'sm' }) => {
    return (
        <div className="flex items-center gap-2 text-gray-500">
            <Spinner size={size} color="gray" />
            <span className="text-sm">{text}</span>
        </div>
    );
};

/**
 * Card/Panel loading state
 */
export const LoadingCard = ({ height = 'h-64', message = '載入中...' }) => {
    return (
        <div className={`glass-card rounded-2xl ${height} flex flex-col items-center justify-center`}>
            <Spinner size="lg" />
            {message && (
                <p className="mt-4 text-gray-500">{message}</p>
            )}
        </div>
    );
};

export default Spinner;
