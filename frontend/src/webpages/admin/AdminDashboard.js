import React from 'react';
import { useNavigate } from 'react-router-dom';
import AdminHeader from '../../components/AdminHeader';
import '../../styles/dashboard.css';

function AdminDashboard() {
  const navigate = useNavigate();

  const adminCards = [
    {
      path: '/admin/productmaster',
      icon: '📦',
      label: 'Product Master',
      desc: 'Manage products, categories, pricing, taxes, images and inventory'
    },
    {
      path: '/admin/astrologermaster',
      icon: '🔮',
      label: 'Astrologer Master',
      desc: 'Manage astrologer profiles, verification, fee, and details'
    },
    {
      path: '/admin/booking-charges',
      icon: '📅',
      label: 'Booking Charges',
      desc: 'Manage astrologer consultation charges, payment and booking status'
    },
    {
      path: '/admin/enquiries',
      icon: '📝',
      label: 'Enquiry Management',
      desc: 'View all enquiries and update status and admin comments'
    }
  ];

  return (
    <div className="dashboard-container">
      <AdminHeader />
      <main className="dashboard-main">
        <div className="welcome-section">
          <h2>Admin Dashboard</h2>
          <p>Access all admin management tools from one place</p>
        </div>

        <div className="menu-grid">
          {adminCards.map((item) => (
            <div
              key={item.path}
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
      </main>
    </div>
  );
}

export default AdminDashboard;
