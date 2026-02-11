import React, { useMemo } from 'react';

const DateTimeHourSelector = ({ label, value, onChange, max }) => {
    const datePart = value ? value.split('T')[0] : '';
    const hourPart = value ? value.split('T')[1]?.substring(0, 2) : '00';
    const maxDate = max ? max.split('T')[0] : undefined;

    const allHours = useMemo(() => Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0')), []);

    const availableHours = useMemo(() => {
        if (!max || !datePart) return allHours;
        if (datePart < maxDate) return allHours;
        if (datePart === maxDate) {
            const maxHour = parseInt(max.split('T')[1].substring(0, 2), 10);
            return allHours.filter(h => parseInt(h, 10) <= maxHour);
        }
        return [];
    }, [max, datePart, maxDate, allHours]);

    const handleDateChange = (e) => {
        const newDate = e.target.value;
        if (!newDate) {
            onChange('');
            return;
        }
        let newHour = hourPart;
        // If date changes to maxDate, ensure hour is within limit
        if (max && newDate === maxDate) {
            const maxHourStr = max.split('T')[1].substring(0, 2);
            if (parseInt(newHour, 10) > parseInt(maxHourStr, 10)) {
                newHour = maxHourStr;
            }
        }
        onChange(`${newDate}T${newHour}:00`);
    };

    const handleHourChange = (e) => {
        const newHour = e.target.value;
        if (!datePart) return;
        onChange(`${datePart}T${newHour}:00`);
    };

    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <div className="flex flex-col sm:flex-row gap-2">
                <input
                    type="date"
                    className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={datePart}
                    onChange={handleDateChange}
                    max={maxDate}
                />
                <select
                    className="w-full sm:w-24 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={hourPart}
                    onChange={handleHourChange}
                    disabled={!datePart}
                >
                    {availableHours.map(h => (
                        <option key={h} value={h}>{h}:00</option>
                    ))}
                </select>
            </div>
        </div>
    );
};

export default DateTimeHourSelector;
