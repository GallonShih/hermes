import API_BASE_URL from './client';

export const fetchStreamInfo = async () => {
    const res = await fetch(`${API_BASE_URL}/api/stream-info`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
};
