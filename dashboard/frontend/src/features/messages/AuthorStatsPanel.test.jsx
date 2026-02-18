import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import AuthorStatsPanel from './AuthorStatsPanel';
import { fetchTopAuthors } from '../../api/chat';

vi.mock('../../api/chat', () => ({
    fetchTopAuthors: vi.fn(),
}));

vi.mock('react-chartjs-2', () => ({
    Bar: () => <div data-testid="author-bar-chart" />,
}));

vi.mock('chart.js', () => ({
    Chart: { register: vi.fn() },
    CategoryScale: {},
    LinearScale: {},
    BarElement: {},
    Title: {},
    Tooltip: {},
    Legend: {},
}));

describe('AuthorStatsPanel', () => {
    beforeEach(() => {
        fetchTopAuthors.mockReset();
    });

    test('renders top authors and triggers onAuthorSelect', async () => {
        const onAuthorSelect = vi.fn();
        fetchTopAuthors.mockResolvedValueOnce({
            top_authors: [
                { author_id: 'a1', author: 'Alice', count: 5 },
                { author_id: 'a2', author: 'Bob', count: 3 },
            ],
            total_authors: 2,
            displayed_authors: 2,
            tie_extended: false,
        });

        render(
            <AuthorStatsPanel
                startTime={null}
                endTime={null}
                authorFilter=""
                messageFilter=""
                paidMessageFilter="all"
                onAuthorSelect={onAuthorSelect}
            />
        );

        expect(await screen.findByText('共 2 位作者')).toBeInTheDocument();
        expect(screen.getByTestId('author-bar-chart')).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: 'Alice' }));

        expect(onAuthorSelect).toHaveBeenCalledWith('a1');
        expect(fetchTopAuthors).toHaveBeenCalled();
    });

    test('shows error state when api fails', async () => {
        fetchTopAuthors.mockRejectedValueOnce(new Error('network failed'));

        render(
            <AuthorStatsPanel
                startTime={null}
                endTime={null}
                authorFilter=""
                messageFilter=""
                paidMessageFilter="all"
            />
        );

        await waitFor(() => {
            expect(screen.getByText(/載入 Top 作者時發生錯誤/)).toBeInTheDocument();
        });
    });
});
