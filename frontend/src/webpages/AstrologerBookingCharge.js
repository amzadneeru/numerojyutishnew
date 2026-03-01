import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/ConsultAstrologers.css';

function AstrologerBookingCharge() {
  const { bookingId } = useParams();
  const navigate = useNavigate();

  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [booking, setBooking] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [transactionRef, setTransactionRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetchBooking();
  }, [bookingId]);

  const fetchBooking = async () => {
    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/consult-bookings/${bookingId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.message || 'Unable to load booking details');
        return;
      }

      setBooking(data.data);
      if (data?.data?.payment_status === 'Paid') {
        setSuccessMessage('This booking is already paid and confirmed.');
      }
    } catch (err) {
      setError('Failed to load booking details');
    } finally {
      setLoading(false);
    }
  };

  const handlePayNow = async () => {
    if (!booking) return;
    if (!transactionRef.trim()) {
      setError('Please enter transaction reference');
      return;
    }

    try {
      setProcessing(true);
      setError('');

      const res = await fetch(`${API_URL}/api/consult-bookings/${bookingId}/charge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({
          payment_method: paymentMethod,
          transaction_ref: transactionRef,
          amount_paid: booking.amount_paid ?? booking.consultation_fee ?? 0
        })
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.message || 'Payment failed');
        return;
      }

      setSuccessMessage('Payment successful. Booking confirmed.');
      setBooking(prev => ({
        ...prev,
        payment_status: data.data.payment_status,
        booking_status: data.data.booking_status,
        amount_paid: data.data.amount_paid
      }));
    } catch (err) {
      setError('Failed to process payment');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="consult-container">
      <Header />
      <button onClick={() => navigate('/consult-astrologers')} className="back-btn">
        ← Back to Astrologers
      </button>

      <div className="slot-booking-wrap">
        <h1>Slot Booking Charge</h1>
        {loading && <p className="loading">Loading booking details...</p>}
        {error && <p className="error-message">{error}</p>}
        {successMessage && <p className="success-message">{successMessage}</p>}

        {booking && (
          <div className="slot-booking-form">
            <div className="booking-summary-box">
              <p><strong>Booking ID:</strong> {booking.booking_id}</p>
              <p><strong>Astrologer:</strong> {booking.astrologer_name}</p>
              <p><strong>Date:</strong> {booking.booking_date}</p>
              <p><strong>Slot:</strong> {booking.start_time} - {booking.end_time}</p>
              <p><strong>Consultation Type:</strong> {booking.consultation_type}</p>
              <p><strong>Booking Status:</strong> {booking.booking_status}</p>
              <p><strong>Payment Status:</strong> {booking.payment_status}</p>
              <p><strong>Amount:</strong> {booking.currency} {booking.amount_paid ?? booking.consultation_fee ?? 0}</p>
            </div>

            {booking.payment_status !== 'Paid' && (
              <>
                <div className="filter-group">
                  <label>Payment Method:</label>
                  <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                    <option value="card">Card</option>
                    <option value="upi">UPI</option>
                    <option value="bank">Bank Transfer</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Transaction Reference:</label>
                  <input
                    type="text"
                    placeholder="Enter transaction reference"
                    value={transactionRef}
                    onChange={(e) => setTransactionRef(e.target.value)}
                  />
                </div>

                <button
                  type="button"
                  className="book-consultation-btn"
                  onClick={handlePayNow}
                  disabled={processing}
                >
                  {processing ? 'Processing...' : 'Pay & Confirm Booking'}
                </button>
              </>
            )}

            {booking.payment_status === 'Paid' && (
              <button
                type="button"
                className="book-consultation-btn"
                onClick={() => navigate('/my-consultation-bookings')}
              >
                Go to My Consultation Bookings
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AstrologerBookingCharge;
