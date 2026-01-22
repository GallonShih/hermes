import React, { useState, useEffect, useCallback, useMemo } from 'react';
import WordCloud from 'react-d3-cloud';
import { useWordFrequency } from '../../hooks/useWordFrequency';
import { useWordlists } from '../../hooks/useWordlists';

function WordCloudPanel({ startTime, endTime, hasTimeFilter }) {
    // Hooks
    const { wordData, stats, loading, error, getWordFrequency } = useWordFrequency();
    const { savedWordlists, refreshWordlists, saveWordlist, updateWordlist, removeWordlist, getWordlist } = useWordlists();

    // Local State
    const [excludeWords, setExcludeWords] = useState([]);
    const [newExcludeWord, setNewExcludeWord] = useState('');
    const [selectedWordlistId, setSelectedWordlistId] = useState(null);
    const [isModified, setIsModified] = useState(false);

    const [showSaveModal, setShowSaveModal] = useState(false);
    const [saveAsName, setSaveAsName] = useState('');
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState('');

    const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1000000));
    const [seedInput, setSeedInput] = useState('');

    // Fetch frequency on change
    useEffect(() => {
        getWordFrequency({ startTime, endTime, excludeWords });
    }, [startTime, endTime, excludeWords, getWordFrequency]);

    // Handle exclude
    const handleAddExcludeWord = () => {
        const word = newExcludeWord.trim();
        if (word && !excludeWords.includes(word)) {
            setExcludeWords([...excludeWords, word]);
            setNewExcludeWord('');
            setIsModified(true);
        }
    };

    const handleRemoveExcludeWord = (word) => {
        setExcludeWords(excludeWords.filter(w => w !== word));
        setIsModified(true);
    };

    // Wordlist handling
    const handleLoadWordlist = async (wordlistId) => {
        if (!wordlistId) {
            setSelectedWordlistId(null);
            setExcludeWords([]);
            setIsModified(false);
            return;
        }
        try {
            const data = await getWordlist(wordlistId);
            setExcludeWords(data.words || []);
            setSelectedWordlistId(wordlistId);
            setIsModified(false);
        } catch (err) {
            console.error(err);
        }
    };

    const handleSaveNew = async () => {
        if (!saveAsName.trim()) { setSaveError('請輸入名稱'); return; }
        setSaving(true);
        try {
            const data = await saveWordlist(saveAsName.trim(), excludeWords);
            setSelectedWordlistId(data.id);
            setIsModified(false);
            setShowSaveModal(false);
            setSaveAsName('');
        } catch (err) {
            setSaveError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleUpdateWordlist = async () => {
        if (!selectedWordlistId) return;
        try {
            await updateWordlist(selectedWordlistId, excludeWords);
            setIsModified(false);
        } catch (err) {
            console.error(err);
        }
    };

    const handleDeleteWordlist = async () => {
        if (!selectedWordlistId || !window.confirm('確定要刪除？')) return;
        try {
            await removeWordlist(selectedWordlistId);
            setSelectedWordlistId(null);
            setExcludeWords([]);
            setIsModified(false);
        } catch (err) {
            console.error(err);
        }
    };

    // Visualization helpers
    // Deterministic data sorting
    const displayWords = useMemo(() => {
        if (!wordData) return [];
        return [...wordData].sort((a, b) => {
            if (b.value !== a.value) return b.value - a.value;
            return a.text.localeCompare(b.text);
        }).map(w => ({ text: w.text, value: w.value }));
    }, [wordData]);

    const fontSize = useCallback((word) => {
        if (!displayWords.length) return 12;
        const maxCount = Math.max(...displayWords.map(w => w.value));
        const minCount = Math.min(...displayWords.map(w => w.value));
        const range = maxCount - minCount || 1;
        const normalized = (word.value - minCount) / range;
        return Math.floor(12 + normalized * 48);
    }, [displayWords]);

    // Simple string hash for deterministic attributes based on text + seed
    const getWordHash = useCallback((text) => {
        let hash = 0;
        const str = text + seed.toString();
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return Math.abs(hash);
    }, [seed]);

    const seededRandom = useMemo(() => {
        let a = seed;
        // Adding displayWords to dependency to ensure PRNG resets when data changes
        return () => {
            let t = a += 0x6D2B79F5;
            t = Math.imul(t ^ t >>> 15, t | 1);
            t ^= t + Math.imul(t ^ t >>> 7, t | 61);
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        };
    }, [seed, displayWords]);

    const colorPalette = useMemo(() => [
        '#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE',
        '#3BA272', '#FC8452', '#9A60B4', '#EA7CCC', '#48B8D0',
        '#6E7074', '#546570', '#C23531', '#2F4554', '#61A0A8'
    ], []);

    const fill = useCallback((word) => {
        // Color depends only on word text and seed, not index
        const idx = getWordHash(word.text) % colorPalette.length;
        return colorPalette[idx];
    }, [getWordHash, colorPalette]);

    const rotate = useCallback((word) => {
        // Rotation depends only on word text and seed, not index
        // Use hash to decide 0 or 90
        return (getWordHash(word.text) % 2 === 0) ? 90 : 0;
    }, [getWordHash]);

    const currentWordlistName = useMemo(() => savedWordlists.find(w => w.id === selectedWordlistId)?.name, [selectedWordlistId, savedWordlists]);

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mt-6">
            {showSaveModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
                        <h3 className="text-lg font-bold mb-4">儲存排除詞彙清單</h3>
                        <input type="text" value={saveAsName} onChange={(e) => setSaveAsName(e.target.value)} placeholder="清單名稱" className="w-full border p-2 mb-2 rounded" />
                        {saveError && <div className="text-red-500 text-sm mb-2">{saveError}</div>}
                        <div className="flex justify-end gap-2 mt-4">
                            <button onClick={() => setShowSaveModal(false)} className="px-4 py-2 text-gray-600">取消</button>
                            <button onClick={handleSaveNew} disabled={saving} className="bg-blue-600 text-white px-4 py-2 rounded">儲存</button>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex flex-wrap justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">☁️ 文字雲</h2>
                <div className="flex gap-2">
                    <button onClick={() => setSeed(Math.floor(Math.random() * 1000000))} className="bg-purple-600 text-white px-4 py-2 rounded text-sm hover:bg-purple-700">🔄 重繪</button>
                    <button onClick={() => getWordFrequency({ startTime, endTime, excludeWords })} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">🔃 重新載入</button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
                <div className="lg:col-span-3 border border-gray-200 rounded-lg bg-gray-50 relative min-h-[400px]">
                    {loading && <div className="absolute inset-0 bg-white bg-opacity-60 flex items-center justify-center z-10">載入中...</div>}
                    {wordData.length > 0 ? (
                        <WordCloud key={seed} data={displayWords} width={600} height={400} fontSize={fontSize} rotate={rotate} fill={fill} padding={2} random={seededRandom} />
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-500">{error || '無資料'}</div>
                    )}
                </div>
                <div className="lg:col-span-1 border border-gray-200 rounded-lg bg-white p-3 max-h-[400px] overflow-y-auto">
                    <div className="text-sm font-semibold mb-2">📊 詞頻排行</div>
                    {displayWords.slice(0, 50).map((w, i) => (
                        <div key={w.text} className="flex justify-between text-sm hover:bg-gray-50 px-1 py-0.5 group">
                            <span style={{ color: fill(w) }}>{i + 1}. {w.text}</span>
                            <div className="flex items-center gap-1">
                                <span className="text-xs text-gray-500">{w.value}</span>
                                <button onClick={() => !excludeWords.includes(w.text) && setExcludeWords([...excludeWords, w.text])} className="opacity-0 group-hover:opacity-100 text-red-500">✕</button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                    <div className="text-sm">總訊息: {stats.total_messages.toLocaleString()} | 不重複詞: {stats.unique_words.toLocaleString()}</div>
                    <div className="flex gap-2 items-center">
                        <span className="text-sm">Seed: {seed}</span>
                        <input type="number" value={seedInput} onChange={(e) => setSeedInput(e.target.value)} placeholder="Seed" className="border px-2 py-1 w-20 text-sm rounded" />
                        <button onClick={() => setSeed(parseInt(seedInput) || seed)} className="bg-gray-200 px-2 py-1 text-sm rounded">Apply</button>
                    </div>
                </div>
                <div>
                    <div className="flex justify-between mb-2 text-sm">
                        <span>排除詞彙 {currentWordlistName && `(${currentWordlistName}${isModified ? '*' : ''})`}</span>
                        <div className="flex gap-1">
                            <select value={selectedWordlistId || ''} onChange={(e) => handleLoadWordlist(e.target.value ? parseInt(e.target.value) : null)} className="border rounded px-1 text-sm">
                                <option value="">⛔️ 無</option>
                                {savedWordlists.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                            </select>
                            {selectedWordlistId && isModified && <button onClick={handleUpdateWordlist} className="bg-green-500 text-white px-2 rounded text-xs">更新</button>}
                            <button onClick={() => setShowSaveModal(true)} className="bg-blue-500 text-white px-2 rounded text-xs">另存</button>
                            {selectedWordlistId && <button onClick={handleDeleteWordlist} className="text-red-600 border border-red-200 px-2 rounded text-xs">刪除</button>}
                        </div>
                    </div>
                    <div className="flex gap-2 mb-2">
                        <input type="text" value={newExcludeWord} onChange={(e) => setNewExcludeWord(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleAddExcludeWord()} className="border rounded px-2 py-1 flex-1 text-sm" placeholder="新增..." />
                        <button onClick={handleAddExcludeWord} className="bg-red-500 text-white px-3 rounded text-sm">+</button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {excludeWords.map(w => (
                            <span key={w} className="bg-red-100 text-red-800 px-2 py-1 rounded text-sm flex items-center gap-1">{w} <button onClick={() => handleRemoveExcludeWord(w)} className="font-bold">✕</button></span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default React.memo(WordCloudPanel);
