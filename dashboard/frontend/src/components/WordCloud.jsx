import React, { useState, useEffect, useCallback, useMemo } from 'react';
import WordCloud from 'react-d3-cloud';

const API_BASE_URL = 'http://localhost:8000';

function WordCloudPanel({ startTime, endTime, hasTimeFilter }) {
    const [wordData, setWordData] = useState([]);
    const [stats, setStats] = useState({ total_messages: 0, unique_words: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Exclusion words management
    const [excludeWords, setExcludeWords] = useState([]);
    const [newExcludeWord, setNewExcludeWord] = useState('');

    // Saved wordlists management
    const [savedWordlists, setSavedWordlists] = useState([]);
    const [selectedWordlistId, setSelectedWordlistId] = useState(null);
    const [isModified, setIsModified] = useState(false);
    const [loadingWordlists, setLoadingWordlists] = useState(false);

    // Save modal state
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [saveAsName, setSaveAsName] = useState('');
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState('');

    // Seed for reproducible layout
    const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1000000));
    const [seedInput, setSeedInput] = useState('');

    // Fetch saved wordlists from API
    const fetchSavedWordlists = useCallback(async () => {
        setLoadingWordlists(true);
        try {
            const res = await fetch(`${API_BASE_URL}/api/exclusion-wordlists`);
            if (res.ok) {
                const data = await res.json();
                setSavedWordlists(data);
            }
        } catch (err) {
            console.error('Failed to fetch saved wordlists', err);
        } finally {
            setLoadingWordlists(false);
        }
    }, []);

    // Load wordlists on mount
    useEffect(() => {
        fetchSavedWordlists();
    }, [fetchSavedWordlists]);

    const fetchWordFrequency = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            let url = `${API_BASE_URL}/api/wordcloud/word-frequency?limit=100`;

            let effectiveStartTime = startTime;
            if (!effectiveStartTime && !endTime) {
                effectiveStartTime = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
            }

            if (effectiveStartTime) {
                url += `&start_time=${encodeURIComponent(effectiveStartTime)}`;
            }
            if (endTime) {
                url += `&end_time=${encodeURIComponent(endTime)}`;
            }
            if (excludeWords.length > 0) {
                url += `&exclude_words=${encodeURIComponent(excludeWords.join(','))}`;
            }

            const res = await fetch(url);
            if (!res.ok) throw new Error(`API error: ${res.status}`);

            const data = await res.json();

            // Transform for react-d3-cloud
            const cloudData = data.words.map(w => ({
                text: w.word,
                value: w.count
            }));

            setWordData(cloudData);
            setStats({
                total_messages: data.total_messages,
                unique_words: data.unique_words
            });
        } catch (err) {
            console.error('Failed to fetch word frequency', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [startTime, endTime, excludeWords]);

    useEffect(() => {
        fetchWordFrequency();
    }, [fetchWordFrequency]);

    // Handle exclude word add
    const handleAddExcludeWord = () => {
        const word = newExcludeWord.trim();
        if (word && !excludeWords.includes(word)) {
            setExcludeWords([...excludeWords, word]);
            setNewExcludeWord('');
            setIsModified(true);
        }
    };

    // Handle exclude word remove
    const handleRemoveExcludeWord = (word) => {
        setExcludeWords(excludeWords.filter(w => w !== word));
        setIsModified(true);
    };

    // Load a saved wordlist
    const handleLoadWordlist = async (wordlistId) => {
        if (!wordlistId) {
            setSelectedWordlistId(null);
            setExcludeWords([]);
            setIsModified(false);
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/api/exclusion-wordlists/${wordlistId}`);
            if (res.ok) {
                const data = await res.json();
                setExcludeWords(data.words || []);
                setSelectedWordlistId(wordlistId);
                setIsModified(false);
            }
        } catch (err) {
            console.error('Failed to load wordlist', err);
        }
    };

    // Save new wordlist
    const handleSaveNew = async () => {
        const name = saveAsName.trim();
        if (!name) {
            setSaveError('請輸入名稱');
            return;
        }

        setSaving(true);
        setSaveError('');

        try {
            const res = await fetch(`${API_BASE_URL}/api/exclusion-wordlists`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, words: excludeWords })
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || '儲存失敗');
            }

            const data = await res.json();
            await fetchSavedWordlists();
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

    // Update existing wordlist
    const handleUpdateWordlist = async () => {
        if (!selectedWordlistId) return;

        try {
            const res = await fetch(`${API_BASE_URL}/api/exclusion-wordlists/${selectedWordlistId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ words: excludeWords })
            });

            if (res.ok) {
                await fetchSavedWordlists();
                setIsModified(false);
            }
        } catch (err) {
            console.error('Failed to update wordlist', err);
        }
    };

    // Delete wordlist
    const handleDeleteWordlist = async () => {
        if (!selectedWordlistId) return;
        if (!window.confirm('確定要刪除此清單？')) return;

        try {
            const res = await fetch(`${API_BASE_URL}/api/exclusion-wordlists/${selectedWordlistId}`, {
                method: 'DELETE'
            });

            if (res.ok) {
                await fetchSavedWordlists();
                setSelectedWordlistId(null);
                setExcludeWords([]);
                setIsModified(false);
            }
        } catch (err) {
            console.error('Failed to delete wordlist', err);
        }
    };

    // Random redraw with new seed
    const handleRandomRedraw = () => {
        const newSeed = Math.floor(Math.random() * 1000000);
        setSeed(newSeed);
        setSeedInput('');
    };

    // Apply seed from input
    const handleApplySeed = () => {
        const parsed = parseInt(seedInput, 10);
        if (!isNaN(parsed)) {
            setSeed(parsed);
        }
    };

    // Copy seed to clipboard
    const handleCopySeed = () => {
        navigator.clipboard.writeText(seed.toString());
    };

    // Font size scale function based on value
    const fontSize = useCallback((word) => {
        if (!wordData.length) return 12;
        const maxCount = Math.max(...wordData.map(w => w.value));
        const minCount = Math.min(...wordData.map(w => w.value));
        const range = maxCount - minCount || 1;
        const normalized = (word.value - minCount) / range;
        return Math.floor(12 + normalized * 48); // 12-60px range
    }, [wordData]);

    // Mulberry32 PRNG - a proper seeded random number generator
    const createSeededRandom = useCallback((seedValue) => {
        let a = seedValue;
        return () => {
            let t = a += 0x6D2B79F5;
            t = Math.imul(t ^ t >>> 15, t | 1);
            t ^= t + Math.imul(t ^ t >>> 7, t | 61);
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        };
    }, []);

    // Create a seeded random instance that resets each render with same seed
    const seededRandom = useMemo(() => {
        return createSeededRandom(seed);
    }, [seed, createSeededRandom]);

    // Color palette for word cloud
    const colorPalette = useMemo(() => [
        '#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE',
        '#3BA272', '#FC8452', '#9A60B4', '#EA7CCC', '#48B8D0',
        '#6E7074', '#546570', '#C23531', '#2F4554', '#61A0A8'
    ], []);

    // Seeded color function - each word gets consistent color based on seed
    const fill = useCallback((word, index) => {
        const rng = createSeededRandom(seed + index);
        const colorIndex = Math.floor(rng() * colorPalette.length);
        return colorPalette[colorIndex];
    }, [seed, createSeededRandom, colorPalette]);

    // Rotation function (0 or 90 degrees) - using seeded random
    const rotate = useCallback((word, index) => {
        const rng = createSeededRandom(seed + index + 1000);
        return rng() > 0.7 ? 90 : 0;
    }, [seed, createSeededRandom]);

    // Get current wordlist name
    const currentWordlistName = useMemo(() => {
        if (!selectedWordlistId) return null;
        const wl = savedWordlists.find(w => w.id === selectedWordlistId);
        return wl ? wl.name : null;
    }, [selectedWordlistId, savedWordlists]);

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mt-6">
            {/* Save Modal */}
            {showSaveModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
                        <h3 className="text-lg font-bold mb-4">儲存排除詞彙清單</h3>
                        <input
                            type="text"
                            value={saveAsName}
                            onChange={(e) => setSaveAsName(e.target.value)}
                            placeholder="輸入清單名稱..."
                            className="w-full border border-gray-300 rounded-md px-3 py-2 mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            autoFocus
                            onKeyPress={(e) => e.key === 'Enter' && handleSaveNew()}
                        />
                        {saveError && (
                            <div className="text-red-500 text-sm mb-2">{saveError}</div>
                        )}
                        <div className="flex justify-end gap-2 mt-4">
                            <button
                                onClick={() => { setShowSaveModal(false); setSaveAsName(''); setSaveError(''); }}
                                className="px-4 py-2 text-gray-600 hover:text-gray-800"
                                disabled={saving}
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSaveNew}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-semibold disabled:opacity-50"
                                disabled={saving}
                            >
                                {saving ? '儲存中...' : '儲存'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="flex flex-wrap justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">☁️ 文字雲</h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRandomRedraw}
                        className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md text-sm font-semibold shadow-md transition-all duration-200 hover:shadow-lg"
                    >
                        🔄 重繪
                    </button>
                    <button
                        onClick={fetchWordFrequency}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-semibold shadow-md transition-all duration-200 hover:shadow-lg"
                    >
                        🔃 重新載入
                    </button>
                </div>
            </div>

            {/* Word Cloud + Word List Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
                {/* Word Cloud Area - 3/4 width */}
                <div className="lg:col-span-3 border border-gray-200 rounded-lg bg-gray-50 relative" style={{ minHeight: '400px' }}>
                    {loading && wordData.length > 0 && (
                        <div className="absolute inset-0 bg-white bg-opacity-60 flex items-center justify-center z-10 transition-opacity duration-300 rounded-lg">
                            <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-blue-500"></div>
                        </div>
                    )}

                    {loading && wordData.length === 0 ? (
                        <div className="flex items-center justify-center h-[400px] text-gray-500">
                            載入中...
                        </div>
                    ) : error ? (
                        <div className="flex items-center justify-center h-[400px] text-red-500">
                            錯誤: {error}
                        </div>
                    ) : wordData.length === 0 ? (
                        <div className="flex items-center justify-center h-[400px] text-gray-500">
                            沒有資料。請確認 processed_chat_messages 表有資料。
                        </div>
                    ) : (
                        <WordCloud
                            key={seed}
                            data={wordData}
                            width={600}
                            height={400}
                            font="sans-serif"
                            fontWeight="bold"
                            fontSize={fontSize}
                            rotate={rotate}
                            fill={fill}
                            padding={2}
                            random={seededRandom}
                        />
                    )}
                </div>

                {/* Word List Panel - 1/4 width */}
                <div className="lg:col-span-1 border border-gray-200 rounded-lg bg-white p-3" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    <div className="text-sm font-semibold text-gray-700 mb-2 sticky top-0 bg-white pb-1 border-b">
                        📊 詞頻排行 ({wordData.length})
                    </div>
                    <div className="space-y-1">
                        {wordData.slice(0, 50).map((word, index) => (
                            <div
                                key={word.text}
                                className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-1 py-0.5 group"
                            >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <span className="text-gray-400 w-5 text-right flex-shrink-0">{index + 1}.</span>
                                    <span
                                        className="truncate font-medium"
                                        style={{ color: fill(word, index) }}
                                        title={word.text}
                                    >
                                        {word.text}
                                    </span>
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                    <span className="text-gray-500 text-xs">{word.value.toLocaleString()}</span>
                                    <button
                                        onClick={() => {
                                            if (!excludeWords.includes(word.text)) {
                                                setExcludeWords([...excludeWords, word.text]);
                                                setIsModified(true);
                                            }
                                        }}
                                        className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 text-xs px-1 transition-opacity"
                                        title="加入排除"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ))}
                        {wordData.length > 50 && (
                            <div className="text-xs text-gray-400 text-center pt-2">
                                顯示前 50 個詞
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Controls Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Left: Stats & Seed */}
                <div className="space-y-3">
                    {/* Stats */}
                    <div className="text-sm text-gray-600">
                        <span className="font-semibold">總訊息數:</span> {stats.total_messages.toLocaleString()} |{' '}
                        <span className="font-semibold">不重複詞:</span> {stats.unique_words.toLocaleString()}
                    </div>

                    {/* Seed controls */}
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-700">Seed:</span>
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">{seed}</code>
                        <button
                            onClick={handleCopySeed}
                            className="text-blue-600 hover:text-blue-800 text-sm underline"
                        >
                            複製
                        </button>
                    </div>

                    {/* Seed input */}
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            value={seedInput}
                            onChange={(e) => setSeedInput(e.target.value)}
                            placeholder="輸入 Seed..."
                            className="border border-gray-300 rounded-md px-3 py-1 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        />
                        <button
                            onClick={handleApplySeed}
                            className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded-md text-sm text-gray-700 font-medium transition-colors"
                        >
                            套用
                        </button>
                    </div>
                </div>

                {/* Right: Exclude words */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <div className="text-sm font-semibold text-gray-700">
                            排除詞彙
                            {currentWordlistName && (
                                <span className="ml-2 text-blue-600 font-normal">
                                    ({currentWordlistName}{isModified && ' - 已修改'})
                                </span>
                            )}
                        </div>
                        {/* Wordlist controls */}
                        <div className="flex items-center gap-1">
                            <select
                                value={selectedWordlistId || ''}
                                onChange={(e) => handleLoadWordlist(e.target.value ? parseInt(e.target.value) : null)}
                                className="border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                disabled={loadingWordlists}
                            >
                                <option value="">⛔️ 不使用清單 (清空)</option>
                                {savedWordlists.map(wl => (
                                    <option key={wl.id} value={wl.id}>{wl.name}</option>
                                ))}
                            </select>
                            {selectedWordlistId && isModified && (
                                <button
                                    onClick={handleUpdateWordlist}
                                    className="bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded text-xs font-medium"
                                    title="更新清單"
                                >
                                    更新
                                </button>
                            )}
                            <button
                                onClick={() => setShowSaveModal(true)}
                                className="bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs font-medium"
                                title="另存新清單"
                            >
                                💾 另存
                            </button>
                            {selectedWordlistId && (
                                <button
                                    onClick={handleDeleteWordlist}
                                    className="bg-red-100 hover:bg-red-200 text-red-600 border border-red-200 px-2 py-1 rounded text-xs font-medium flex items-center gap-1"
                                    title="刪除此清單"
                                >
                                    🗑️ 刪除
                                </button>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                        <input
                            type="text"
                            value={newExcludeWord}
                            onChange={(e) => setNewExcludeWord(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleAddExcludeWord()}
                            placeholder="新增排除詞..."
                            className="border border-gray-300 rounded-md px-3 py-1 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-red-500"
                        />
                        <button
                            onClick={handleAddExcludeWord}
                            className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-md text-sm font-medium transition-colors"
                        >
                            + 加入
                        </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {excludeWords.map((word) => (
                            <span
                                key={word}
                                className="inline-flex items-center bg-red-100 text-red-800 px-2 py-1 rounded text-sm"
                            >
                                {word}
                                <button
                                    onClick={() => handleRemoveExcludeWord(word)}
                                    className="ml-1 text-red-600 hover:text-red-800 font-bold"
                                >
                                    ✕
                                </button>
                            </span>
                        ))}
                        {excludeWords.length === 0 && (
                            <span className="text-sm text-gray-400">尚無排除詞</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Time filter indicator */}
            {hasTimeFilter && (
                <div className="mt-4 text-sm text-blue-600">
                    ℹ️ 已套用時間篩選
                </div>
            )}
        </div>
    );
}

export default WordCloudPanel;
