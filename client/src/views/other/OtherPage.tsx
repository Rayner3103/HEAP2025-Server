import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const OtherPage = () => {
    const location = useLocation();
    const serverData = location.state || {};

    const navigate = useNavigate();

    return (
        <div>
        <h1>Other Page</h1>
        <p>This is another page in the application.</p>
        {serverData ? (
            <div>
                <h2>Data from Server:</h2>
                <pre>{JSON.stringify(serverData, null, 2)}</pre>
            </div>
        ) : (
            <p>No data received from the server.</p>
        )}
        <button onClick={() => navigate('/')}>Go Back to Home</button>
        </div>
    );
}

export default OtherPage;