import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate();
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/api/login`, {      
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        setStatus('Login successful');
        navigate('/dashboard');
      } else {
        setStatus(data.message || 'Login failed');
      }
    } catch (err) {
      setStatus('Error connecting to backend');
    }
  };

  return (
    <div className="hero-wrapper">
      <div className="content-box">
        <img src="/logo.png" alt="Logo" className="logo-image" />
        <h2 className="subtitle">TRADE PROGRAM</h2>

        <form className="auth-form" onSubmit={handleLogin}>
          <input
            type="text"
            placeholder="Username"
            className="auth-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button type="submit" className="cta-button full-width">Log In</button>

          <div className="forgot-wrapper">
            <span
              className="forgot-below smallest-text"
              style={{ cursor: 'pointer', color: '#a8652b', textDecoration: 'underline' }}
              onClick={() => navigate('/forgot-password')}
            >
              Forgot Password?
            </span>
          </div>

          <button
            type="button"
            className="cta-button full-width secondary"
            onClick={() => navigate('/register')}
          >
            Join Now
          </button>
        </form>

        {status && <p style={{ marginTop: '10px', color: '#333', fontSize: '14px' }}>{status}</p>}
      </div>
    </div>
  );
}

export default App;
