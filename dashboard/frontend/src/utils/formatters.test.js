import { describe, expect, test } from 'vitest';
import { formatChartAxisTick } from './formatters';

describe('formatChartAxisTick', () => {
    test('returns the number as string when below 1000', () => {
        expect(formatChartAxisTick(0)).toBe('0');
        expect(formatChartAxisTick(999)).toBe('999');
        expect(formatChartAxisTick(500)).toBe('500');
    });

    test('formats 1000 as 1k', () => {
        expect(formatChartAxisTick(1000)).toBe('1k');
    });

    test('formats values above 1000 with one decimal place', () => {
        expect(formatChartAxisTick(1500)).toBe('1.5k');
        expect(formatChartAxisTick(23000)).toBe('23k');
        expect(formatChartAxisTick(25000)).toBe('25k');
        expect(formatChartAxisTick(8500)).toBe('8.5k');
    });

    test('drops trailing .0 from decimal', () => {
        expect(formatChartAxisTick(2000)).toBe('2k');
        expect(formatChartAxisTick(10000)).toBe('10k');
    });

    test('rounds to one decimal place', () => {
        expect(formatChartAxisTick(1234)).toBe('1.2k');
        expect(formatChartAxisTick(1250)).toBe('1.3k');
    });

    test('returns non-finite value as-is', () => {
        expect(formatChartAxisTick(NaN)).toBeNaN();
        expect(formatChartAxisTick(Infinity)).toBe(Infinity);
    });
});
