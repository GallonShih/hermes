import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './components/common/Toast';
import Dashboard from './features/dashboard/Dashboard';
import AdminPanel from './features/admin/AdminPanel';
import PlaybackPage from './features/playback/PlaybackPage';
import TrendsPage from './features/trends/TrendsPage';

function App() {
    return (
        <ToastProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/admin" element={<AdminPanel />} />
                    <Route path="/playback" element={<PlaybackPage />} />
                    <Route path="/trends" element={<TrendsPage />} />
                </Routes>
            </BrowserRouter>
        </ToastProvider>
    );
}

export default App;
