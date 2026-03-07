import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/MySubscriptions.css';

function MySubscriptions() {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [subscriptions, setSubscriptions] = useState([]);
  const [plansWithPricing, setPlansWithPricing] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSubscriptions();
    fetchPlansWithPricing();
  }, []);

  const fetchSubscriptions = async () => {
    if (!userId || !authToken) {
      setError('Please login to view your subscriptions');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/subscriptions/my?user_id=${userId}`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.message || 'Failed to load subscriptions');
        return;
      }

      setSubscriptions(data.data || []);
    } catch (err) {
      setError('Unable to load subscriptions');
    } finally {
      setLoading(false);
    }
  };

  const fetchPlansWithPricing = async () => {
    try {
      const res = await fetch(`${API_URL}/api/subscription-plans-with-pricing?country_code=IN`);
      const data = await res.json();
      if (!res.ok || !data.success) {
        return;
      }
      setPlansWithPricing(data.data || []);
    } catch (err) {
      // no-op; upgrade button will be disabled gracefully if pricing cannot be loaded
    }
  };

  const formatDate = (value) => {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: '2-digit'
    });
  };

  const cycleLabel = (billingCycleId) => {
    if (Number(billingCycleId) === 2) return 'Yearly';
    if (Number(billingCycleId) === 1) return 'Monthly';
    return '-';
  };

  const getUpgradeCandidate = (sub) => {
    const sorted = [...plansWithPricing].sort((a, b) => Number(a.plan_id) - Number(b.plan_id));
    const currentPlanId = Number(sub.plan_id);
    const currentCycleId = Number(sub.billing_cycle_id);

    let targetPlan = sorted.find((plan) => Number(plan.plan_id) > currentPlanId);
    if (!targetPlan) {
      targetPlan = sorted.find((plan) => Number(plan.plan_id) !== currentPlanId);
    }
    if (!targetPlan) return null;

    const targetPricing = (targetPlan.pricing || []).find((p) => Number(p.billing_cycle_id) === currentCycleId)
      || (targetPlan.pricing || [])[0];
    if (!targetPricing) return null;

    const billingPeriod = Number(targetPricing.billing_cycle_id) === 2 ? 'yearly' : 'monthly';

    return {
      plan_id: Number(targetPlan.plan_id),
      plan_name: targetPlan.plan_name,
      billing_cycle_id: Number(targetPricing.billing_cycle_id),
      billing_period: billingPeriod,
      price: Number(targetPricing.final_price || 0),
      country_code: 'IN'
    };
  };

  const handleUpgrade = (sub) => {
    const selectedPlan = getUpgradeCandidate(sub);
    if (!selectedPlan) {
      setError('No upgrade option available right now. Please try another plan from Subscription Plans.');
      return;
    }

    navigate('/subscription-payment', {
      state: { selectedPlan }
    });
  };

  return (
    <div className="my-subscriptions-page">
      <Header />

      <main className="my-subscriptions-main">
        <div className="my-subscriptions-head">
          <h1>My Subscriptions</h1>
          <button className="my-subscriptions-btn" onClick={() => navigate('/subscription-plan')}>
            + Subscribe New Plan
          </button>
        </div>

        {loading && <p className="my-subscriptions-loading">Loading subscriptions...</p>}
        {error && <p className="my-subscriptions-error">{error}</p>}

        {!loading && !error && subscriptions.length === 0 && (
          <div className="my-subscriptions-empty">
            <p>No subscriptions found.</p>
            <button className="my-subscriptions-btn" onClick={() => navigate('/subscription-plan')}>
              Browse Plans
            </button>
          </div>
        )}

        {!loading && !error && subscriptions.length > 0 && (
          <div className="my-subscriptions-grid">
            {subscriptions.map((sub) => (
              <article key={sub.subscription_id} className="my-sub-card">
                <div className="my-sub-card-head">
                  <h3>{sub.plan_name || `Plan #${sub.plan_id}`}</h3>
                  <span className={`my-sub-badge ${String(sub.subscription_status || '').toLowerCase()}`}>
                    {sub.subscription_status || 'Unknown'}
                  </span>
                </div>

                <p><strong>Subscription ID:</strong> {sub.subscription_id}</p>
                <p><strong>Plan Code:</strong> {sub.plan_code || '-'}</p>
                <p><strong>Billing Cycle:</strong> {cycleLabel(sub.billing_cycle_id)}</p>
                <p><strong>Start Date:</strong> {formatDate(sub.start_date)}</p>
                <p><strong>End Date:</strong> {formatDate(sub.end_date)}</p>

                <div className="my-sub-payment">
                  <h4>Latest Payment</h4>
                  <p><strong>Payment ID:</strong> {sub.payment?.subscription_payment_id || '-'}</p>
                  <p><strong>Amount:</strong> ₹ {sub.payment?.amount ?? 0}</p>
                  <p><strong>Status:</strong> {sub.payment?.status || '-'}</p>
                  <p><strong>Paid On:</strong> {formatDate(sub.payment?.created_at)}</p>
                </div>

                <div className="my-sub-actions">
                  <button
                    className="my-sub-upgrade-btn"
                    onClick={() => handleUpgrade(sub)}
                    disabled={String(sub.subscription_status || '').toUpperCase() !== 'ACTIVE'}
                  >
                    Upgrade Plan
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default MySubscriptions;
