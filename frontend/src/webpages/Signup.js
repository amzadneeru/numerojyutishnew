import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import '../styles/Login.css';

function Signup() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });
  const [msg, setMsg] = useState('');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : 'https://your-production-api.example.com');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async () => {
    // Reset message
    setMsg('');

    // Validate inputs
    if (!formData.password || (!formData.email && !formData.phone)) {
      setMsg('Please enter either email or phone, and password');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setMsg('Passwords do not match');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: formData.email,
          phone: formData.phone,
          password: formData.password,
          confirm_password: formData.confirmPassword
        })
      });

      const data = await res.json();

      if (data.success) {
        // Store auth data
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('userId', data.user_id);
        if (data.email) localStorage.setItem('email', data.email);

        setMsg('Signup successful!');
        // Navigate to dashboard after brief delay
        setTimeout(() => navigate('/dashboard'), 1000);
      } else {
        setMsg(data.message || 'Signup failed. Please try again.');
      }
    } catch (error) {
      console.error('Signup error:', error);
      setMsg('Could not connect to server. Please try again later.');
    }
  };

  return (
    <div className="login-wrapper" style={{ background: '#F8F1FF' }}>
      <div className="login-box" style={{ maxWidth: '400px', padding: '2rem' }}>
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <h1 style={{ 
            fontSize: '2rem', 
            fontWeight: 'bold',
            marginBottom: '0.5rem'
          }}>Sign Up</h1>
          <p style={{ 
            color: '#666',
            fontSize: '1rem'
          }}>Create new account.</p>
        </div>

        <input
          type="email"
          name="email"
          placeholder="Enter Your Email"
          value={formData.email}
          onChange={handleChange}
          className="login-input"
        />
        
        <div style={{ 
          margin: '1rem 0',
          textAlign: 'center',
          color: '#666'
        }}>Or</div>

        <input
          type="tel"
          name="phone"
          placeholder="Enter Your Phone"
          value={formData.phone}
          onChange={handleChange}
          className="login-input"
        />

        <input
          type="password"
          name="password"
          placeholder="Set a New Password"
          value={formData.password}
          onChange={handleChange}
          className="login-input"
          style={{ marginTop: '1rem' }}
        />

        <input
          type="password"
          name="confirmPassword"
          placeholder="Reenter New Password"
          value={formData.confirmPassword}
          onChange={handleChange}
          className="login-input"
        />

        <button 
          onClick={handleSubmit} 
          className="login-button"
          style={{
            background: 'linear-gradient(to right, #F4B555, #9C3B9C)',
            marginTop: '1.5rem'
          }}
        >
          Continue
        </button>

        <div style={{ 
          marginTop: '1.5rem',
          textAlign: 'center',
          color: '#666'
        }}>
          Or, sign in using
        </div>

        <div style={{ 
          display: 'flex', 
          gap: '1rem',
          marginTop: '1rem',
          justifyContent: 'center'
        }}>
          <button 
            onClick={() => {/* TODO: Implement Facebook login */}} 
            className="social-button"
            style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid #ddd' }}
          >
            Facebook
          </button>
          <button 
            onClick={() => {/* TODO: Implement Google login */}} 
            className="social-button"
            style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid #ddd' }}
          >
            Google
          </button>
        </div>

        {msg && (
          <div style={{ 
            marginTop: '1rem',
            textAlign: 'center',
            color: msg.includes('successful') ? 'green' : 'red'
          }}>
            {msg}
          </div>
        )}
      </div>
    </div>
  );
}

export default Signup;