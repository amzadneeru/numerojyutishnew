// src/components/Login.js
import React, { useState } from 'react';
import '../styles/Login.css';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [emailPhone, setEmailPhone] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [isOtpMode, setIsOtpMode] = useState(false);
  
  const [newPassword, setNewPassword] = useState('');
  const [forgotMsg, setForgotMsg] = useState('');
  
  const navigate = useNavigate();
  // Prefer an explicit REACT_APP_API_URL for deployed builds.
  // While developing locally (NODE_ENV === 'development') use localhost.
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : 'https://your-production-api.example.com');

  const handleLogin = async () => {
    if (!emailPhone || !password) {
      setMsg("Please enter email/phone and password.");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: emailPhone, password }),
      });
      const data = await res.json();
      
      if (data.success) {
        // store token and user info for authenticated requests
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('userId', data.user_id);
        localStorage.setItem('email', data.email);
        if (data.user_role || data.role) {
          localStorage.setItem('userRole', data.user_role || data.role);
        }
        if (typeof data.is_admin !== 'undefined') {
          localStorage.setItem('isAdmin', String(data.is_admin));
        }

        console.info('Login successful:', data.user_id);
        setMsg('Login successful!');
        // Navigate to products page after successful login
        setTimeout(() => navigate('/products'), 1000);
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

  const handleOtpLogin = () => {
    // TODO: Implement OTP login functionality
    console.log('OTP login clicked');
  };

  return (
    <div className="login-wrapper" style={{ background: '#F8F1FF', minHeight: '100vh', padding: '20px' }}>
      <div className="login-box" style={{ 
        maxWidth: '400px', 
        margin: '0 auto',
        padding: '2rem',
        background: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{ 
          fontSize: '24px',
          marginBottom: '8px',
          fontWeight: 'bold'
        }}>Sign In</h1>
        <p style={{
          color: '#666',
          marginBottom: '24px'
        }}>Access your account.</p>

        <input
          type="text"
          placeholder="Email/Phone"
          value={emailPhone}
          onChange={(e) => setEmailPhone(e.target.value)}
          className="login-input"
          style={{
            width: '100%',
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            marginBottom: '12px'
          }}
        />

        {!isOtpMode && (
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="login-input"
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              marginBottom: '16px'
            }}
          />
        )}

        <button 
          onClick={isOtpMode ? handleOtpLogin : handleLogin} 
          className="login-button"
          style={{
            width: '100%',
            padding: '12px',
            border: 'none',
            borderRadius: '4px',
            background: 'linear-gradient(to right, #F4B555, #9C3B9C)',
            color: 'white',
            fontWeight: 'bold',
            cursor: 'pointer',
            marginBottom: '12px'
          }}
        >
          Sign In
        </button>

        <button 
          onClick={() => setIsOtpMode(!isOtpMode)} 
          style={{
            width: '100%',
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            background: '#F8F1FF',
            color: '#333',
            cursor: 'pointer',
            marginBottom: '24px'
          }}
        >
          Sign In Using {isOtpMode ? 'Password' : 'OTP'}
        </button>

        {msg && <p style={{ color: msg.includes('successful') ? 'green' : 'red', textAlign: 'center', margin: '12px 0' }}>{msg}</p>}

        <div style={{ textAlign: 'center', color: '#666', marginBottom: '16px' }}>Or, sign in using</div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button
            onClick={() => { window.location.href = `${API_URL}/api/auth/facebook`; }}
            style={{
              flex: 1,
              padding: '10px',
              border: '1px solid #1877F2',
              borderRadius: '4px',
              background: 'white',
              color: '#1877F2',
              cursor: 'pointer'
            }}
          >
            Facebook
          </button>
          <button
            onClick={() => { window.location.href = `${API_URL}/api/auth/google`; }}
            style={{
              flex: 1,
              padding: '10px',
              border: '1px solid #DB4437',
              borderRadius: '4px',
              background: 'white',
              color: '#DB4437',
              cursor: 'pointer'
            }}
          >
            Google
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
