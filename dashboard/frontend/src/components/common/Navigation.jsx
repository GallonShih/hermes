import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    ChartBarIcon,
    PlayIcon,
    ArrowTrendingUpIcon,
    Cog6ToothIcon,
    Bars3Icon,
    XMarkIcon,
} from '@heroicons/react/24/outline';

const navItems = [
    { path: '/', label: 'Dashboard', icon: ChartBarIcon },
    { path: '/playback', label: 'Playback', icon: PlayIcon },
    { path: '/trends', label: 'Trends', icon: ArrowTrendingUpIcon },
    { path: '/admin', label: 'Admin', icon: Cog6ToothIcon },
];

const Navigation = () => {
    const location = useLocation();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const isActive = (path) => location.pathname === path;

    return (
        <>
            {/* Desktop Navigation */}
            <div className="hidden md:flex gap-2 lg:gap-3">
                {navItems.map(({ path, label, icon: Icon }) => (
                    <Link
                        key={path}
                        to={path}
                        className={`flex items-center gap-1.5 lg:gap-2 px-3 lg:px-4 py-2 font-semibold rounded-xl transition-all duration-200 cursor-pointer ${
                            isActive(path)
                                ? 'bg-white/90 text-indigo-700 shadow-lg hover:bg-white hover:shadow-xl backdrop-blur-sm border border-white/50'
                                : 'glass-button text-gray-700'
                        }`}
                    >
                        <Icon className="w-5 h-5" />
                        <span className="hidden lg:inline">{label}</span>
                    </Link>
                ))}
            </div>

            {/* Mobile Menu Button */}
            <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 glass-button rounded-xl cursor-pointer"
                aria-label="Toggle menu"
            >
                {mobileMenuOpen ? (
                    <XMarkIcon className="w-6 h-6 text-gray-700" />
                ) : (
                    <Bars3Icon className="w-6 h-6 text-gray-700" />
                )}
            </button>

            {/* Mobile Menu Dropdown */}
            {mobileMenuOpen && (
                <div className="absolute top-full right-0 mt-2 w-48 glass-card rounded-xl shadow-xl z-50 md:hidden overflow-hidden">
                    {navItems.map(({ path, label, icon: Icon }) => (
                        <Link
                            key={path}
                            to={path}
                            onClick={() => setMobileMenuOpen(false)}
                            className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                                isActive(path)
                                    ? 'bg-indigo-100 text-indigo-700 font-semibold'
                                    : 'text-gray-700 hover:bg-gray-100'
                            }`}
                        >
                            <Icon className="w-5 h-5" />
                            <span>{label}</span>
                        </Link>
                    ))}
                </div>
            )}
        </>
    );
};

export default Navigation;
