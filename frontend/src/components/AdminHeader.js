import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import '../styles/AdminHeader.css';

function AdminHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const userEmail = localStorage.getItem('email') || 'Admin';
  const userInitial = userEmail.charAt(0).toUpperCase();

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    localStorage.removeItem('userRole');
    localStorage.removeItem('isAdmin');
    navigate('/login');
  };

  const menuItems = [
    { label: 'Admin Dashboard', path: '/admin/dashboard' },
    { label: 'Product Master', path: '/admin/productmaster' },
    { label: 'Astrologer Master', path: '/admin/astrologermaster' },
    { label: 'Booking Charges', path: '/admin/booking-charges' }
  ];

  return (
    <header className="admin-header">
      <div className="admin-header-left" onClick={() => navigate('/admin/dashboard')} role="button" tabIndex={0}>
        <div className="admin-logo">NUMRO JYOTISH</div>
        <span className="admin-badge">Admin</span>
      </div>

      <nav className="admin-nav">
        {menuItems.map((item) => (
          <button
            key={item.path}
            className={`admin-nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="admin-user-menu">
        <button className="admin-user-btn" onClick={() => setShowUserMenu((prev) => !prev)}>
          {userInitial} ▼
        </button>

        {showUserMenu && (
          <div className="admin-user-dropdown">
            <div className="admin-user-email">{userEmail}</div>
            <button onClick={() => navigate('/dashboard')}>User Dashboard</button>
            <button onClick={() => navigate('/my-consultation-bookings')}>My Consultations</button>
            <button className="logout" onClick={handleLogout}>Logout</button>
          </div>
        )}
      </div>
    </header>
  );
}

export default AdminHeader;
