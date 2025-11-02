// src/components/Login.js
import React, { useState } from 'react';
import '../styles/Login.css';
import { useNavigate, Link } from 'react-router-dom';


function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [showForgot, setShowForgot] = useState(false);
  
  const [newPassword, setNewPassword] = useState('');
  const [forgotMsg, setForgotMsg] = useState('');
  
  const navigate = useNavigate();
  // Prefer an explicit REACT_APP_API_URL for deployed builds.
  // While developing locally (NODE_ENV === 'development') use localhost.
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : 'https://your-production-api.example.com');

  const handleLogin = async () => {
    if (!username || !password) {
      setMsg("Please enter username and password.");
      return;
    }
    try {
  const res = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      
      if (data.success) {
        // store token and user info for authenticated requests
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('userId', data.user_id);
        localStorage.setItem('email', data.email);
        setMsg('Login successful!');
        // Navigate to dashboard after successful login
        setTimeout(() => navigate('/dashboard'), 1000);
      } else {
        setMsg(data.message || 'Invalid credentials');
      }
    } catch (error) {
      console.error('Login error:', error);
      setMsg("Could not connect to server. Please try again later.");
    }
  };

  

  const handleForgotPassword = async () => {
    if (!username || !newPassword) {
      setForgotMsg('Please enter your username and new password.');
      return;
    }
    try {
  const res = await fetch(`${API_URL}/api/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, new_password: newPassword }),
      });
      const data = await res.json();
      if (data.success) {
        setForgotMsg('Password updated successfully! You can now log in.');
      } else {
        setForgotMsg(data.message || 'Failed to update password.');
      }
    } catch (error) {
      setForgotMsg('Could not connect to server.');
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-box">
        <h1 className="login-title">Login</h1>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="login-input"
        />
        {!showForgot && (
          <>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="login-input"
            />
            <button onClick={handleLogin} className="login-button">Log In</button>
            <div style={{display: 'flex', gap: '12px', alignItems: 'center'}}>
              <Link to="/forgot-password" className="forgot-link">Forgot Password?</Link>
              <Link to="/register" className="forgot-link">Create account</Link>
            </div>
            {msg && <p className="login-msg">{msg}</p>}
          </>
        )}
        
        {showForgot && (
          <div className="forgot-password-form">
            <input
              type="password"
              placeholder="New Password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              className="login-input"
            />
            <button onClick={handleForgotPassword} className="login-button">Reset Password</button>
            <button className="forgot-link" onClick={() => { setShowForgot(false); setForgotMsg(''); }}>Back to Login</button>
            {forgotMsg && <p className="login-msg">{forgotMsg}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export default Login;
