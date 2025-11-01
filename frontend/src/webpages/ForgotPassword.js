import React, { useState } from 'react';
import '../styles/Login.css';
import { useNavigate } from 'react-router-dom';
import '../App.css';
function ForgotPassword() {
  const [username, setUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [msg, setMsg] = useState('');
  const navigate = useNavigate();

  const handleForgotPassword = async () => {
    if (!username || !newPassword) {
      setMsg('Please enter your username and new password.');
      return;
    }
    try {
      //const res = await fetch('http://localhost:5000/api/forgot-password', {
      const res = await fetch('https://numerojyotish.onrender.com/api/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, new_password: newPassword }),
      });
      const data = await res.json();
      if (data.success) {
        setMsg('Password updated successfully! You can now log in.');
        setTimeout(() => navigate('/'), 2000);
      } else {
        setMsg(data.message || 'Failed to update password.');
      }
    } catch (error) {
      setMsg('Could not connect to server.');
    }
  };

  return (
     <div className="hero-wrapper">
      <div className="content-box">
        <img src="/logo.png" alt="Logo" className="logo-image" />
        <h2 className="subtitle">TRADE PROGRAM</h2>
          <h1 className="login-title">Forgot Password</h1>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="login-input"
            />
            <input
              type="password"
              placeholder="New Password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              className="login-input"
            />
            <button onClick={handleForgotPassword} className="login-button">Reset Password</button>
                    <button className="forgot-link" onClick={() => navigate('/')}>Back to Login</button>
            {msg && <p className="login-msg">{msg}</p>}
          </div>
        </div>
   
  );
}

export default ForgotPassword;
