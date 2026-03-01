import React from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './components/Header';
import './styles/dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const userEmail = localStorage.getItem('email') || 'User';

  const menuItems = [
    { path: '/shopping', icon: '🛍️', label: 'Online Store', desc: 'Browse and purchase products' },
    { path: '/products', icon: '📦', label: 'Products', desc: 'View all available products' },
    { path: '/consult-astrologers', icon: '⭐', label: 'Consult Astrologers', desc: 'Connect with expert astrologers' },
    { path: '/subscription-plan', icon: '💳', label: 'Subscription Plans', desc: 'Manage your subscription' }
  ];

  return (
    <div className="dashboard-container">
      <Header />

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