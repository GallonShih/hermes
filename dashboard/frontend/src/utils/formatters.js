/**
 * Format a number with commas (zh-TW locale)
 * @param {number} num 
 * @returns {string}
 */
export const formatNumber = (num) => {
    if (num === null || num === undefined) return '--';
    return new Intl.NumberFormat('zh-TW').format(num);
};

/**
 * Format currency in TWD (zh-TW locale)
 * @param {number} amount 
 * @returns {string}
 */
export const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '--';
    return new Intl.NumberFormat('zh-TW', {
        style: 'currency',
        currency: 'TWD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
};

/**
 * Format timestamp to "YYYY/MM/DD HH:MM"
 * @param {string|Date} isoString 
 * @returns {string}
 */
export const formatTimestamp = (isoString) => {
    if (!isoString) return '--';
    const date = new Date(isoString);
    const pad = (n) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

/**
 * Format date to local hour ISO string "YYYY-MM-DDTHH:00"
 * @param {string|Date} date 
 * @returns {string}
 */
export const formatLocalHour = (date) => {
    const d = new Date(date);
    d.setMinutes(0, 0, 0);
    const pad = (n) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
};

/**
 * Format timestamp with specific timezone (Asia/Taipei)
 * @param {string|Date} utcTime 
 * @returns {string}
 */
export const formatMessageTime = (utcTime) => {
    if (!utcTime) return 'N/A';
    const date = new Date(utcTime);
    const options = {
        timeZone: 'Asia/Taipei',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    return new Intl.DateTimeFormat('zh-TW', options).format(date);
};
