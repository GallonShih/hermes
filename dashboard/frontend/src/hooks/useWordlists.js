import { useState, useCallback, useEffect } from 'react';
import * as api from '../api/wordcloud';

export const useWordlists = () => {
    const [savedWordlists, setSavedWordlists] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const loadWordlists = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.fetchWordlists();
            setSavedWordlists(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadWordlists();
    }, [loadWordlists]);

    const saveWordlist = async (name, words) => {
        const result = await api.createWordlist({ name, words });
        await loadWordlists();
        return result;
    };

    const updateWordlist = async (id, words) => {
        const result = await api.updateWordlist(id, { words });
        await loadWordlists();
        return result;
    };

    const removeWordlist = async (id) => {
        const result = await api.deleteWordlist(id);
        await loadWordlists();
        return result;
    };

    const getWordlist = async (id) => {
        return await api.fetchWordlist(id);
    };

    return {
        savedWordlists,
        loading,
        error,
        refreshWordlists: loadWordlists,
        saveWordlist,
        updateWordlist,
        removeWordlist,
        getWordlist
    };
};
