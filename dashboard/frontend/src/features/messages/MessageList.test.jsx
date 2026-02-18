import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import MessageList from './MessageList';
import { useChatMessages } from '../../hooks/useChatMessages';

vi.mock('../../hooks/useChatMessages', () => ({
    useChatMessages: vi.fn(),
}));

vi.mock('./AuthorStatsPanel', () => ({
    default: () => <div data-testid="author-stats-panel" />,
}));

vi.mock('react-chartjs-2', () => ({
    Line: () => <div data-testid="message-line-chart" />,
}));

vi.mock('chart.js', () => ({
    Chart: { register: vi.fn() },
    CategoryScale: {},
    LinearScale: {},
    TimeScale: {},
    PointElement: {},
    LineElement: {},
    Title: {},
    Tooltip: {},
    Legend: {},
}));

const makeHookReturn = (overrides = {}) => {
    const getMessages = vi.fn();
    const getHourlyStats = vi.fn();
    const resetStats = vi.fn();

    return {
        messages: [
            {
                id: 'msg_1',
                time: '2026-02-17T00:00:00Z',
                author: '@Tester',
                author_id: 'author_1',
                message: 'hello :smile:',
                emotes: [{ name: ':smile:', images: [{ url: 'https://example.com/smile.png' }] }],
                message_type: 'paid_message',
                money: { text: '$100.00' },
            },
        ],
        loading: false,
        isRefreshing: false,
        error: null,
        totalMessages: 25,
        hourlyStats: [{ hour: '2026-02-17T00:00:00Z', count: 1 }],
        statsLoading: false,
        getMessages,
        getHourlyStats,
        resetStats,
        ...overrides,
    };
};

describe('MessageList', () => {
    beforeEach(() => {
        useChatMessages.mockReset();
    });

    test('renders message content and clicks author callback', async () => {
        const onAuthorSelect = vi.fn();
        useChatMessages.mockReturnValue(makeHookReturn());

        const user = userEvent.setup();

        render(<MessageList startTime={null} endTime={null} onAuthorSelect={onAuthorSelect} />);

        await user.click(screen.getAllByRole('button', { name: '@Tester' })[0]);

        expect(onAuthorSelect).toHaveBeenCalledWith('author_1');
        expect(screen.getAllByText('$100.00').length).toBeGreaterThan(0);
        expect(screen.getAllByAltText(':smile:').length).toBeGreaterThan(0);
        expect(screen.getByTestId('author-stats-panel')).toBeInTheDocument();
    });

    test('applies author filter on blur and sends it to getMessages', async () => {
        const hook = makeHookReturn();
        useChatMessages.mockReturnValue(hook);

        const user = userEvent.setup();

        render(<MessageList startTime={null} endTime={null} />);

        const authorInput = screen.getAllByPlaceholderText('輸入後按 Enter 搜尋...')[0];
        await user.clear(authorInput);
        await user.type(authorInput, 'Alice');
        await user.tab(); // trigger blur

        await waitFor(() => {
            expect(hook.getMessages).toHaveBeenCalled();
        });

        const lastCallArg = hook.getMessages.mock.calls.at(-1)?.[0];
        expect(lastCallArg.authorFilter).toBe('Alice');
    });

    test('manual refresh triggers message and stats reload', async () => {
        const hook = makeHookReturn();
        useChatMessages.mockReturnValue(hook);

        const user = userEvent.setup();

        render(<MessageList startTime={null} endTime={null} />);

        await user.click(screen.getByRole('button', { name: /刷新列表/ }));

        expect(hook.getMessages).toHaveBeenCalled();
        expect(hook.getHourlyStats).toHaveBeenCalled();
    });
});
