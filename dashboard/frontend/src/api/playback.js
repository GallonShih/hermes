import API_BASE_URL from './client';

export const fetchPlaybackSnapshots = async ({ startTime, endTime, stepSeconds }) => {
    const params = new URLSearchParams({
        start_time: startTime,
        end_time: endTime,
        step_seconds: stepSeconds.toString()
    });

    const response = await fetch(`${API_BASE_URL}/api/playback/snapshots?${params}`);
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};

export const fetchPlaybackWordCloudSnapshots = async ({ startTime, endTime, stepSeconds, windowHours, wordLimit, wordlistId, replacementWordlistId }) => {
    const params = new URLSearchParams({
        start_time: startTime,
        end_time: endTime,
        step_seconds: stepSeconds.toString(),
        window_hours: windowHours.toString(),
        word_limit: wordLimit.toString()
    });

    if (wordlistId) {
        params.append('wordlist_id', wordlistId.toString());
    }
    if (replacementWordlistId) {
        params.append('replacement_wordlist_id', replacementWordlistId.toString());
    }

    const response = await fetch(`${API_BASE_URL}/api/playback/word-frequency-snapshots?${params}`);
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};
