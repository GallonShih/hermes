import React, { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    TimeScale, // Add TimeScale import
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { enUS } from 'date-fns/locale';

ChartJS.register(
    CategoryScale,
    LinearScale,
    TimeScale, // Register TimeScale
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend
);

const API_BASE_URL = 'http://localhost:8000'; // Should be configurable or relative in prod

function App() {
    const [viewData, setViewData] = useState([]);
    const [commentData, setCommentData] = useState([]);
    const [barFlash, setBarFlash] = useState(false);

    // Filter States
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [toggleRefresh, setToggleRefresh] = useState(true);

    // Dynamic Time Axis State
    const [timeAxisConfig, setTimeAxisConfig] = useState({
        type: 'time',
        time: {
            unit: 'hour',
            displayFormats: { hour: 'MM/dd HH:mm' }
        },
        ticks: {
            source: 'auto', // Ensure ticks are generated based on scale, not just data
            autoSkip: false // Try to show all hour ticks if space permits
        },
        min: new Date(new Date().getTime() - 12 * 60 * 60 * 1000).getTime(), // Initial rolling 12h
        max: new Date().getTime(),
    });

    const fetchViewers = async (start, end) => {
        try {
            let url = `${API_BASE_URL}/api/stats/viewers?hours=12`;
            if (start && end) {
                url = `${API_BASE_URL}/api/stats/viewers?start_time=${start}&end_time=${end}`;
            }
            const res = await fetch(url);
            const data = await res.json();
            const validData = data.map(d => ({
                // API returns UTC ISO string without Z
                x: new Date(d.time.endsWith('Z') ? d.time : d.time + 'Z').getTime(),
                y: d.count
            }));
            setViewData(validData);
        } catch (err) {
            console.error("Failed to fetch viewers", err);
        }
    };

    const fetchComments = async (start, end) => {
        try {
            let url = `${API_BASE_URL}/api/stats/comments?hours=12`;
            if (start && end) {
                url = `${API_BASE_URL}/api/stats/comments?start_time=${start}&end_time=${end}`;
            }
            const res = await fetch(url);
            const data = await res.json();
            const validData = data.map(d => ({
                // API returns UTC ISO string without Z
                // Shift by +30 minutes to center the bar in the hour slot
                x: new Date(d.hour.endsWith('Z') ? d.hour : d.hour + 'Z').getTime() + 30 * 60 * 1000,
                y: d.count
            }));
            setCommentData(validData);

            // Flash effect can remain
            setBarFlash(true);
            setTimeout(() => setBarFlash(false), 400);
        } catch (err) {
            console.error("Failed to fetch comments", err);
        }
    };

    const handleFilter = () => {
        if (!startDate || !endDate) {
            alert('Please select both start and end time');
            return;
        }

        const startIso = new Date(startDate).toISOString();
        const endObj = new Date(endDate);
        endObj.setMinutes(59, 59, 999);
        const endIso = endObj.toISOString();

        const startTs = new Date(startDate).getTime();
        const endTs = endObj.getTime();

        setTimeAxisConfig(prev => ({
            ...prev,
            min: startTs,
            max: endTs,
        }));

        setToggleRefresh(false);
        fetchViewers(startIso, endIso);
        fetchComments(startIso, endIso);
    };

    useEffect(() => {
        // Initial / Polling
        const intervalId = setInterval(() => {
            if (toggleRefresh) {
                fetchViewers();
                fetchComments();

                // Update rolling window
                const now = new Date();
                const twelveHoursAgo = new Date(now.getTime() - 12 * 60 * 60 * 1000);
                setTimeAxisConfig(prev => ({
                    ...prev,
                    min: twelveHoursAgo.getTime(),
                    max: now.getTime(),
                }));
            }
        }, 5000);

        // Ensure initial run
        if (toggleRefresh) {
            fetchViewers();
            fetchComments();
        }

        return () => clearInterval(intervalId);
    }, [toggleRefresh]);



    // Dual Axis Chart Config
    const chartData = {
        datasets: [
            {
                type: 'line',
                label: '即時觀看人數',
                data: viewData,
                borderColor: '#5470C6',
                backgroundColor: 'rgba(84,112,198,0.2)',
                tension: 0.4,
                pointRadius: (ctx) => {
                    const index = ctx.dataIndex;
                    const count = ctx.dataset.data.length;
                    return index === count - 1 ? 5 : 0;
                },
                pointBackgroundColor: (ctx) => {
                    const index = ctx.dataIndex;
                    const count = ctx.dataset.data.length;
                    return index === count - 1 ? '#ff4d4f' : '#5470C6';
                },
                pointBorderColor: (ctx) => {
                    const index = ctx.dataIndex;
                    const count = ctx.dataset.data.length;
                    return index === count - 1 ? '#ff4d4f' : '#5470C6';
                },
                pointHoverRadius: 8,
                yAxisID: 'y1',
                order: 1, // Draw on top
            },
            {
                type: 'bar',
                label: '每小時留言數',
                data: commentData,
                backgroundColor: (ctx) => {
                    if (!commentData.length || !ctx.raw) return '#91cc75'; // Default color green-ish for distinction

                    const maxX = commentData[commentData.length - 1].x;
                    if (ctx.raw.x === maxX) {
                        return barFlash ? 'rgba(255,77,79,0.5)' : '#ff4d4f';
                    }
                    return '#91cc75';
                },
                borderWidth: 1,
                yAxisID: 'y2',
                order: 2,
            },
        ],
    };

    // Custom Plugin to draw Grid Lines strictly at Top of Hour
    const hourGridPlugin = {
        id: 'hourGrid',
        beforeDraw: (chart) => {
            const ctx = chart.ctx;
            const xAxis = chart.scales.x;
            const yAxis = chart.scales.y1; // Use y1 height reference

            // Save context
            ctx.save();
            ctx.beginPath();
            ctx.lineWidth = 1;
            ctx.strokeStyle = '#e0e0e0'; // Grid color

            const minTime = xAxis.min;
            const maxTime = xAxis.max;

            // Find first top of hour after minTime
            let currentTime = new Date(minTime);
            if (currentTime.getMinutes() !== 0 || currentTime.getSeconds() !== 0 || currentTime.getMilliseconds() !== 0) {
                // Move to next hour
                currentTime.setHours(currentTime.getHours() + 1, 0, 0, 0);
            }

            while (currentTime.getTime() <= maxTime) {
                const x = xAxis.getPixelForValue(currentTime.getTime());

                // Draw vertical line if within chart area
                if (x >= xAxis.left && x <= xAxis.right) {
                    ctx.moveTo(x, xAxis.top);
                    ctx.lineTo(x, xAxis.bottom);
                }

                // Increment 1 hour
                currentTime.setTime(currentTime.getTime() + 60 * 60 * 1000);
            }

            ctx.stroke();
            ctx.restore();
        }
    };

    // Register the plugin only for this chart or use in options
    // ChartJS 3/4 way is to pass in plugins array or register globally.
    // We will include it in the <Chart /> component usage below.

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false,
        },
        plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'Real-time Analytics (12H)' },
            tooltip: {
                callbacks: {
                    footer: (tooltipItems) => {
                        const item = tooltipItems[0];
                        if (!item || !item.raw) return '';

                        const timestamp = item.raw.x;

                        // If hovering Viewers (Line), show Comments for that hour
                        if (item.dataset.type === 'line') {
                            // Floor to hour to find matching comment bar
                            const date = new Date(timestamp);
                            date.setMinutes(0, 0, 0); // Comments are stored at top of hour

                            // Data is shifted by +30 mins for centering, so we must match that
                            const hourTime = date.getTime() + 30 * 60 * 1000;
                            const comment = commentData.find(d => d.x === hourTime);

                            return `Comments: ${comment ? comment.y : 'NA'}`;
                        }

                        // If hovering Comments (Bar), show Viewers at that time
                        if (item.dataset.type === 'bar') {
                            if (!viewData.length) return 'Viewers: NA';

                            const closestViewer = viewData.reduce((prev, curr) => {
                                return (Math.abs(curr.x - timestamp) < Math.abs(prev.x - timestamp) ? curr : prev);
                            });

                            // Strict 5 minute threshold
                            const diff = Math.abs(closestViewer.x - timestamp);
                            const THRESHOLD = 5 * 60 * 1000;

                            if (diff > THRESHOLD) {
                                return 'Viewers: NA';
                            }

                            return closestViewer ? `Viewers: ${closestViewer.y}` : 'Viewers: NA';
                        }
                        return '';
                    }
                }
            },
        },
        scales: {
            x: {
                ...timeAxisConfig,
                grid: { display: false }, // Disable default grid, use plugin
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'left',
                title: { display: true, text: 'Viewers' },
                grid: { display: true },
                beginAtZero: true,
            },
            y2: {
                type: 'linear',
                display: true,
                position: 'right',
                title: { display: true, text: 'Comments' },
                grid: { drawOnChartArea: false }, // only want the grid lines for one axis to show up
                beginAtZero: true,
            },
        },
    };

    // Helper for local datetime-local string (YYYY-MM-DDTHH:00)
    const formatLocalHour = (date) => {
        const d = new Date(date);
        d.setMinutes(0, 0, 0);
        const pad = (n) => n.toString().padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
    };

    return (
        <div className="min-h-screen bg-gray-100 font-sans text-gray-900">
            <div className="max-w-7xl mx-auto p-4 md:p-8">
                <header className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                    <h1 className="text-3xl font-bold text-gray-800">Hermes 監控儀表板</h1>

                    <div className="flex items-center gap-2 bg-white p-3 rounded shadow">
                        <label className="text-sm font-semibold text-gray-600">Range:</label>
                        <button
                            onClick={() => setStartDate(formatLocalHour(new Date(Date.now() - 12 * 60 * 60 * 1000)))}
                            className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded text-xs text-gray-600"
                        >
                            -12H
                        </button>
                        <input
                            type="datetime-local"
                            step="3600"
                            className="border rounded p-1 text-sm cursor-pointer"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                        />
                        <span className="text-gray-400">to</span>
                        <input
                            type="datetime-local"
                            step="3600"
                            className="border rounded p-1 text-sm cursor-pointer"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                        />
                        <button
                            onClick={() => setEndDate(formatLocalHour(new Date()))}
                            className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded text-xs text-gray-600 mr-2"
                        >
                            Now
                        </button>
                        <button
                            onClick={handleFilter}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1 rounded text-sm font-medium transition-colors"
                        >
                            Filter
                        </button>
                        {(startDate || endDate) && (
                            <button
                                onClick={() => {
                                    setStartDate('');
                                    setEndDate('');
                                    setToggleRefresh(true);
                                    // Reset window immediately
                                    const now = new Date();
                                    const twelveHoursAgo = new Date(now.getTime() - 12 * 60 * 60 * 1000);
                                    setTimeAxisConfig({
                                        type: 'time',
                                        time: { unit: 'hour', displayFormats: { hour: 'MM/dd HH:mm' } },
                                        min: twelveHoursAgo.getTime(),
                                        max: now.getTime(),
                                    });
                                }}
                                className="text-red-500 hover:text-red-700 text-sm underline ml-2"
                            >
                                Clear
                            </button>
                        )}
                    </div>
                </header>


                <div className="bg-white p-6 rounded-lg shadow-md h-[80vh]">
                    <Chart type='bar' options={chartOptions} data={chartData} plugins={[hourGridPlugin]} />
                </div>
            </div >
        </div >
    );
}

export default App;
