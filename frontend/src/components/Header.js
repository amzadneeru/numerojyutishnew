import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Header.css';

function Header() {
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [expandedMenu, setExpandedMenu] = useState(null);

  // Get user info from localStorage
  const userEmail = localStorage.getItem('email') || 'Guest';
  const userId = localStorage.getItem('userId');
  const userInitials = userEmail.charAt(0).toUpperCase();
  const authToken = localStorage.getItem('authToken');

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    localStorage.removeItem('userRole');
    localStorage.removeItem('isAdmin');
    setShowUserMenu(false);
    navigate('/login');
  };

  const handleNavigation = (path) => {
    navigate(path);
    setShowMobileMenu(false);
    setShowUserMenu(false);
    setExpandedMenu(null);
  };

  const toggleSubmenu = (menu) => {
    setExpandedMenu(expandedMenu === menu ? null : menu);
  };

  return (
    <header className="header">
      {/* Top Bar */}
      <div className="header-top">
        <div className="header-container">
          {/* Logo */}
          <div className="logo-section" onClick={() => handleNavigation('/')}>
            <div className="logo">
              <span className="logo-text">NUMRO</span>
              <span className="logo-subtext">JYOTISH</span>
            </div>
          </div>

          {/* Central Navigation */}
          <nav className={`nav-menu ${showMobileMenu ? 'active' : ''}`}>
            {/* Home */}
            <button className="nav-item" onClick={() => handleNavigation('/')}>
              🏠 Home
            </button>

            {/* Products Dropdown */}
            <div className="nav-item-group">
              <button 
                className="nav-item dropdown-toggle"
                onClick={() => toggleSubmenu('products')}
              >
                📦 Products
                <span className="dropdown-arrow">▼</span>
              </button>
              {expandedMenu === 'products' && (
                <div className="dropdown-submenu">
                  <button onClick={() => handleNavigation('/products')}>All Products</button>
                  <button onClick={() => handleNavigation('/products?category=numerology')}>Numerology Readings</button>
                  <button onClick={() => handleNavigation('/products?category=astrology')}>Astrology Services</button>
                  <button onClick={() => handleNavigation('/products?category=books')}>Books & Guides</button>
                </div>
              )}
            </div>

            {/* Services Dropdown */}
            <div className="nav-item-group">
              <button 
                className="nav-item dropdown-toggle"
                onClick={() => toggleSubmenu('services')}
              >
                ✨ Services
                <span className="dropdown-arrow">▼</span>
              </button>
              {expandedMenu === 'services' && (
                <div className="dropdown-submenu">
                  <button onClick={() => handleNavigation('/consult-astrologers')}>
                    Consult Astrologers
                  </button>
                  {userId && (
                    <button onClick={() => handleNavigation('/my-consultation-bookings')}>
                      My Consultation Bookings
                    </button>
                  )}
                  <button onClick={() => handleNavigation('/subscription-plan')}>
                    Subscription Plans
                  </button>
                  <button onClick={() => handleNavigation('/shopping')}>
                    Online Store
                  </button>
                </div>
              )}
            </div>

            {/* Consultation Dropdown */}
            <div className="nav-item-group">
              <button
                className="nav-item dropdown-toggle"
                onClick={() => toggleSubmenu('consultation')}
              >
                📅 Consultation
                <span className="dropdown-arrow">▼</span>
              </button>
              {expandedMenu === 'consultation' && (
                <div className="dropdown-submenu">
                  <button onClick={() => handleNavigation('/consult-astrologers')}>
                    Book Consultation Slot
                  </button>
                  {userId && (
                    <button onClick={() => handleNavigation('/my-consultation-bookings')}>
                      My Consultation Bookings
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Astrologers */}
            <button 
              className="nav-item" 
              onClick={() => handleNavigation('/consult-astrologers')}
            >
              ⭐ Astrologers
            </button>

            {/* Plans */}
            <button 
              className="nav-item" 
              onClick={() => handleNavigation('/subscription-plan')}
            >
              💳 Plans
            </button>

            {/* Dashboard - Only show if logged in */}
            {userId && (
              <button 
                className="nav-item dashboard-btn" 
                onClick={() => handleNavigation('/dashboard')}
              >
                📊 Dashboard
              </button>
            )}

          </nav>

          {/* Right Section */}
          <div className="header-right">
            {/* Auth Buttons / User Menu */}
            {authToken ? (
              <div className="user-menu-container">
                <button
                  className="user-button"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                >
                  <span className="user-initial">{userInitials}</span>
                  <span className="user-dropdown-arrow">▼</span>
                </button>

                {showUserMenu && (
                  <div className="dropdown-menu">
                    <div className="dropdown-header">
                      <span className="user-email">{userEmail}</span>
                      <span className="user-status">Active</span>
                    </div>
                    <div className="dropdown-divider"></div>

                    <button
                      className="dropdown-item"
                      onClick={() => handleNavigation('/dashboard')}
                    >
                      📊 Dashboard
                    </button>

                    <button
                      className="dropdown-item"
                      onClick={() => handleNavigation('/consult-astrologers')}
                    >
                      ⭐ Consult Astrologers
                    </button>

                    <button
                      className="dropdown-item"
                      onClick={() => handleNavigation('/my-consultation-bookings')}
                    >
                      📅 My Consultation Bookings
                    </button>

                    <button
                      className="dropdown-item"
                      onClick={() => handleNavigation('/shopping')}
                    >
                      🛍️ Shopping Cart
                    </button>

                    <div className="dropdown-divider"></div>

                    <button
                      className="dropdown-item"
                      onClick={() => handleNavigation('/subscription-plan')}
                    >
                      💳 Manage Subscription
                    </button>

                    <div className="dropdown-divider"></div>

                    <button
                      className="dropdown-item logout"
                      onClick={handleLogout}
                    >
                      🚪 Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="auth-buttons">
                <button
                  className="btn-login"
                  onClick={() => handleNavigation('/login')}
                >
                  Sign In
                </button>
                <button
                  className="btn-signup"
                  onClick={() => handleNavigation('/signup')}
                >
                  Sign Up
                </button>
              </div>
            )}

            {/* Mobile Menu Toggle */}
            <button
              className={`mobile-menu-toggle ${showMobileMenu ? 'active' : ''}`}
              onClick={() => setShowMobileMenu(!showMobileMenu)}
              aria-label="Toggle mobile menu"
            >
              <span></span>
              <span></span>
              <span></span>
            </button>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="header-search">
        <div className="header-container">
          <div className="search-wrapper">
            <input
              type="text"
              placeholder="Search products, astrologers..."
              className="search-input"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  const query = e.target.value;
                  navigate(`/products?search=${encodeURIComponent(query)}`);
                }
              }}
            />
            <button className="search-btn">🔍</button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
