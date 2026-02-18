import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { useChatMessages } from './useChatMessages';
import { fetchChatMessages, fetchChatMessageStats } from '../api/chat';

vi.mock('../api/chat', () => ({
    fetchChatMessages: vi.fn(),
    fetchChatMessageStats: vi.fn(),
}));

describe('useChatMessages', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    test('uses last 12 hours as default range when fetching messages in real-time mode', async () => {
        vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-02-18T12:00:00.000Z').getTime());
        fetchChatMessages.mockResolvedValue({
            messages: [{ id: 'm1', message: 'hello' }],
            total: 1,
        });

        const { result } = renderHook(() => useChatMessages());

        await act(async () => {
            await result.current.getMessages({
                limit: 20,
                offset: 0,
                startTime: undefined,
                endTime: undefined,
                isInitial: true,
            });
        });

        expect(fetchChatMessages).toHaveBeenCalledWith({
            limit: 20,
            offset: 0,
            startTime: '2026-02-18T00:00:00.000Z',
            endTime: undefined,
            authorFilter: undefined,
            messageFilter: undefined,
            paidMessageFilter: undefined,
        });
        expect(result.current.messages).toEqual([{ id: 'm1', message: 'hello' }]);
        expect(result.current.totalMessages).toBe(1);
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBeNull();
    });

    test('captures API errors when refreshing messages', async () => {
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        fetchChatMessages.mockRejectedValue(new Error('fetch failed'));

        const { result } = renderHook(() => useChatMessages());

        await act(async () => {
            await result.current.getMessages({
                limit: 20,
                offset: 0,
                startTime: '2026-02-18T10:00:00.000Z',
                endTime: '2026-02-18T12:00:00.000Z',
                isInitial: false,
            });
        });

        expect(result.current.error).toBe('fetch failed');
        expect(result.current.isRefreshing).toBe(false);
        expect(result.current.loading).toBe(false);
        consoleErrorSpy.mockRestore();
    });

    test('fetches hourly stats incrementally and merges with existing points', async () => {
        vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-02-18T12:00:00.000Z').getTime());
        fetchChatMessageStats
            .mockResolvedValueOnce([{ hour: '2026-02-18T10:00:00.000Z', count: 2 }])
            .mockResolvedValueOnce([{ hour: '2026-02-18T11:00:00.000Z', count: 5 }]);

        const { result } = renderHook(() => useChatMessages());

        await act(async () => {
            await result.current.getHourlyStats({
                startTime: undefined,
                endTime: undefined,
                forceFullFetch: false,
            });
        });

        expect(fetchChatMessageStats).toHaveBeenNthCalledWith(1, {
            startTime: '2026-02-18T00:00:00.000Z',
            endTime: undefined,
            authorFilter: undefined,
            messageFilter: undefined,
            paidMessageFilter: undefined,
            since: undefined,
        });
        expect(result.current.hourlyStats).toEqual([{ hour: '2026-02-18T10:00:00.000Z', count: 2 }]);

        await act(async () => {
            await result.current.getHourlyStats({
                startTime: undefined,
                endTime: undefined,
                forceFullFetch: false,
            });
        });

        expect(fetchChatMessageStats).toHaveBeenNthCalledWith(2, {
            startTime: undefined,
            endTime: undefined,
            authorFilter: undefined,
            messageFilter: undefined,
            paidMessageFilter: undefined,
            since: '2026-02-18T10:00:00.000Z',
        });
        await waitFor(() => {
            expect(result.current.hourlyStats).toEqual([
                { hour: '2026-02-18T10:00:00.000Z', count: 2 },
                { hour: '2026-02-18T11:00:00.000Z', count: 5 },
            ]);
        });
    });

    test('resetStats clears incremental state so next stats fetch is full range again', async () => {
        vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-02-18T12:00:00.000Z').getTime());
        fetchChatMessageStats
            .mockResolvedValueOnce([{ hour: '2026-02-18T09:00:00.000Z', count: 3 }])
            .mockResolvedValueOnce([{ hour: '2026-02-18T10:00:00.000Z', count: 4 }])
            .mockResolvedValueOnce([{ hour: '2026-02-18T11:00:00.000Z', count: 5 }]);

        const { result } = renderHook(() => useChatMessages());

        await act(async () => {
            await result.current.getHourlyStats({
                startTime: undefined,
                endTime: undefined,
            });
        });
        await act(async () => {
            await result.current.getHourlyStats({
                startTime: undefined,
                endTime: undefined,
            });
        });

        act(() => {
            result.current.resetStats();
        });

        expect(result.current.hourlyStats).toEqual([]);

        await act(async () => {
            await result.current.getHourlyStats({
                startTime: undefined,
                endTime: undefined,
            });
        });

        expect(fetchChatMessageStats).toHaveBeenNthCalledWith(3, {
            startTime: '2026-02-18T00:00:00.000Z',
            endTime: undefined,
            authorFilter: undefined,
            messageFilter: undefined,
            paidMessageFilter: undefined,
            since: undefined,
        });
    });
});
