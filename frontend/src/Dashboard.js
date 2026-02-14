import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './styles/dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userEmail = localStorage.getItem('email') || 'User';
  const userInitials = userEmail.charAt(0).toUpperCase();

  const menuItems = [
    { path: '/shopping', icon: '🛍️', label: 'Online Store', desc: 'Browse and purchase products' },
    { path: '/products', icon: '📦', label: 'Products', desc: 'View all available products' },
    { path: '/subscription-plan', icon: '💳', label: 'Subscription Plans', desc: 'Manage your subscription' },
    { path: '/admin/productmaster', icon: '⚙️', label: 'Admin Panel', desc: 'Manage products & inventory' },
  ];

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    navigate('/login');
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="logo">
          <h1>NUMRO</h1>
          <h2>JYOTISH</h2>
        </div>
        <h3 className="page-title">Dashboard</h3>
        <div className="user-menu-container">
          <button
            className="user-button"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            {userInitials} ▼
          </button>
          {showUserMenu && (
            <div className="user-dropdown">
              <div className="dropdown-header">{userEmail}</div>
              <div className="dropdown-divider"></div>
              <button className="dropdown-item" onClick={() => navigate('/dashboard')}>
                📊 My Dashboard
              </button>
              <button className="dropdown-item" onClick={() => navigate('/shop')}>
                🛍️ Go to Store
              </button>
              <div className="dropdown-divider"></div>
              <button className="dropdown-item logout" onClick={handleLogout}>
                🚪 Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        <div className="welcome-section">
          <h2>Welcome, {userEmail.split('@')[0]}!</h2>
          <p>Choose what you'd like to do</p>
        </div>

        <div className="menu-grid">
          {menuItems.map((item, index) => (
            <div
              key={index}
              className="menu-card"
              onClick={() => navigate(item.path)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && navigate(item.path)}
            >
              <div className="menu-icon">{item.icon}</div>
              <h3>{item.label}</h3>
              <p>{item.desc}</p>
              <span className="arrow">→</span>
            </div>
          ))}
        </div>

        {/* Quick Stats */}
        <section className="quick-stats">
          <h3>Quick Stats</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">🛒</div>
              <div className="stat-content">
                <div className="stat-number">0</div>
                <div className="stat-label">Orders</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">💰</div>
              <div className="stat-content">
                <div className="stat-number">₹0</div>
                <div className="stat-label">Total Spent</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">📦</div>
              <div className="stat-content">
                <div className="stat-number">0</div>
                <div className="stat-label">Products</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">💳</div>
              <div className="stat-content">
                <div className="stat-number">-</div>
                <div className="stat-label">Plan</div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Dashboard;