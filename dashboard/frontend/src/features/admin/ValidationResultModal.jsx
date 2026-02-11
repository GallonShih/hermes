import React, { useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';

const ValidationResultModal = ({ isOpen, isValid, conflicts, warnings = [], onClose }) => {
    const closeButtonRef = useRef(null);

    // Focus management and keyboard handling
    useEffect(() => {
        if (isOpen) {
            closeButtonRef.current?.focus();

            const handleKeyDown = (e) => {
                if (e.key === 'Escape') {
                    onClose();
                }
            };

            document.addEventListener('keydown', handleKeyDown);
            return () => document.removeEventListener('keydown', handleKeyDown);
        }
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const hasWarnings = warnings && warnings.length > 0;

    return ReactDOM.createPortal(
        <div
            className="fixed inset-0 z-50 glass-modal-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="validation-result-title"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999
            }}
        >
            <div
                className="glass-modal rounded-2xl overflow-hidden"
                style={{
                    width: 'calc(100% - 2rem)',
                    maxWidth: '42rem',
                    maxHeight: 'calc(100vh - 4rem)'
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6">
                    {/* Header */}
                    <div className="flex items-center mb-4">
                        {isValid ? (
                            <>
                                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mr-4" aria-hidden="true">
                                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <h3 id="validation-result-title" className="text-xl font-bold text-green-700">驗證通過</h3>
                            </>
                        ) : (
                            <>
                                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mr-4" aria-hidden="true">
                                    <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </div>
                                <h3 id="validation-result-title" className="text-xl font-bold text-red-700">驗證失敗</h3>
                            </>
                        )}
                    </div>

                    {/* Content */}
                    <div className="mb-6">
                        {isValid ? (
                            <div>
                                <p className="text-gray-700 mb-3">未發現衝突，此詞彙可以安全批准。</p>

                                {/* Warnings Section */}
                                {hasWarnings && (
                                    <div className="mt-4">
                                        <p className="text-gray-700 mb-2 font-semibold flex items-center">
                                            <svg className="w-5 h-5 text-yellow-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                            </svg>
                                            但有以下提示：
                                        </p>
                                        <div className="bg-yellow-50 border border-yellow-200 rounded p-4 max-h-64 overflow-y-auto" role="alert">
                                            <ul className="space-y-2" aria-label="警告清單">
                                                {warnings.map((warning, index) => (
                                                    <li key={index} className="text-sm flex items-start">
                                                        <span className="text-yellow-600 mr-2 mt-0.5">⚠️</span>
                                                        <div className="flex-1">
                                                            <span className="font-semibold text-yellow-800">
                                                                {warning.type}:
                                                            </span>
                                                            <span className="text-gray-700 ml-2">
                                                                {warning.message}
                                                            </span>
                                                        </div>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <p className="text-sm text-gray-600 mt-2 italic flex items-center">
                                            <svg className="w-4 h-4 text-blue-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                            </svg>
                                            這些警告不會阻止批准，但請確認是否符合預期
                                        </p>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div>
                                <p className="text-gray-700 mb-3 font-semibold">發現以下衝突：</p>
                                <div className="bg-red-50 border border-red-200 rounded p-4 max-h-96 overflow-y-auto" role="alert">
                                    {conflicts && conflicts.length > 0 ? (
                                        <ul className="space-y-2" aria-label="衝突清單">
                                            {conflicts.map((conflict, index) => (
                                                <li key={index} className="text-sm">
                                                    <span className="font-semibold text-red-700">
                                                        {conflict.type}:
                                                    </span>
                                                    <span className="text-gray-800 ml-2">
                                                        {conflict.message}
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-gray-600">未提供詳細資訊</p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex justify-end">
                        <button
                            ref={closeButtonRef}
                            onClick={onClose}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                        >
                            確定
                        </button>
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default ValidationResultModal;
