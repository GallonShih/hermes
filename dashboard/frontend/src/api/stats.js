import API_BASE_URL from './client';

export const fetchViewersStats = async ({ hours, startTime, endTime }) => {
    let url = `${API_BASE_URL}/api/stats/viewers`;
    const params = new URLSearchParams();
    if (hours) params.append('hours', hours);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    if (Array.from(params).length > 0) {
        url += `?${params.toString()}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
};

export const fetchCommentsStats = async ({ hours, startTime, endTime }) => {
    let url = `${API_BASE_URL}/api/stats/comments`;
    const params = new URLSearchParams();
    if (hours) params.append('hours', hours);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    if (Array.from(params).length > 0) {
        url += `?${params.toString()}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
};

export const fetchMoneySummary = async ({ startTime, endTime }) => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    const response = await fetch(`${API_BASE_URL}/api/stats/money-summary?${params}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
};
