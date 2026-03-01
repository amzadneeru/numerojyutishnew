import React, { useEffect, useState } from 'react';
import AdminHeader from '../../components/AdminHeader';
import '../../styles/AdminBookingCharges.css';

function AstrologerBookingChargesAdmin() {
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [paymentFilter, setPaymentFilter] = useState('');
  const [editingMap, setEditingMap] = useState({});
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    fetchBookings();
  }, [paymentFilter]);

  const fetchBookings = async () => {
    try {
      setLoading(true);
      setError('');
      const query = paymentFilter ? `?payment_status=${encodeURIComponent(paymentFilter)}` : '';
      const res = await fetch(`${API_URL}/api/admin/consult-bookings${query}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.message || 'Failed to load booking charges');
        return;
      }

      setBookings(data.data || []);
      const initialMap = {};
      (data.data || []).forEach((item) => {
        initialMap[item.booking_id] = {
          amount_paid: item.amount_paid ?? 0,
          payment_status: item.payment_status || 'Pending',
          booking_status: item.booking_status || 'Pending'
        };
      });
      setEditingMap(initialMap);
    } catch (err) {
      setError('Unable to load booking charges');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (bookingId) => {
    const draft = editingMap[bookingId];
    if (!draft) return;

    try {
      setSavingId(bookingId);
      setError('');
      setSuccessMessage('');

      const res = await fetch(`${API_URL}/api/admin/consult-bookings/${bookingId}/charge`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({
          amount_paid: Number(draft.amount_paid),
          payment_status: draft.payment_status,
          booking_status: draft.booking_status
        })
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Failed to update charge details');
        return;
      }

      setSuccessMessage(`Booking #${bookingId} updated`);
      fetchBookings();
    } catch (err) {
      setError('Failed to update charge details');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="admin-booking-charges-page">
      <AdminHeader />
      <main className="admin-booking-charges-main">
        <h1>Astrologer Booking Charges</h1>
        <p className="admin-booking-subtitle">Manage consultation booking payment amount and statuses</p>

        {error && <p className="error-message">{error}</p>}
        {successMessage && <p className="success-message">{successMessage}</p>}

        <div className="admin-booking-filters">
          <select value={paymentFilter} onChange={(e) => setPaymentFilter(e.target.value)}>
            <option value="">All Payment Status</option>
            <option value="Pending">Pending</option>
            <option value="Paid">Paid</option>
            <option value="Failed">Failed</option>
          </select>
          <button type="button" onClick={fetchBookings}>Refresh</button>
        </div>

        {loading ? (
          <p className="loading">Loading bookings...</p>
        ) : (
          <div className="admin-booking-table-wrap">
            <table className="admin-booking-table">
              <thead>
                <tr>
                  <th>Booking</th>
                  <th>User/Astrologer</th>
                  <th>Schedule</th>
                  <th>Type</th>
                  <th>Charge Details</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {bookings.map((item) => (
                  <tr key={item.booking_id}>
                    <td>#{item.booking_id}</td>
                    <td>
                      <div>User: {item.user_id}</div>
                      <div>Astrologer: {item.astrologer_name || item.astrologer_id}</div>
                    </td>
                    <td>
                      <div>{item.booking_date}</div>
                      <div>{item.start_time} - {item.end_time}</div>
                    </td>
                    <td>{item.consultation_type || 'Call'}</td>
                    <td>
                      <div className="admin-booking-actions">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={editingMap[item.booking_id]?.amount_paid ?? 0}
                          onChange={(e) => {
                            const val = e.target.value;
                            setEditingMap((prev) => ({
                              ...prev,
                              [item.booking_id]: {
                                ...prev[item.booking_id],
                                amount_paid: val
                              }
                            }));
                          }}
                        />
                        <select
                          value={editingMap[item.booking_id]?.payment_status || 'Pending'}
                          onChange={(e) => {
                            const val = e.target.value;
                            setEditingMap((prev) => ({
                              ...prev,
                              [item.booking_id]: {
                                ...prev[item.booking_id],
                                payment_status: val
                              }
                            }));
                          }}
                        >
                          <option value="Pending">Pending</option>
                          <option value="Paid">Paid</option>
                          <option value="Failed">Failed</option>
                        </select>
                        <select
                          value={editingMap[item.booking_id]?.booking_status || 'Pending'}
                          onChange={(e) => {
                            const val = e.target.value;
                            setEditingMap((prev) => ({
                              ...prev,
                              [item.booking_id]: {
                                ...prev[item.booking_id],
                                booking_status: val
                              }
                            }));
                          }}
                        >
                          <option value="Pending">Pending</option>
                          <option value="Confirmed">Confirmed</option>
                          <option value="Cancelled">Cancelled</option>
                        </select>
                      </div>
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => handleUpdate(item.booking_id)}
                        disabled={savingId === item.booking_id}
                      >
                        {savingId === item.booking_id ? 'Saving...' : 'Save'}
                      </button>
                    </td>
                  </tr>
                ))}
                {bookings.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center' }}>No booking charges found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

export default AstrologerBookingChargesAdmin;
