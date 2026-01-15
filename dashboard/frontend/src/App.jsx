import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import AdminPanel from './components/Admin/AdminPanel';
import PlaybackPage from './components/PlaybackPage';

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
