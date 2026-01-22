import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './features/dashboard/Dashboard';
import AdminPanel from './features/admin/AdminPanel';
import PlaybackPage from './features/playback/PlaybackPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/playback" element={<PlaybackPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
