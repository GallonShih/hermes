import { useState, useCallback } from 'react';
import { fetchWordFrequency } from '../api/wordcloud';

export const useWordFrequency = () => {
    const [wordData, setWordData] = useState([]);
    const [stats, setStats] = useState({ total_messages: 0, unique_words: 0 });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const getWordFrequency = useCallback(async ({ startTime, endTime, limit = 100, excludeWords }) => {
        setLoading(true);
        setError(null);
        try {
            let effectiveStartTime = startTime;
            if (!effectiveStartTime && !endTime) {
                effectiveStartTime = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
            }

            const data = await fetchWordFrequency({
                startTime: effectiveStartTime,
                endTime,
                limit,
                excludeWords
            });

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
    }, []);

    return {
        wordData,
        stats,
        loading,
        error,
        getWordFrequency
    };
};
