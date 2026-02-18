import API_BASE_URL from './client';

const parseErrorDetail = async (response) => {
    try {
        const payload = await response.json();
        if (payload?.detail) return payload.detail;
    } catch (_) {
        // ignore json parse errors and fallback to status text
    }
    return `HTTP error! status: ${response.status}`;
};

export const fetchChatMessages = async ({ limit, offset, startTime, endTime, authorFilter, messageFilter, paidMessageFilter }) => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit);
    if (offset) params.append('offset', offset);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    if (authorFilter) params.append('author_filter', authorFilter);
    if (messageFilter) params.append('message_filter', messageFilter);
    if (paidMessageFilter && paidMessageFilter !== 'all') params.append('paid_message_filter', paidMessageFilter);

    const response = await fetch(`${API_BASE_URL}/api/chat/messages?${params}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
};

export const fetchChatMessageStats = async ({ startTime, endTime, authorFilter, messageFilter, paidMessageFilter, since }) => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    if (authorFilter) params.append('author_filter', authorFilter);
    if (messageFilter) params.append('message_filter', messageFilter);
    if (paidMessageFilter && paidMessageFilter !== 'all') params.append('paid_message_filter', paidMessageFilter);
    if (since) params.append('since', since);

    const response = await fetch(`${API_BASE_URL}/api/chat/message-stats?${params}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
};

export const fetchTopAuthors = async ({ startTime, endTime, authorFilter, messageFilter, paidMessageFilter, includeMeta = false }) => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    if (authorFilter) params.append('author_filter', authorFilter);
    if (messageFilter) params.append('message_filter', messageFilter);
    if (paidMessageFilter && paidMessageFilter !== 'all') params.append('paid_message_filter', paidMessageFilter);
    if (includeMeta) params.append('include_meta', 'true');

    const response = await fetch(`${API_BASE_URL}/api/chat/top-authors?${params}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
};

export const fetchAuthorSummary = async ({ authorId, startTime, endTime }) => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    const response = await fetch(`${API_BASE_URL}/api/chat/authors/${encodeURIComponent(authorId)}/summary?${params}`);
    if (!response.ok) {
        throw new Error(await parseErrorDetail(response));
    }
    return response.json();
};

export const fetchAuthorMessages = async ({ authorId, limit, offset, startTime, endTime }) => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit);
    if (offset) params.append('offset', offset);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    const response = await fetch(`${API_BASE_URL}/api/chat/authors/${encodeURIComponent(authorId)}/messages?${params}`);
    if (!response.ok) {
        throw new Error(await parseErrorDetail(response));
    }
    return response.json();
};

export const fetchAuthorTrend = async ({ authorId, startTime, endTime }) => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    const response = await fetch(`${API_BASE_URL}/api/chat/authors/${encodeURIComponent(authorId)}/trend?${params}`);
    if (!response.ok) {
        throw new Error(await parseErrorDetail(response));
    }
    return response.json();
};
