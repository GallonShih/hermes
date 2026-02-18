import React from 'react';
import { Link, useSearchParams, useParams } from 'react-router-dom';
import Navigation from '../../components/common/Navigation';
import AuthorDetailContent from './AuthorDetailContent';

const AuthorPage = () => {
    const { authorId } = useParams();
    const [searchParams] = useSearchParams();

    const initialStartTime = searchParams.get('start_time');
    const initialEndTime = searchParams.get('end_time');

    return (
        <div className="min-h-screen font-sans text-gray-900">
            <div className="max-w-7xl mx-auto p-4 md:p-8">
                <div className="flex justify-between items-center mb-6 relative">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl sm:text-3xl font-bold text-white drop-shadow-lg">Author Profile</h1>
                        <Link to="/" className="text-sm text-white/90 underline hover:text-white">回 Dashboard</Link>
                    </div>
                    <Navigation />
                </div>

                <div className="glass-card rounded-2xl p-6">
                    <AuthorDetailContent
                        authorId={authorId}
                        initialStartTime={initialStartTime}
                        initialEndTime={initialEndTime}
                        showOpenInNewPage={false}
                    />
                </div>
            </div>
        </div>
    );
};

export default AuthorPage;
