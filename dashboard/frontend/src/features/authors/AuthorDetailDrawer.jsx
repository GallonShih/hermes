import React, { useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import AuthorDetailContent from './AuthorDetailContent';

const AuthorDetailDrawer = ({
    isOpen,
    onClose,
    authorId,
    initialStartTime = null,
    initialEndTime = null,
}) => {
    useEffect(() => {
        if (!isOpen) return;
        const handleEscape = (event) => {
            if (event.key === 'Escape') onClose();
        };

        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 bg-black/40"
            onClick={(event) => {
                if (event.target === event.currentTarget) onClose();
            }}
        >
            <div className="absolute right-0 top-0 h-full w-full sm:w-[680px] bg-white shadow-2xl overflow-y-auto">
                <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                    <h2 className="text-base font-semibold text-gray-800">Author Detail</h2>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-1.5 rounded hover:bg-gray-100"
                        aria-label="Close"
                    >
                        <XMarkIcon className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <div className="p-4">
                    <AuthorDetailContent
                        authorId={authorId}
                        initialStartTime={initialStartTime}
                        initialEndTime={initialEndTime}
                        showOpenInNewPage
                    />
                </div>
            </div>
        </div>
    );
};

export default AuthorDetailDrawer;
