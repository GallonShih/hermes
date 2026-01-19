import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    TimeScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import 'chartjs-adapter-date-fns';

// Register all necessary components including Filler
export const registerChartComponents = () => {
    ChartJS.register(
        CategoryScale,
        LinearScale,
        TimeScale,
        PointElement,
        LineElement,
        BarElement,
        Title,
        Tooltip,
        Legend,
        Filler
    );
};

// Shared Hour Grid Plugin
export const hourGridPlugin = {
    id: 'hourGrid',
    beforeDraw: (chart) => {
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;

        // Safety check
        if (!xAxis) return;

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
