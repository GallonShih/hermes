import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import AuthorDetailDrawer from './AuthorDetailDrawer';

vi.mock('./AuthorDetailContent', () => ({
    default: ({ authorId }) => <div data-testid="author-detail-content">author:{authorId}</div>,
}));

describe('AuthorDetailDrawer', () => {
    test('renders content when open', () => {
        render(<AuthorDetailDrawer isOpen onClose={vi.fn()} authorId="author_1" />);

        expect(screen.getByText('Author Detail')).toBeInTheDocument();
        expect(screen.getByTestId('author-detail-content')).toHaveTextContent('author:author_1');
    });

    test('calls onClose when pressing Escape', () => {
        const onClose = vi.fn();
        render(<AuthorDetailDrawer isOpen onClose={onClose} authorId="author_1" />);

        fireEvent.keyDown(document, { key: 'Escape' });

        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
