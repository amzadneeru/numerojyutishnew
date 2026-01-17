import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function SocialCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const userId = params.get('user_id');
    const email = params.get('email');
    if (token) {
      localStorage.setItem('authToken', token);
      if (userId) localStorage.setItem('userId', userId);
      if (email) localStorage.setItem('email', email);
      // Redirect to dashboard
      navigate('/dashboard');
    } else {
      // No token: redirect to login
      navigate('/login');
    }
  }, [navigate]);

  return (
    <div style={{display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center'}}>
      <p>Signing you in...</p>
    </div>
  );
}

export default SocialCallback;
