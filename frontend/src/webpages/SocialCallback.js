import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';

function SocialCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const userId = params.get('user_id');
    const email = params.get('email');
    const userRole = params.get('user_role') || params.get('role');
    const isAdmin = params.get('is_admin');
    if (token) {
      localStorage.setItem('authToken', token);
      if (userId) localStorage.setItem('userId', userId);
      if (email) localStorage.setItem('email', email);
      if (userRole) localStorage.setItem('userRole', userRole);
      if (isAdmin !== null) localStorage.setItem('isAdmin', isAdmin);
      // Redirect to dashboard
      navigate('/dashboard');
    } else {
      // No token: redirect to login
      navigate('/login');
    }
  }, [navigate]);

  return (
    <div>
      <Header />
      <div style={{display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center'}}>
        <p>Signing you in...</p>
      </div>
    </div>
  );
}

export default SocialCallback;
