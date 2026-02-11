import React, { useState, useEffect, useCallback } from 'react';
import {
    SparklesIcon,
    PlusIcon,
    PencilIcon,
    TrashIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    ArrowPathIcon,
    DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import {
    fetchPromptTemplates,
    createPromptTemplate,
    updatePromptTemplate,
    deletePromptTemplate,
    activatePromptTemplate,
} from '../../api/etl';

const PromptTemplatesManager = () => {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [editingTemplate, setEditingTemplate] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        template: '',
    });

    const loadTemplates = useCallback(async () => {
        try {
            setLoading(true);
            const data = await fetchPromptTemplates();
            setTemplates(data.templates || []);
            setError(null);
        } catch (err) {
            console.error('Error loading templates:', err);
            setError('Failed to load templates');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadTemplates();
    }, [loadTemplates]);

    const handleCreate = () => {
        setEditingTemplate(null);
        setFormData({
            name: '',
            description: '',
            template: '',
        });
        setShowModal(true);
    };

    const handleEdit = (template) => {
        setEditingTemplate(template);
        setFormData({
            name: template.name,
            description: template.description || '',
            template: template.template,
        });
        setShowModal(true);
    };

    const handleSave = async () => {
        try {
            if (editingTemplate) {
                await updatePromptTemplate(editingTemplate.id, formData);
                setSuccessMessage('Template updated successfully');
            } else {
                await createPromptTemplate(formData);
                setSuccessMessage('Template created successfully');
            }
            setShowModal(false);
            await loadTemplates();
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error('Error saving template:', err);
            setError('Failed to save template');
        }
    };

    const handleDelete = async (templateId) => {
        if (!window.confirm('確定要刪除這個範本嗎？')) return;

        try {
            await deletePromptTemplate(templateId);
            setSuccessMessage('Template deleted successfully');
            await loadTemplates();
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error('Error deleting template:', err);
            setError('Failed to delete template. Make sure it is not active.');
        }
    };

    const handleActivate = async (templateId) => {
        try {
            await activatePromptTemplate(templateId);
            setSuccessMessage('Template activated successfully');
            await loadTemplates();
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error('Error activating template:', err);
            setError('Failed to activate template');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <ArrowPathIcon className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Alerts */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-5 h-5" />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto">&times;</button>
                </div>
            )}
            {successMessage && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
                    <CheckCircleIcon className="w-5 h-5" />
                    {successMessage}
                </div>
            )}

            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                        <SparklesIcon className="w-6 h-6 text-purple-500" />
                        AI Prompt Templates
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                        管理 AI 詞彙發現的提示詞範本，支援變數：{'{{messages_text}}'}, {'{{replace_examples}}'}, {'{{replace_count}}'}, {'{{special_examples}}'}, {'{{special_count}}'}
                    </p>
                </div>
                <button
                    onClick={handleCreate}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                    <PlusIcon className="w-5 h-5" />
                    建立新範本
                </button>
            </div>

            {/* Templates List */}
            <div className="space-y-3">
                {templates.map((template) => (
                    <div
                        key={template.id}
                        className={`bg-white border rounded-lg p-4 transition-all ${template.is_active
                            ? 'border-green-500 shadow-md'
                            : 'border-gray-200 hover:shadow-sm'
                            }`}
                    >
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        {template.name}
                                    </h3>
                                    {template.is_active && (
                                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-full font-medium">
                                            啟用中
                                        </span>
                                    )}
                                </div>
                                {template.description && (
                                    <p className="text-sm text-gray-600 mt-1">
                                        {template.description}
                                    </p>
                                )}
                                <div className="mt-2 text-xs text-gray-400">
                                    建立於：{new Date(template.created_at).toLocaleString()}
                                </div>
                            </div>

                            <div className="flex items-center gap-2 sm:ml-4">
                                {!template.is_active && (
                                    <button
                                        onClick={() => handleActivate(template.id)}
                                        className="px-3 py-1.5 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                    >
                                        啟用
                                    </button>
                                )}
                                <button
                                    onClick={() => handleEdit(template)}
                                    className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                    title="編輯"
                                >
                                    <PencilIcon className="w-5 h-5" />
                                </button>
                                {!template.is_active && (
                                    <button
                                        onClick={() => handleDelete(template.id)}
                                        className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                        title="刪除"
                                    >
                                        <TrashIcon className="w-5 h-5" />
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Template Preview */}
                        <details className="mt-3">
                            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                                查看範本內容
                            </summary>
                            <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                                {template.template}
                            </pre>
                        </details>
                    </div>
                ))}
            </div>

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
                            <h3 className="text-lg font-semibold text-gray-900">
                                {editingTemplate ? '編輯範本' : '建立新範本'}
                            </h3>
                        </div>

                        <div className="p-6 space-y-4">
                            {/* Name */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    範本名稱 *
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="例如：Default Template"
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    描述
                                </label>
                                <input
                                    type="text"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="簡短描述這個範本的用途"
                                />
                            </div>

                            {/* Template */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    提示詞範本 *
                                </label>
                                <div className="mb-2 text-xs text-gray-500 bg-blue-50 border border-blue-200 rounded p-2">
                                    💡 可用變數：<code className="bg-blue-100 px-1 rounded">{'{{messages_text}}'}</code>,{' '}
                                    <code className="bg-blue-100 px-1 rounded">{'{{replace_examples}}'}</code>,{' '}
                                    <code className="bg-blue-100 px-1 rounded">{'{{replace_count}}'}</code>,{' '}
                                    <code className="bg-blue-100 px-1 rounded">{'{{special_examples}}'}</code>,{' '}
                                    <code className="bg-blue-100 px-1 rounded">{'{{special_count}}'}</code>
                                </div>
                                <textarea
                                    value={formData.template}
                                    onChange={(e) => setFormData({ ...formData, template: e.target.value })}
                                    rows={20}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                                    placeholder="輸入完整的提示詞範本..."
                                />
                            </div>
                        </div>

                        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={!formData.name || !formData.template}
                                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                儲存
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PromptTemplatesManager;
