import { useState, useCallback, useEffect } from 'react';
import * as api from '../api/replacement_wordlist';

export const useReplacementWordlists = () => {
    const [savedWordlists, setSavedWordlists] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const loadWordlists = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.fetchReplacementWordlists();
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

    const saveWordlist = useCallback(async (name, replacements) => {
        const result = await api.createReplacementWordlist({ name, replacements });
        await loadWordlists();
        return result;
    }, [loadWordlists]);

    const updateWordlist = useCallback(async (id, replacements) => {
        // Note: The API supports updating name too, but this convenience method focuses on replacements
        const result = await api.updateReplacementWordlist(id, { replacements });
        await loadWordlists();
        return result;
    }, [loadWordlists]);

    const removeWordlist = useCallback(async (id) => {
        const result = await api.deleteReplacementWordlist(id);
        await loadWordlists();
        return result;
    }, [loadWordlists]);

    const getWordlist = useCallback(async (id) => {
        return await api.fetchReplacementWordlist(id);
    }, []);

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
