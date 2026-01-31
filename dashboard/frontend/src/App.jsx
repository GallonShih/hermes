import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './features/dashboard/Dashboard';
import AdminPanel from './features/admin/AdminPanel';
import PlaybackPage from './features/playback/PlaybackPage';
import TrendsPage from './features/trends/TrendsPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/playback" element={<PlaybackPage />} />
                <Route path="/trends" element={<TrendsPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
