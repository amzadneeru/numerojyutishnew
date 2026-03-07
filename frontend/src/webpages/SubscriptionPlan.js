import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/SubscriptionPlan.css';

function SubscriptionPlan() {
  const navigate = useNavigate();
  const [billingPeriod, setBillingPeriod] = useState('monthly'); // 'monthly' or 'yearly'
  const [currentPlanIndex, setCurrentPlanIndex] = useState(0);
  const [expandedPlan, setExpandedPlan] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const userEmail = localStorage.getItem('email') || 'User';
  const userInitials = userEmail.charAt(0).toUpperCase();
  
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Fetch subscription plans with pricing from backend
  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoading(true);
        setError('');
        
        const res = await fetch(`${API_URL}/api/subscription-plans-with-pricing?country_code=IN`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (!res.ok) {
          throw new Error('Failed to fetch subscription plans');
        }
        
        const data = await res.json();
        
        if (data.success && data.data) {
          // Transform the API data to match our component structure
          const transformedPlans = data.data.map((plan, index) => ({
            id: plan.plan_id,
            code: plan.plan_code,
            name: plan.plan_name,
            description: plan.description,
            icon: ['🔮', '✨', '👑', '💎', '🌟'][index % 5], // Assign icons based on index
            pricing: plan.pricing.reduce((acc, p) => {
              if (p.billing_cycle_id === 1) {
                acc.monthlyPrice = p.final_price;
                acc.monthlyBasePrice = p.base_price;
                acc.monthlyTaxPercent = p.tax_percent;
                acc.monthlyTaxAmount = p.base_price * (p.tax_percent / 100);
              } else if (p.billing_cycle_id === 2) {
                acc.yearlyPrice = p.final_price;
                acc.yearlyBasePrice = p.base_price;
                acc.yearlyTaxPercent = p.tax_percent;
                acc.yearlyTaxAmount = p.base_price * (p.tax_percent / 100);
              }
              return acc;
            }, {}),
            features: [
              `Plan ID: ${plan.plan_id}`,
              `Code: ${plan.plan_code}`,
              'Standard features included',
              'Priority support available'
            ]
          }));
          
          setPlans(transformedPlans);
        } else {
          throw new Error(data.message || 'Invalid response format');
        }
      } catch (err) {
        console.error('Error fetching plans:', err);
        setError('Failed to load subscription plans. Please try again later.');
        // Fallback to empty plans array
        setPlans([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPlans();
  }, [API_URL]);

  const currentPlan = plans[currentPlanIndex];
  const price = currentPlan && currentPlan.pricing ? (
    billingPeriod === 'monthly' 
      ? currentPlan.pricing.monthlyPrice || 0
      : currentPlan.pricing.yearlyPrice || 0
  ) : 0;
  const totalPlans = plans.length;

  const handleNext = () => {
    setCurrentPlanIndex((prev) => (prev + 1) % (totalPlans || 1));
    setExpandedPlan(null);
  };

  const handlePrev = () => {
    setCurrentPlanIndex((prev) => (prev - 1 + (totalPlans || 1)) % (totalPlans || 1));
    setExpandedPlan(null);
  };

  const handleSubscribe = async () => {
    if (!currentPlan) {
      setError('No plan selected');
      return;
    }

    const userId = localStorage.getItem('userId');
    const authToken = localStorage.getItem('authToken');
    if (!userId || !authToken) {
      setError('Please login to continue with subscription');
      navigate('/');
      return;
    }

    setError('');
    navigate('/subscription-payment', {
      state: {
        selectedPlan: {
          plan_id: Number(currentPlan.id),
          plan_name: currentPlan.name,
          billing_cycle_id: billingPeriod === 'yearly' ? 2 : 1,
          billing_period: billingPeriod,
          price: Number(price || 0),
          country_code: 'IN'
        }
      }
    });
  };


    const handleProduct = async () => {
      // Navigate to products listing (show all products)
      navigate('/products');
    };

  const handleSkip = () => {
    // Skip subscription selection and go to products listing
    navigate('/subscription-plan');
  };

  const toggleDetails = () => {
    setExpandedPlan(expandedPlan === currentPlanIndex ? null : currentPlanIndex);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    localStorage.removeItem('selectedPlan');
    navigate('/login');
  };

  const handleMyAccount = () => {
    setShowUserMenu(false);
    // Navigate to account page (create this page later)
    navigate('/my-account');
  };

  const handleSettings = () => {
    setShowUserMenu(false);
    // Navigate to settings page
    navigate('/settings');
  };

  const handleMyProfile = () => {
    setShowUserMenu(false);
    // Navigate to registration wizard for editing profile
    navigate('/registration-wizard');
  };

  return (
    <div className="subscription-container">
      <Header />
      {/* Header */}
      <header className="subscription-header">
        <div className="logo">
          <h1>NUMRO</h1>
          <h2>JYOTISH</h2>
        </div>
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
              <button className="dropdown-item" onClick={handleMyProfile}>
                👤 My Profile
              </button>
              <button className="dropdown-item" onClick={handleMyAccount}>
                ℹ️ My Account
              </button>
              <button className="dropdown-item" onClick={handleSettings}>
                ⚙️ Settings
              </button>
              <button className="dropdown-item" onClick={handleProduct}>
                📊 Products
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
      <main className="subscription-main">
        <div className="subscription-content">
          {/* Welcome Message */}
          <div className="welcome-section">
            <h3>Excellent! Your profile is all set up.</h3>
            <p>Now choose a Subscription plan to get started.</p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading subscription plans...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="error-state">
              <p>❌ {error}</p>
            </div>
          )}

          {/* Plans Available */}
          {!loading && !error && plans.length > 0 && (
            <>
              {/* Billing Period Toggle */}
              <div className="billing-toggle">
                <span>Subscribe for</span>
                <div className="toggle-buttons">
                  <button
                    className={`toggle-btn ${billingPeriod === 'monthly' ? 'active' : ''}`}
                    onClick={() => setBillingPeriod('monthly')}
                  >
                    Monthly
                  </button>
                  <button
                    className={`toggle-btn ${billingPeriod === 'yearly' ? 'active' : ''}`}
                    onClick={() => setBillingPeriod('yearly')}
                  >
                    Yearly
                  </button>
                </div>
              </div>

              {/* Plan Card */}
              <div className={`plan-card ${expandedPlan === currentPlanIndex ? 'expanded' : ''}`}>
                <div className="plan-header">
                  <div className="plan-icon">{currentPlan?.icon}</div>
                  <h4>Plan {currentPlanIndex + 1}: {currentPlan?.name}</h4>
                </div>

                <div className="plan-pricing">
                  <span className="price">₹ {price.toLocaleString('en-IN')}</span>
            </div>

            <div className="plan-pricing-breakdown">
              <div className="price-row">
                <span className="label">Base Price:</span>
                <span className="base-price">₹ {(billingPeriod === 'monthly' 
                  ? currentPlan?.pricing.monthlyBasePrice || 0
                  : currentPlan?.pricing.yearlyBasePrice || 0
                ).toLocaleString('en-IN')}</span>
              </div>
              <div className="price-row">
                <span className="label">Tax ({(billingPeriod === 'monthly' 
                  ? currentPlan?.pricing.monthlyTaxPercent || 0
                  : currentPlan?.pricing.yearlyTaxPercent || 0
                )}%):</span>
                <span className="tax-amount">₹ {(billingPeriod === 'monthly' 
                  ? currentPlan?.pricing.monthlyTaxAmount || 0
                  : currentPlan?.pricing.yearlyTaxAmount || 0
                ).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
              <div className="price-row final">
                <span className="label final-label">Final Price:</span>
                <span className="final-price">₹ {price.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <p className="plan-description">{currentPlan.description}</p>

            {/* Expandable Details */}
            {expandedPlan === currentPlanIndex && (
              <div className="plan-features">
                <h5>Included Features:</h5>
                <ul>
                  {currentPlan.features.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Details Toggle Button */}
            <button className="details-button" onClick={toggleDetails}>
              Details <span className={`arrow ${expandedPlan === currentPlanIndex ? 'up' : 'down'}`}>▼</span>
            </button>
          </div>

          {/* Colored Banner */}
          <div className="banner"></div>

          {/* Action Buttons */}
          <div className="action-section">
            <button className="subscribe-btn" onClick={handleSubscribe}>
              Continue to Payment
            </button>
            <button className="skip-btn" onClick={handleSkip}>
              Skip for now
            </button>
          </div>

          {/* Navigation */}
          <div className="navigation">
            <button className="nav-arrow" onClick={handlePrev}>❮</button>
            <span className="plan-counter">{currentPlanIndex + 1} / {totalPlans}</span>
            <button className="nav-arrow" onClick={handleNext}>❯</button>
          </div>
            </>
          )}

          {/* No Plans Available */}
          {!loading && !error && plans.length === 0 && (
            <div className="empty-state">
              <p>No subscription plans available at the moment.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default SubscriptionPlan;
