import { beforeEach, afterEach, describe, expect, test, vi } from 'vitest';
import {
    fetchAuthorMessages,
    fetchAuthorSummary,
    fetchAuthorTrend,
    fetchTopAuthors,
} from './chat';

const mockFetch = vi.fn();

describe('chat api helpers', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', mockFetch);
        mockFetch.mockReset();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    test('fetchAuthorSummary passes query params and returns json', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ author_id: 'author_1' }),
        });

        const data = await fetchAuthorSummary({
            authorId: 'author_1',
            startTime: '2026-02-17T00:00:00Z',
            endTime: '2026-02-17T01:00:00Z',
        });

        expect(data.author_id).toBe('author_1');
        expect(mockFetch).toHaveBeenCalledTimes(1);

        const calledUrl = mockFetch.mock.calls[0][0];
        expect(calledUrl).toContain('/api/chat/authors/author_1/summary?');
        expect(calledUrl).toContain('start_time=2026-02-17T00%3A00%3A00Z');
        expect(calledUrl).toContain('end_time=2026-02-17T01%3A00%3A00Z');
    });

    test('fetchAuthorSummary surfaces backend detail for errors', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            status: 404,
            json: async () => ({ detail: '查無作者資料：author_x。可能不在目前直播或時間範圍內。' }),
        });

        await expect(fetchAuthorSummary({ authorId: 'author_x' })).rejects.toThrow('可能不在目前直播或時間範圍內');
    });

    test('fetchAuthorMessages sends pagination params', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ messages: [], total: 0 }),
        });

        await fetchAuthorMessages({
            authorId: 'author_1',
            limit: 20,
            offset: 40,
            startTime: '2026-02-17T00:00:00Z',
            endTime: '2026-02-17T01:00:00Z',
        });

        const calledUrl = mockFetch.mock.calls[0][0];
        expect(calledUrl).toContain('/api/chat/authors/author_1/messages?');
        expect(calledUrl).toContain('limit=20');
        expect(calledUrl).toContain('offset=40');
    });

    test('fetchAuthorTrend and fetchTopAuthors build expected URLs', async () => {
        mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
        mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ top_authors: [] }) });

        await fetchAuthorTrend({ authorId: 'author_1' });
        await fetchTopAuthors({ includeMeta: true, paidMessageFilter: 'paid_only' });

        expect(mockFetch.mock.calls[0][0]).toContain('/api/chat/authors/author_1/trend?');
        expect(mockFetch.mock.calls[1][0]).toContain('/api/chat/top-authors?');
        expect(mockFetch.mock.calls[1][0]).toContain('include_meta=true');
        expect(mockFetch.mock.calls[1][0]).toContain('paid_message_filter=paid_only');
    });
});
