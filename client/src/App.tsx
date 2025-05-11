import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './views/home/Home';
import OtherPage from './views/other/OtherPage'; // create this component as needed
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/other" element={<OtherPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;