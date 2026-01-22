import { useState, useRef, useEffect, useCallback } from 'react';
import { fetchChatMessages, fetchChatMessageStats } from '../api/chat';

export const useChatMessages = ({ autoRefresh = true, refreshInterval = 10 } = {}) => {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [totalMessages, setTotalMessages] = useState(0);
    const [hourlyStats, setHourlyStats] = useState([]);
    const [statsLoading, setStatsLoading] = useState(false);

    // Internal state for pagination and filters managed by hook consumers usually?
    // Or we can manage them here. MessageList managed them locally.
    // Let's expose fetch methods and let component manage filter state to keep hook flexible,
    // OR create a powerful hook that manages all.
    // The previous component had complex state (pagination, filters, auto-refresh).
    // Let's expose `refresh` and `load` functions.

    const lastFetchedHourRef = useRef(null);
    const hasInitialStatsLoadedRef = useRef(false);

    const getMessages = useCallback(async ({ limit, offset, startTime, endTime, authorFilter, messageFilter, paidMessageFilter, isInitial = false }) => {
        try {
            if (isInitial) setLoading(true);
            else setIsRefreshing(true);

            // Default logic moved from component?
            let effectiveStartTime = startTime;
            if (!effectiveStartTime && !endTime) {
                effectiveStartTime = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
            }

            const data = await fetchChatMessages({
                limit,
                offset,
                startTime: effectiveStartTime,
                endTime,
                authorFilter,
                messageFilter,
                paidMessageFilter
            });

            setMessages(data.messages || []);
            setTotalMessages(data.total || 0);
            setError(null);
        } catch (err) {
            console.error('Error fetching messages:', err);
            setError(err.message);
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    }, []);

    const getHourlyStats = useCallback(async ({ startTime, endTime, authorFilter, messageFilter, paidMessageFilter, forceFullFetch = false }) => {
        try {
            if (!hasInitialStatsLoadedRef.current) setStatsLoading(true);

            let effectiveStartTime = startTime;
            const isRealTime = !startTime && !endTime;
            if (isRealTime && (forceFullFetch || !hasInitialStatsLoadedRef.current)) {
                effectiveStartTime = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
            }

            const useIncrementalFetch = !forceFullFetch &&
                hasInitialStatsLoadedRef.current &&
                isRealTime &&
                lastFetchedHourRef.current;

            const data = await fetchChatMessageStats({
                startTime: effectiveStartTime,
                endTime,
                authorFilter,
                messageFilter,
                paidMessageFilter,
                since: useIncrementalFetch ? lastFetchedHourRef.current : undefined
            });

            if (data.length === 0) return;

            lastFetchedHourRef.current = data[data.length - 1].hour;

            if (!hasInitialStatsLoadedRef.current || forceFullFetch || startTime || endTime) {
                setHourlyStats(data || []);
                hasInitialStatsLoadedRef.current = true;
            } else {
                setHourlyStats(prev => {
                    const map = new Map(prev.map(item => [item.hour, item.count]));
                    data.forEach(item => map.set(item.hour, item.count));

                    if (isRealTime) {
                        const cutOff = new Date(Date.now() - 12 * 60 * 60 * 1000).getTime();
                        for (const [key] of map.entries()) {
                            const ts = new Date(key).getTime();
                            if (ts < cutOff) map.delete(key);
                        }
                    }
                    return Array.from(map.entries())
                        .map(([hour, count]) => ({ hour, count }))
                        .sort((a, b) => new Date(a.hour) - new Date(b.hour));
                });
            }

        } catch (err) {
            console.error('Error fetching stats:', err);
        } finally {
            setStatsLoading(false);
        }
    }, []);

    const resetStats = useCallback(() => {
        hasInitialStatsLoadedRef.current = false;
        lastFetchedHourRef.current = null;
        setHourlyStats([]);
    }, []);

    return {
        messages,
        loading,
        isRefreshing,
        error,
        totalMessages,
        hourlyStats,
        statsLoading,
        getMessages,
        getHourlyStats,
        resetStats
    };
};
