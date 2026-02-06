import React, { useState, useEffect, useCallback } from 'react';
import { fetchStreamInfo } from '../../api/streamInfo';

const REFRESH_INTERVAL = 60_000; // 60 seconds

function StatusBadge({ status }) {
    const config = {
        live: { label: 'LIVE', bg: 'bg-red-500', animate: true },
        upcoming: { label: 'UPCOMING', bg: 'bg-yellow-500', animate: false },
        none: { label: 'ENDED', bg: 'bg-gray-500', animate: false },
    };
    const { label, bg, animate } = config[status] || config.none;

    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-white text-xs font-bold ${bg}`}>
            {animate && (
                <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
                </span>
            )}
            {label}
        </span>
    );
}

function formatNumber(n) {
    if (n == null) return '--';
    return n.toLocaleString();
}

function StreamInfoBar() {
    const [stream, setStream] = useState(null);

    const load = useCallback(async () => {
        try {
            const data = await fetchStreamInfo();
            setStream(data.stream);
        } catch (err) {
            console.error('Failed to fetch stream info', err);
        }
    }, []);

    useEffect(() => {
        load();
        const id = setInterval(load, REFRESH_INTERVAL);
        return () => clearInterval(id);
    }, [load]);

    if (!stream) return null;

    const stats = stream.stats;
    const youtubeUrl = `https://www.youtube.com/watch?v=${stream.video_id}`;

    return (
        <div className="glass-card rounded-2xl mb-4 sm:mb-6 p-3 sm:p-4">
            <div className="flex items-start gap-3 sm:gap-4">
                {/* Thumbnail */}
                {stream.thumbnail_url && (
                    <a
                        href={youtubeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-shrink-0"
                    >
                        <img
                            src={stream.thumbnail_url}
                            alt={stream.title}
                            className="w-24 h-auto sm:w-36 rounded-lg object-cover shadow-sm hover:shadow-md transition-shadow"
                        />
                    </a>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                    {/* Row 1: Badge + Channel */}
                    <div className="flex items-center gap-2 mb-1">
                        <StatusBadge status={stream.live_broadcast_content} />
                        {stream.channel_title && (
                            <span className="text-sm font-semibold text-gray-700 truncate">
                                {stream.channel_title}
                            </span>
                        )}
                    </div>

                    {/* Row 2: Title */}
                    <a
                        href={youtubeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm sm:text-base font-medium text-gray-900 hover:text-blue-600 transition-colors line-clamp-2"
                    >
                        {stream.title}
                    </a>

                    {/* Row 3: Stats */}
                    {stats && (
                        <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-1.5 text-xs sm:text-sm text-gray-600">
                            {stats.concurrent_viewers != null && (
                                <span className="flex items-center gap-1">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                    <span className="font-medium">{formatNumber(stats.concurrent_viewers)}</span>
                                    <span className="hidden sm:inline">viewers</span>
                                </span>
                            )}
                            {stats.view_count != null && (
                                <span className="flex items-center gap-1">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span className="font-medium">{formatNumber(stats.view_count)}</span>
                                    <span className="hidden sm:inline">views</span>
                                </span>
                            )}
                            {stats.like_count != null && (
                                <span className="flex items-center gap-1">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                                    </svg>
                                    <span className="font-medium">{formatNumber(stats.like_count)}</span>
                                    <span className="hidden sm:inline">likes</span>
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default StreamInfoBar;
