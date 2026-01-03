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

    // Common Time Range (12 hours)
    // We calculate this on the frontend to sync the charts
    const now = new Date();
    const minTime = new Date(now.getTime() - 12 * 60 * 60 * 1000).getTime();
    const maxTime = now.getTime();

    // Fetch Viewer Stats
    const fetchViewers = async () => {
        try {
            // Fetch 12 hours of data to match comments
            const res = await fetch(`${API_BASE_URL}/api/stats/viewers?hours=12`);
            const data = await res.json();
            // data format: [{time: "ISO_STRING", count: 123}, ...]

            // Map to x, y for Chart.js
            const validData = data.map(d => ({
                x: new Date(d.time).getTime(),
                y: d.count
            }));

            setViewData(validData);
        } catch (err) {
            console.error("Failed to fetch viewers", err);
        }
    };

    // Fetch Comment Stats
    const fetchComments = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/stats/comments?hours=12`);
            const data = await res.json();
            // data format: [{hour: "ISO_STRING", count: 123}, ...]

            // Map to x, y for Chart.js
            const validData = data.map(d => ({
                x: new Date(d.hour).getTime(),
                y: d.count
            }));

            setCommentData(validData);

            // Flash effect logic
            setBarFlash(true);
            setTimeout(() => setBarFlash(false), 400);

        } catch (err) {
            console.error("Failed to fetch comments", err);
        }
    };

    // Polling Effect
    useEffect(() => {
        // Initial fetch
        fetchViewers();
        fetchComments();

        const intervalId = setInterval(() => {
            fetchViewers();
            fetchComments();
        }, 5000); // Poll every 5 seconds

        return () => clearInterval(intervalId);
    }, []);

    // Common Axis Config
    const timeAxisConfig = {
        type: 'time',
        time: {
            unit: 'hour',
            displayFormats: {
                hour: 'MM/dd HH:mm'
            }
        },
        min: minTime,
        max: maxTime,
        grid: {
            display: true,
        },
    };

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
                            // Floor to hour
                            const date = new Date(timestamp);
                            date.setMinutes(0, 0, 0);
                            const hourTime = date.getTime();

                            const comment = commentData.find(d => d.x === hourTime);
                            return comment ? `Hourly Comments: ${comment.y}` : 'Hourly Comments: 0';
                        }

                        // If hovering Comments (Bar), show Viewers at that time
                        if (item.dataset.type === 'bar') {
                            if (!viewData.length) return '';
                            // Find closest viewer data point
                            const closestViewer = viewData.reduce((prev, curr) => {
                                return (Math.abs(curr.x - timestamp) < Math.abs(prev.x - timestamp) ? curr : prev);
                            });

                            return closestViewer ? `Viewers: ${closestViewer.y}` : '';
                        }
                        return '';
                    }
                }
            },
        },
        scales: {
            x: timeAxisConfig,
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

    return (
        <div className="min-h-screen bg-gray-100 p-8">
            <div className="max-w-7xl mx-auto space-y-8">
                <header className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-800">Hermes 監控儀表板</h1>
                </header>

                <div className="bg-white p-6 rounded-lg shadow-md h-[80vh]">
                    <Chart type='bar' options={chartOptions} data={chartData} />
                </div>
            </div>
        </div>
    );
}

export default App;
