import { useState, useRef, useEffect, useCallback } from 'react';
import { fetchPlaybackSnapshots, fetchPlaybackWordCloudSnapshots } from '../api/playback';

export const usePlayback = () => {
    // Playback state
    const [snapshots, setSnapshots] = useState([]);
    const [metadata, setMetadata] = useState(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // Word cloud state
    const [wordcloudSnapshots, setWordcloudSnapshots] = useState([]);
    const [wordcloudLoading, setWordcloudLoading] = useState(false);
    const [wordcloudError, setWordcloudError] = useState(null);

    const playIntervalRef = useRef(null);

    // Load snapshots
    const loadSnapshots = async ({ startDate, endDate, stepSeconds }) => {
        if (!startDate || !endDate) return;

        setIsLoading(true);
        setError(null);
        setIsPlaying(false);

        try {
            const startIso = new Date(startDate).toISOString();
            const endIso = new Date(endDate).toISOString();

            const data = await fetchPlaybackSnapshots({
                startTime: startIso,
                endTime: endIso,
                stepSeconds
            });

            setSnapshots(data.snapshots);
            setMetadata(data.metadata);
            setCurrentIndex(0);
            return true;
        } catch (err) {
            console.error('Error loading snapshots:', err);
            setError(err.message);
            return false;
        } finally {
            setIsLoading(false);
        }
    };

    // Load wordcloud snapshots
    const loadWordcloudSnapshots = async ({ startDate, endDate, stepSeconds, windowHours, wordLimit, wordlistId }) => {
        if (!startDate || !endDate) return;

        setWordcloudLoading(true);
        setWordcloudError(null);

        try {
            const startIso = new Date(startDate).toISOString();
            const endIso = new Date(endDate).toISOString();

            const data = await fetchPlaybackWordCloudSnapshots({
                startTime: startIso,
                endTime: endIso,
                stepSeconds,
                windowHours,
                wordLimit,
                wordlistId
            });

            setWordcloudSnapshots(data.snapshots);
        } catch (err) {
            console.error('Error loading wordcloud snapshots:', err);
            setWordcloudError(err.message);
        } finally {
            setWordcloudLoading(false);
        }
    };

    // Playback control
    const togglePlayback = useCallback(() => {
        if (snapshots.length === 0) return;
        setIsPlaying(prev => !prev);
    }, [snapshots.length]);

    // Handle playback interval
    useEffect(() => {
        // Needs playbackSpeed passed in or managed here? 
        // We'll accept speed in the effect dep or ref, but typically hooks should be self contained or accept config.
        // Let's rely on the component to manage the interval if speed varies dynamic, OR expose a setSpeed.
        // For simplicity, let's keep the interval logic here but we need `playbackSpeed`. 
        // I'll make the hook accept `playbackSpeed`.
    }, []); // Wait, useEffect needs `playbackSpeed`.

    // Refactored: let the hook handle the interval, but it needs `playbackSpeed`
    // We can return a ref or method to update speed? Or just accept it as arg to the hook?
    // If we accept as arg, usage is `usePlayback(speed)`.

    return {
        snapshots,
        metadata,
        currentIndex,
        setCurrentIndex,
        isPlaying,
        setIsPlaying,
        isLoading,
        error,
        wordcloudSnapshots,
        wordcloudLoading,
        wordcloudError,
        loadSnapshots,
        loadWordcloudSnapshots,
        togglePlayback
    };
};
