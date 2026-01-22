import React, { useEffect, useRef, useMemo, useCallback } from 'react';
import * as d3 from 'd3';

/**
 * Dynamic Word Cloud Component using D3.js
 * 
 * Features:
 * - Slot-based stable layout (words stay in position)
 * - Boundary clamping (prevents text from going outside)
 * - Smooth transitions for size changes
 * - Color palette based on word text hash
 */
function DynamicWordCloud({ words, width = 900, height = 500, wordLimit = 30 }) {
    const containerRef = useRef(null);
    const svgRef = useRef(null);
    const wordToSlotMapRef = useRef(new Map());
    const slotsRef = useRef([]);

    // Configuration
    const margin = 60;
    const numSlots = wordLimit;

    // Color palette
    const colorPalette = useMemo(() => [
        '#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE',
        '#3BA272', '#FC8452', '#9A60B4', '#EA7CCC', '#48B8D0',
        '#6E7074', '#546570', '#C23531', '#2F4554', '#61A0A8'
    ], []);

    // Generate stable color based on word text
    const getWordColor = useCallback((word) => {
        let hash = 0;
        for (let i = 0; i < word.length; i++) {
            hash = word.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colorPalette[Math.abs(hash) % colorPalette.length];
    }, [colorPalette]);

    // Initialize slots with spread-out spiral + noise distribution to maximize canvas usage
    useEffect(() => {
        const slots = [];
        const centerX = width / 2;
        const centerY = height / 2;

        // Use a larger effective area to spread words out
        // Leave a smaller margin for the actual calculation but clamp later
        const effectiveWidth = width - margin * 1.5;
        const effectiveHeight = height - margin * 1.5;
        const maxRadius = Math.min(effectiveWidth, effectiveHeight) / 2;

        const seededRandom = (seed) => {
            const x = Math.sin(seed * 9999) * 10000;
            return x - Math.floor(x);
        };

        for (let i = 0; i < numSlots; i++) {
            // Golden angle 
            const goldenAngle = Math.PI * (3 - Math.sqrt(5));
            const angle = i * goldenAngle;

            // Square root distribution for area
            const normalizedRadius = Math.sqrt((i + 1) / numSlots);

            // Push words further out to use full canvas
            const baseRadius = normalizedRadius * maxRadius;

            // Scale X and Y to match aspect ratio
            const aspectRatio = effectiveWidth / effectiveHeight;
            const radiusX = baseRadius * (aspectRatio > 1 ? aspectRatio * 0.8 : 1);
            const radiusY = baseRadius * (aspectRatio < 1 ? (1 / aspectRatio) * 0.8 : 1);

            // Add organic noise, scaled by available space
            const noiseX = (seededRandom(i * 7 + 1) - 0.5) * (effectiveWidth / 10);
            const noiseY = (seededRandom(i * 13 + 2) - 0.5) * (effectiveHeight / 10);

            let x = centerX + Math.cos(angle) * radiusX + noiseX;
            let y = centerY + Math.sin(angle) * radiusY + noiseY;

            // Clamp to stay strictly within margins
            x = Math.max(margin, Math.min(width - margin, x));
            y = Math.max(margin, Math.min(height - margin, y));

            slots.push({
                id: i,
                x: x,
                y: y,
                occupiedBy: null
            });
        }
        slotsRef.current = slots;
        // Reset word-to-slot mapping when slots are re-initialized
        wordToSlotMapRef.current = new Map();
    }, [width, height, margin, numSlots]);

    // Initialize SVG
    useEffect(() => {
        if (!containerRef.current || svgRef.current) return;

        const svg = d3.select(containerRef.current)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .style('font-family', 'Noto Sans TC, sans-serif');

        svg.append('g').attr('class', 'word-group');
        svgRef.current = svg;

        return () => {
            if (containerRef.current) {
                d3.select(containerRef.current).selectAll('*').remove();
            }
            svgRef.current = null;
        };
    }, [width, height]);

    // Update word cloud when words change
    useEffect(() => {
        if (!svgRef.current || !words || words.length === 0) return;

        const svg = svgRef.current;
        const wordGroup = svg.select('.word-group');
        const slots = slotsRef.current;
        const wordToSlotMap = wordToSlotMapRef.current;

        const activeWordNames = new Set(words.map(w => w.word));

        // Release disappeared words
        for (let [word, slotId] of wordToSlotMap.entries()) {
            if (!activeWordNames.has(word)) {
                slots[slotId].occupiedBy = null;
                wordToSlotMap.delete(word);
            }
        }

        // Assign slots to new words
        words.forEach(w => {
            if (!wordToSlotMap.has(w.word)) {
                const emptySlot = slots.find(s => s.occupiedBy === null);
                if (emptySlot) {
                    emptySlot.occupiedBy = w.word;
                    wordToSlotMap.set(w.word, emptySlot.id);
                }
            }
        });

        // Calculate font size scaling
        const maxSize = Math.max(...words.map(w => w.size), 1);
        const minSize = Math.min(...words.map(w => w.size), 0);
        const sizeRange = maxSize - minSize || 1;

        const getFontSize = (size) => {
            const normalized = (size - minSize) / sizeRange;
            return Math.floor(12 + normalized * 48); // 12-60px range
        };

        // Prepare display data
        const displayData = words
            .filter(w => wordToSlotMap.has(w.word))
            .map(w => {
                const slot = slots[wordToSlotMap.get(w.word)];
                return {
                    text: w.word,
                    size: w.size,
                    fontSize: getFontSize(w.size),
                    x: slot.x,
                    y: slot.y
                };
            });

        // D3 Data Join
        const texts = wordGroup.selectAll('text')
            .data(displayData, d => d.text);

        // Exit - fade out and shrink (use d3.select for explicit transition)
        const exitSelection = texts.exit();
        exitSelection.each(function () {
            d3.select(this)
                .style('opacity', 0)
                .style('font-size', '0px');
        });
        // Remove after a delay
        setTimeout(() => {
            exitSelection.remove();
        }, 600);

        // Enter - new words fade in
        const enterTexts = texts.enter()
            .append('text')
            .attr('text-anchor', 'middle')
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .style('opacity', 0)
            .style('font-size', '0px')
            .style('font-weight', '900')
            .style('paint-order', 'stroke')
            .style('stroke', '#ffffff')
            .style('stroke-width', '1px')
            .style('cursor', 'default')
            .text(d => d.text);

        // Update - merge enter and update, animate using CSS transitions
        const mergedTexts = texts.merge(enterTexts);

        // Apply CSS transition for smooth animation
        mergedTexts
            .style('transition', 'all 0.8s cubic-bezier(0.33, 1, 0.68, 1)')
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .style('opacity', 1)
            .style('font-size', d => d.fontSize + 'px')
            .style('fill', d => getWordColor(d.text));

    }, [words, getWordColor]);

    // Empty state
    if (!words || words.length === 0) {
        return (
            <div
                ref={containerRef}
                className="flex items-center justify-center text-gray-400 bg-slate-50 rounded-2xl border border-slate-200"
                style={{ height: `${height}px` }}
            >
                <div className="text-center">
                    <div className="text-4xl mb-2">☁️</div>
                    <div>載入資料後顯示動態文字雲</div>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="bg-slate-50 rounded-2xl overflow-hidden relative border border-slate-200 shadow-inner"
            style={{ height: `${height}px` }}
        />
    );
}

export default DynamicWordCloud;
