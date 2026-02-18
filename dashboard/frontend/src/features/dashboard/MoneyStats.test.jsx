import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import MoneyStats from './MoneyStats';
import { fetchMoneySummary } from '../../api/stats';

vi.mock('../../api/stats', () => ({
    fetchMoneySummary: vi.fn(),
}));

describe('MoneyStats', () => {
    beforeEach(() => {
        fetchMoneySummary.mockReset();
    });

    test('renders money stats and allows opening author details', async () => {
        const onAuthorSelect = vi.fn();

        fetchMoneySummary.mockResolvedValueOnce({
            total_amount_twd: 500,
            paid_message_count: 2,
            unknown_currencies: ['USD'],
            top_authors: [
                {
                    author_id: 'author_paid_1',
                    author: 'PaidUser',
                    amount_twd: 500,
                    message_count: 2,
                },
            ],
        });

        render(<MoneyStats startTime={null} endTime={null} onAuthorSelect={onAuthorSelect} />);

        expect(await screen.findByText('Money Statistics')).toBeInTheDocument();
        expect(screen.getByText(/Missing exchange rates/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /1\. PaidUser/i })).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /1\. PaidUser/i }));

        expect(onAuthorSelect).toHaveBeenCalledWith('author_paid_1');
    });

    test('shows error text on api failure', async () => {
        fetchMoneySummary.mockRejectedValueOnce(new Error('summary failed'));

        render(<MoneyStats startTime={null} endTime={null} />);

        expect(await screen.findByText(/Error: summary failed/)).toBeInTheDocument();
    });
});
