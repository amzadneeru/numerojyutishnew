import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/SubscriptionPayment.css';

function SubscriptionPayment() {
  const navigate = useNavigate();
  const location = useLocation();

  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');
  const authToken = localStorage.getItem('authToken');
  const userId = localStorage.getItem('userId');

  const [submitting, setSubmitting] = useState(false);
  const [loadingCurrent, setLoadingCurrent] = useState(false);
  const [error, setError] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('UPI');
  const [paymentReference, setPaymentReference] = useState('');
  const [activeSubscription, setActiveSubscription] = useState(null);
  const [upgradeOptions, setUpgradeOptions] = useState([]);

  const selectedPlan = useMemo(() => {
    if (location.state?.selectedPlan) {
      localStorage.setItem('pendingSubscriptionPlan', JSON.stringify(location.state.selectedPlan));
      return location.state.selectedPlan;
    }

    const fromStorage = localStorage.getItem('pendingSubscriptionPlan');
    if (!fromStorage) return null;

    try {
      return JSON.parse(fromStorage);
    } catch {
      return null;
    }
  }, [location.state]);

  useEffect(() => {
    if (!authToken || !userId) {
      setError('Please login to continue with payment');
      return;
    }

    if (!selectedPlan) {
      setError('No subscription plan selected. Please choose a plan first.');
      return;
    }

    fetchActiveSubscription();
  }, []);

  const fetchActiveSubscription = async () => {
    try {
      setLoadingCurrent(true);
      setError('');

      const res = await fetch(`${API_URL}/api/subscriptions/my?user_id=${Number(userId)}`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        setError(data.message || 'Could not verify existing subscriptions');
        return;
      }

      const active = (data.data || []).find((sub) => String(sub.subscription_status || '').toUpperCase() === 'ACTIVE');
      setActiveSubscription(active || null);
    } catch (err) {
      setError('Unable to verify existing subscription');
    } finally {
      setLoadingCurrent(false);
    }
  };

  const isSameAsCurrent = !!(
    activeSubscription &&
    Number(activeSubscription.plan_id) === Number(selectedPlan?.plan_id) &&
    Number(activeSubscription.billing_cycle_id) === Number(selectedPlan?.billing_cycle_id)
  );

  const isUpgrade = !!(activeSubscription && !isSameAsCurrent);

  const handleBackToPlans = () => {
    navigate('/subscription-plan');
  };

  const handleUpgradeChoice = (option) => {
    const billingPeriod = Number(option.billing_cycle_id) === 2 ? 'yearly' : 'monthly';
    navigate('/subscription-payment', {
      replace: true,
      state: {
        selectedPlan: {
          plan_id: Number(option.plan_id),
          plan_name: option.plan_name,
          billing_cycle_id: Number(option.billing_cycle_id),
          billing_period: billingPeriod,
          price: Number(option.final_price || 0),
          country_code: 'IN'
        }
      }
    });
  };

  const handlePayNow = async () => {
    if (!selectedPlan || !authToken || !userId) {
      setError('Missing user or plan details. Please reselect your plan.');
      return;
    }

    if (isSameAsCurrent) {
      setError('You already have this active subscription plan.');
      return;
    }

    try {
      setSubmitting(true);
      setError('');

      const res = await fetch(`${API_URL}/api/subscriptions/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({
          user_id: Number(userId),
          plan_id: Number(selectedPlan.plan_id),
          billing_cycle_id: Number(selectedPlan.billing_cycle_id),
          country_code: selectedPlan.country_code || 'IN',
          order_id: Date.now(),
          payment_id: Date.now() + 1,
          status: 'Paid',
          payment_method: paymentMethod,
          payment_reference: paymentReference || null,
          is_upgrade: isUpgrade
        })
      });

      const data = await res.json();

      if (res.status === 409 && data?.upgrade_required) {
        setError(data.message || 'You already have an active subscription. Please upgrade instead.');
        setUpgradeOptions(data?.data?.upgrade_options || []);
        setActiveSubscription(data?.data?.current_subscription || activeSubscription);
        return;
      }

      if (!res.ok || !data.success) {
        setError(data.message || 'Payment failed. Please try again.');
        return;
      }

      localStorage.setItem('selectedPlan', JSON.stringify({
        planId: selectedPlan.plan_id,
        planName: selectedPlan.plan_name,
        billingPeriod: selectedPlan.billing_period,
        price: selectedPlan.price,
        subscriptionId: data?.data?.subscription_id,
        subscriptionPaymentId: data?.data?.payment?.subscription_payment_id,
        subscriptionStatus: data?.data?.subscription_status,
        isUpgrade: !!data?.data?.is_upgrade
      }));
      localStorage.removeItem('pendingSubscriptionPlan');

      navigate('/my-subscriptions');
    } catch (err) {
      setError('Could not complete payment. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="subscription-payment-page">
      <Header />
      <main className="subscription-payment-main">
        <div className="subscription-payment-card">
          <h1>Subscription Payment</h1>

          {!selectedPlan && (
            <p className="payment-error">No plan selected. Go back and select a subscription plan.</p>
          )}

          {selectedPlan && (
            <>
              <div className="payment-summary">
                <h3>{selectedPlan.plan_name || `Plan #${selectedPlan.plan_id}`}</h3>
                <p><strong>Billing:</strong> {selectedPlan.billing_period === 'yearly' ? 'Yearly' : 'Monthly'}</p>
                <p><strong>Total Amount:</strong> ₹ {Number(selectedPlan.price || 0).toLocaleString('en-IN')}</p>
              </div>

              {loadingCurrent && <p className="payment-info">Checking your existing subscription...</p>}

              {!loadingCurrent && activeSubscription && (
                <div className="current-subscription-box">
                  <p><strong>Current Active Subscription:</strong> Plan #{activeSubscription.plan_id} ({Number(activeSubscription.billing_cycle_id) === 2 ? 'Yearly' : 'Monthly'})</p>
                  {isSameAsCurrent ? (
                    <p className="payment-warning">You already have this active plan. Choose another plan to upgrade.</p>
                  ) : (
                    <p className="payment-info">This payment will upgrade your existing active subscription.</p>
                  )}
                </div>
              )}

              <div className="payment-form">
                <label htmlFor="paymentMethod">Payment Method</label>
                <select
                  id="paymentMethod"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                >
                  <option value="UPI">UPI</option>
                  <option value="CARD">Credit/Debit Card</option>
                  <option value="NETBANKING">Net Banking</option>
                </select>

                <label htmlFor="paymentReference">Payment Reference (Optional)</label>
                <input
                  id="paymentReference"
                  type="text"
                  value={paymentReference}
                  onChange={(e) => setPaymentReference(e.target.value)}
                  placeholder="Enter txn/ref id"
                />
              </div>
            </>
          )}

          {error && <p className="payment-error">{error}</p>}

          {upgradeOptions.length > 0 && (
            <div className="upgrade-options-box">
              <h4>Available Upgrade Options</h4>
              <div className="upgrade-options-list">
                {upgradeOptions.map((option, idx) => (
                  <button key={`${option.plan_id}-${option.billing_cycle_id}-${idx}`} onClick={() => handleUpgradeChoice(option)}>
                    {option.plan_name} - {Number(option.billing_cycle_id) === 2 ? 'Yearly' : 'Monthly'} (₹ {Number(option.final_price || 0).toLocaleString('en-IN')})
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="payment-actions">
            <button type="button" className="secondary-btn" onClick={handleBackToPlans}>Back to Plans</button>
            <button
              type="button"
              className="primary-btn"
              onClick={handlePayNow}
              disabled={submitting || !selectedPlan || isSameAsCurrent}
            >
              {submitting ? 'Processing...' : isUpgrade ? 'Pay & Upgrade' : 'Pay & Subscribe'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default SubscriptionPayment;
