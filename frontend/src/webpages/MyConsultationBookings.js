import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/ConsultAstrologers.css';

function MyConsultationBookings() {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [rescheduleState, setRescheduleState] = useState({});
  const [cancelBookingTarget, setCancelBookingTarget] = useState(null);

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    if (!userId) {
      setError('Please login to view your consultation bookings');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/consult-bookings?user_id=${userId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Failed to load bookings');
        return;
      }

      setBookings(data.data || []);
    } catch (err) {
      setError('Unable to load your consultation bookings');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancelBookingTarget) return;

    try {
      setActionLoadingId(cancelBookingTarget.booking_id);
      setError('');
      setSuccessMessage('');

      const res = await fetch(`${API_URL}/api/consult-bookings/${cancelBookingTarget.booking_id}/cancel`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({ user_id: Number(userId) })
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Failed to cancel booking');
        return;
      }

      setSuccessMessage('Booking cancelled successfully');
      setCancelBookingTarget(null);
      fetchBookings();
    } catch (err) {
      setError('Failed to cancel booking');
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div className="consult-container">
      <Header />
      <div className="consult-header">
        <h1>My Consultation Bookings</h1>
        <p>View all your astrologer slot bookings and payment status</p>
      </div>

      {error && <p className="error-message">{error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}
      {loading && <p className="loading">Loading your bookings...</p>}

      {!loading && bookings.length === 0 && !error && (
        <p className="no-results">No consultation bookings found.</p>
      )}

      {!loading && bookings.length > 0 && (
        <div className="booking-cards-grid">
          {bookings.map((booking) => (
            <div className="booking-card" key={booking.booking_id}>
              <h3>{booking.astrologer_name || `Astrologer #${booking.astrologer_id}`}</h3>
              <p><strong>Booking ID:</strong> {booking.booking_id}</p>
              <p><strong>Date:</strong> {booking.booking_date}</p>
              <p><strong>Slot:</strong> {booking.start_time} - {booking.end_time}</p>
              <p><strong>Type:</strong> {booking.consultation_type || 'Call'}</p>
              <p><strong>Booking Status:</strong> {booking.booking_status}</p>
              <p><strong>Payment Status:</strong> {booking.payment_status}</p>
              <p><strong>Amount:</strong> {booking.currency} {booking.amount_paid ?? 0}</p>

              {booking.payment_status !== 'Paid' && (
                <button
                  className="book-consultation-btn"
                  onClick={() => navigate(`/consult-bookings/${booking.booking_id}/charge`)}
                >
                  Complete Payment
                </button>
              )}

              {booking.booking_status !== 'Cancelled' && (
                <div className="booking-action-row">
                  <button
                    className="booking-action-btn"
                    disabled={actionLoadingId === booking.booking_id}
                    onClick={() => setCancelBookingTarget(booking)}
                  >
                    {actionLoadingId === booking.booking_id ? 'Cancelling...' : 'Cancel Booking'}
                  </button>

                  <button
                    className="booking-action-btn"
                    onClick={() => {
                      setRescheduleState((prev) => ({
                        ...prev,
                        [booking.booking_id]: {
                          ...(prev[booking.booking_id] || {}),
                          show: !prev[booking.booking_id]?.show,
                          date: prev[booking.booking_id]?.date || '',
                          slots: prev[booking.booking_id]?.slots || [],
                          selectedSlot: prev[booking.booking_id]?.selectedSlot || null,
                          loadingSlots: false
                        }
                      }));
                    }}
                  >
                    {rescheduleState[booking.booking_id]?.show ? 'Hide Reschedule' : 'Reschedule'}
                  </button>
                </div>
              )}

              {rescheduleState[booking.booking_id]?.show && booking.booking_status !== 'Cancelled' && (
                <div className="reschedule-box">
                  <div className="filter-group">
                    <label>New Date:</label>
                    <input
                      type="date"
                      min={new Date().toISOString().split('T')[0]}
                      value={rescheduleState[booking.booking_id]?.date || ''}
                      onChange={async (e) => {
                        const date = e.target.value;
                        setRescheduleState((prev) => ({
                          ...prev,
                          [booking.booking_id]: {
                            ...prev[booking.booking_id],
                            date,
                            selectedSlot: null,
                            loadingSlots: true
                          }
                        }));

                        try {
                          const res = await fetch(
                            `${API_URL}/api/astrologers/${booking.astrologer_id}/available-slots?booking_date=${date}`,
                            { headers: { Authorization: `Bearer ${authToken}` } }
                          );
                          const data = await res.json();

                          if (!res.ok) {
                            setError(data.message || 'Failed to load available slots');
                            setRescheduleState((prev) => ({
                              ...prev,
                              [booking.booking_id]: {
                                ...prev[booking.booking_id],
                                slots: [],
                                loadingSlots: false
                              }
                            }));
                            return;
                          }

                          setRescheduleState((prev) => ({
                            ...prev,
                            [booking.booking_id]: {
                              ...prev[booking.booking_id],
                              slots: data.data || [],
                              loadingSlots: false
                            }
                          }));
                        } catch (err) {
                          setError('Failed to load available slots');
                          setRescheduleState((prev) => ({
                            ...prev,
                            [booking.booking_id]: {
                              ...prev[booking.booking_id],
                              slots: [],
                              loadingSlots: false
                            }
                          }));
                        }
                      }}
                    />
                  </div>

                  {rescheduleState[booking.booking_id]?.loadingSlots && (
                    <p className="loading">Loading slots...</p>
                  )}

                  {!!rescheduleState[booking.booking_id]?.slots?.length && (
                    <div className="slot-grid">
                      {rescheduleState[booking.booking_id].slots.map((slot, idx) => {
                        const selected =
                          rescheduleState[booking.booking_id]?.selectedSlot &&
                          rescheduleState[booking.booking_id]?.selectedSlot.start_time === slot.start_time &&
                          rescheduleState[booking.booking_id]?.selectedSlot.end_time === slot.end_time;

                        return (
                          <button
                            type="button"
                            key={`${booking.booking_id}-${slot.start_time}-${slot.end_time}-${idx}`}
                            className={`slot-btn ${selected ? 'slot-btn-selected' : ''}`}
                            onClick={() => {
                              setRescheduleState((prev) => ({
                                ...prev,
                                [booking.booking_id]: {
                                  ...prev[booking.booking_id],
                                  selectedSlot: slot
                                }
                              }));
                            }}
                          >
                            {slot.start_time} - {slot.end_time}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <button
                    className="book-consultation-btn"
                    disabled={!rescheduleState[booking.booking_id]?.selectedSlot || actionLoadingId === booking.booking_id}
                    onClick={async () => {
                      const draft = rescheduleState[booking.booking_id];
                      if (!draft?.date || !draft?.selectedSlot) {
                        setError('Please select new date and slot');
                        return;
                      }

                      try {
                        setActionLoadingId(booking.booking_id);
                        setError('');
                        setSuccessMessage('');

                        const res = await fetch(`${API_URL}/api/consult-bookings/${booking.booking_id}/reschedule`, {
                          method: 'PUT',
                          headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${authToken}`
                          },
                          body: JSON.stringify({
                            user_id: Number(userId),
                            booking_date: draft.date,
                            start_time: draft.selectedSlot.start_time,
                            end_time: draft.selectedSlot.end_time
                          })
                        });
                        const data = await res.json();

                        if (!res.ok) {
                          setError(data.message || 'Failed to reschedule booking');
                          return;
                        }

                        setSuccessMessage('Booking rescheduled successfully');
                        setRescheduleState((prev) => ({
                          ...prev,
                          [booking.booking_id]: {
                            ...prev[booking.booking_id],
                            show: false,
                            selectedSlot: null
                          }
                        }));
                        fetchBookings();
                      } catch (err) {
                        setError('Failed to reschedule booking');
                      } finally {
                        setActionLoadingId(null);
                      }
                    }}
                  >
                    {actionLoadingId === booking.booking_id ? 'Updating...' : 'Confirm Reschedule'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {cancelBookingTarget && (
        <div className="booking-modal-overlay">
          <div className="booking-modal-card">
            <h3>Cancel Booking?</h3>
            <p>
              Booking ID #{cancelBookingTarget.booking_id} with {cancelBookingTarget.astrologer_name || `Astrologer #${cancelBookingTarget.astrologer_id}`} will be cancelled.
            </p>
            <div className="booking-modal-actions">
              <button
                type="button"
                className="booking-action-btn"
                onClick={() => setCancelBookingTarget(null)}
                disabled={actionLoadingId === cancelBookingTarget.booking_id}
              >
                Keep Booking
              </button>
              <button
                type="button"
                className="book-consultation-btn"
                onClick={handleConfirmCancel}
                disabled={actionLoadingId === cancelBookingTarget.booking_id}
              >
                {actionLoadingId === cancelBookingTarget.booking_id ? 'Cancelling...' : 'Yes, Cancel Booking'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MyConsultationBookings;
