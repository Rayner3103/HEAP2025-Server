import React from 'react';

const Home = () => {
    const handleButtonClick = () => {
        console.log('Button clicked!');
        // get from server
        fetch('http://localhost:5000/api/example')
            .then(response => response.json())
            .then(data => console.log(data))
            .catch(error => console.error('Error fetching data:', error));
    }

    return (
        <div>
            <h1>Welcome to the Home Page</h1>
            <p>This is a simple home page component.</p>
            <button onClick={handleButtonClick}>Test</button>
        </div>
    )
}

export default Home;