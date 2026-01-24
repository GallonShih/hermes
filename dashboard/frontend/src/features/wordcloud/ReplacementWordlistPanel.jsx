import React, { useState, useEffect, useCallback } from 'react';
import { useReplacementWordlists } from '../../hooks/useReplacementWordlists';

const ReplacementWordlistPanel = ({ selectedId, onSelect, onUpdate, rules, onRulesChange }) => {
    // Hooks
    const {
        savedWordlists,
        loading, // loading list of wordlists
        saveWordlist,
        updateWordlist,
        removeWordlist
    } = useReplacementWordlists();

    const [newSource, setNewSource] = useState('');
    const [newTarget, setNewTarget] = useState('');

    // UI state
    const [isModified, setIsModified] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newListName, setNewListName] = useState('');
    const [createError, setCreateError] = useState('');

    // Reset modified state when list selection changes
    useEffect(() => {
        setIsModified(false);
    }, [selectedId]);

    // Handlers
    const handleAddRule = () => {
        if (!newSource.trim() || !newTarget.trim()) return;

        // Remove existing rule for same source if any (to avoid duplicates)
        const filtered = rules.filter(r => r.source !== newSource.trim());
        const newRules = [...filtered, { source: newSource.trim(), target: newTarget.trim() }];

        onRulesChange(newRules);
        setNewSource('');
        setNewTarget('');
        setIsModified(true);
    };

    const handleRemoveRule = (source) => {
        const newRules = rules.filter(r => r.source !== source);
        onRulesChange(newRules);
        setIsModified(true);
    };

    const handleSaveChanges = async () => {
        if (!selectedId) return;
        try {
            await updateWordlist(selectedId, rules);
            setIsModified(false);
            if (onUpdate) onUpdate();
        } catch (err) {
            console.error(err);
        }
    };

    const handleCreateNew = async () => {
        if (!newListName.trim()) {
            setCreateError('請輸入名稱');
            return;
        }
        try {
            const data = await saveWordlist(newListName.trim(), rules);
            setShowCreateModal(false);
            setNewListName('');
            setCreateError('');
            setIsModified(false);
            if (onSelect) onSelect(data.id);
        } catch (err) {
            setCreateError(err.message);
        }
    };

    const handleDeleteList = async () => {
        if (!selectedId || !window.confirm('確定要刪除此取代清單？')) return;
        try {
            await removeWordlist(selectedId);
            if (onSelect) onSelect(null);
        } catch (err) {
            console.error(err);
        }
    };

    const currentListName = savedWordlists.find(w => w.id === selectedId)?.name;

    return (
        <div className="bg-white p-4 rounded-lg border border-gray-200 mt-4">
            {/* Header / Selector */}
            <div className="flex flex-wrap justify-between items-center mb-4 gap-2">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-700">🔀 取代規則</span>
                    {currentListName && <span className="text-sm text-gray-600">({currentListName}{isModified ? '*' : ''})</span>}
                </div>

                <div className="flex gap-2">
                    <select
                        value={selectedId || ''}
                        onChange={(e) => onSelect(e.target.value ? parseInt(e.target.value) : null)}
                        className="border rounded px-2 py-1 text-sm max-w-[150px]"
                    >
                        <option value="">⛔️ 無</option>
                        {savedWordlists.map(w => (
                            <option key={w.id} value={w.id}>{w.name}</option>
                        ))}
                    </select>

                    {selectedId ? (
                        <>
                            {isModified && (
                                <button
                                    onClick={handleSaveChanges}
                                    className="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600"
                                >
                                    儲存變更
                                </button>
                            )}
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600"
                            >
                                另存
                            </button>
                            <button
                                onClick={handleDeleteList}
                                className="text-red-600 border border-red-200 px-2 py-1 rounded text-xs hover:bg-red-50"
                            >
                                刪除
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600"
                            disabled={rules.length === 0}
                        >
                            儲存為新清單
                        </button>
                    )}
                </div>
            </div>

            {/* Editor Area */}
            <div className="space-y-3">
                {/* Input Row */}
                <div className="flex gap-2 items-center">
                    <input
                        type="text"
                        value={newSource}
                        onChange={(e) => setNewSource(e.target.value)}
                        placeholder="原始詞 (如: 酥)"
                        className="border rounded px-2 py-1 text-sm flex-1"
                    />
                    <span className="text-gray-400">➜</span>
                    <input
                        type="text"
                        value={newTarget}
                        onChange={(e) => setNewTarget(e.target.value)}
                        placeholder="取代為 (如: 方塊酥)"
                        className="border rounded px-2 py-1 text-sm flex-1"
                        onKeyPress={(e) => e.key === 'Enter' && handleAddRule()}
                    />
                    <button
                        onClick={handleAddRule}
                        disabled={!newSource.trim() || !newTarget.trim()}
                        className="bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
                    >
                        +
                    </button>
                </div>

                {/* Rules List */}
                <div className="bg-gray-50 rounded p-2 max-h-[150px] overflow-y-auto border border-gray-100 flex flex-wrap gap-2">
                    {rules.length === 0 && <div className="text-gray-400 text-xs w-full text-center py-2">尚無取代規則</div>}
                    {rules.map((rule, idx) => (
                        <div key={`${rule.source}-${idx}`} className="bg-white border rounded px-2 py-1 text-sm flex items-center gap-2 shadow-sm">
                            <span className="text-gray-600">{rule.source}</span>
                            <span className="text-xs text-purple-400">➜</span>
                            <span className="font-medium text-gray-800">{rule.target}</span>
                            <button
                                onClick={() => handleRemoveRule(rule.source)}
                                className="text-red-400 hover:text-red-600 ml-1"
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-80 shadow-xl">
                        <h3 className="text-lg font-bold mb-4">建立取代清單</h3>
                        <input
                            type="text"
                            value={newListName}
                            onChange={(e) => setNewListName(e.target.value)}
                            placeholder="清單名稱"
                            className="w-full border p-2 mb-2 rounded"
                            autoFocus
                        />
                        {createError && <div className="text-red-500 text-sm mb-2">{createError}</div>}
                        <div className="flex justify-end gap-2 mt-4">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleCreateNew}
                                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                            >
                                建立
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReplacementWordlistPanel;
