import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';

function App() {
  const [emailPhone, setEmailPhone] = useState('');
  const [password, setPassword] = useState('');
  const [isOtpMode, setIsOtpMode] = useState(false);
  const [msg, setMsg] = useState('');
  const navigate = useNavigate();
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  const handleOtpLogin = async () => {
    try {
      const res = await fetch(`${API_URL}/api/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ emailPhone })
      });
      const data = await res.json();
      if (res.ok) {
        setMsg('OTP sent successfully');
        // Here you might want to navigate to an OTP verification page
        // navigate('/verify-otp');
      } else {
        setMsg(data.message || 'Failed to send OTP');
      }
    } catch (err) {
      setMsg('Error connecting to backend');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/api/login`, {      
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: emailPhone, password })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('userId', data.user_id);
        localStorage.setItem('email', data.email);

        console.info('Login successful:', data.user_id);
        setMsg('Login successful');
        navigate('/subscription-plan');
      } else {
        setMsg(data.message || 'Login failed');
      }
    } catch (err) {
      setMsg('Error connecting to backend');
    }
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

export default App;
