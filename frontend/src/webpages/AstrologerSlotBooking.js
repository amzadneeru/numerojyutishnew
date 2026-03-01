import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/ConsultAstrologers.css';

function AstrologerSlotBooking() {
  const { astroId } = useParams();
  const navigate = useNavigate();

  const userId = localStorage.getItem('userId');
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [astrologer, setAstrologer] = useState(null);
  const [bookingDate, setBookingDate] = useState('');
  const [availableSlots, setAvailableSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [consultationType, setConsultationType] = useState('Call');
  const [pricingByType, setPricingByType] = useState({});
  const [slotInfoMessage, setSlotInfoMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetchAstrologerProfile();
    fetchAstrologerPricing();
  }, [astroId]);

  useEffect(() => {
    if (bookingDate) {
      fetchAvailableSlots(bookingDate);
    }
  }, [bookingDate]);

  const fetchAstrologerProfile = async () => {
    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/astrologers/${astroId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      if (!res.ok) {
        setError('Unable to load astrologer profile');
        return;
      }

      const data = await res.json();
      setAstrologer(data.data);
    } catch (err) {
      setError('Failed to load astrologer profile');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableSlots = async (date) => {
    try {
      setLoading(true);
      setError('');
      setSlotInfoMessage('');
      setSelectedSlot(null);
      setSuccessMessage('');

      const res = await fetch(`${API_URL}/api/astrologers/${astroId}/available-slots?booking_date=${date}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      if (!res.ok) {
        const responseData = await res.json().catch(() => ({}));
        setError(responseData.message || 'Unable to fetch available slots');
        setAvailableSlots([]);
        return;
      }

      const data = await res.json();
      setAvailableSlots(data.data || []);
      setSlotInfoMessage(data.message || '');
    } catch (err) {
      setError('Failed to load available slots');
      setAvailableSlots([]);
      setSlotInfoMessage('');
    } finally {
      setLoading(false);
    }
  };

  const fetchAstrologerPricing = async () => {
    try {
      const res = await fetch(`${API_URL}/api/astrologers/${astroId}/pricing`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      if (!res.ok) {
        return;
      }

      const data = await res.json();
      const pricingList = data.data || [];
      const pricingMap = {};
      pricingList.forEach((item) => {
        if (item.is_active) {
          pricingMap[(item.consultation_type || '').toLowerCase()] = item;
        }
      });
      setPricingByType(pricingMap);
    } catch (err) {
      // silent fallback to avoid blocking booking UI
    }
  };

  const formatTime = (timeValue) => {
    if (!timeValue) return '';
    const [hours, minutes] = timeValue.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const normalizedHour = hours % 12 || 12;
    return `${normalizedHour}:${String(minutes).padStart(2, '0')} ${period}`;
  };

  const getSlotDurationMinutes = (slot) => {
    if (!slot) return 0;
    const [startHour, startMin] = (slot.start_time || '00:00').split(':').map(Number);
    const [endHour, endMin] = (slot.end_time || '00:00').split(':').map(Number);
    return Math.max(0, (endHour * 60 + endMin) - (startHour * 60 + startMin));
  };

  const currentPricing = pricingByType[(consultationType || '').toLowerCase()] || null;
  const slotMinutes = getSlotDurationMinutes(selectedSlot);
  const estimatedAmount = currentPricing ? (Number(currentPricing.price_per_minute || 0) * slotMinutes).toFixed(2) : null;
  const selectedSlotLabel = selectedSlot
    ? `${formatTime(selectedSlot.start_time)} - ${formatTime(selectedSlot.end_time)}`
    : '';

  const handleBookSlot = async () => {
    if (!userId) {
      setError('Please login first to book a consultation');
      return;
    }
    if (!bookingDate) {
      setError('Please select booking date');
      return;
    }
    if (!selectedSlot) {
      setError('Please select a slot');
      return;
    }

    try {
      setBookingLoading(true);
      setError('');
      setSuccessMessage('');

      const res = await fetch(`${API_URL}/api/consult-bookings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({
          astrologer_id: Number(astroId),
          user_id: Number(userId),
          booking_date: bookingDate,
          start_time: selectedSlot.start_time,
          end_time: selectedSlot.end_time,
          consultation_type: consultationType
        })
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.message || 'Booking failed');
        return;
      }

      navigate(`/consult-bookings/${data?.data?.booking_id}/charge`);
    } catch (err) {
      setError('Booking request failed');
    } finally {
      setBookingLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="consult-container">
      <Header />
      <button onClick={() => navigate(`/consult-astrologers/${astroId}`)} className="back-btn">
        ← Back to Astrologer Profile
      </button>

      {loading && <p className="loading">Loading...</p>}
      {error && <p className="error-message">{error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}

      {astrologer && (
        <div className="slot-booking-wrap">
          <h1>Book Slot with {astrologer.display_name || astrologer.full_name}</h1>
          <p className="slot-booking-subtitle">
            Consultation Fee: {astrologer.currency} {astrologer.consultation_fee}
          </p>

          <div className="slot-booking-form">
            <div className="filter-group">
              <label>Select Date:</label>
              <input
                type="date"
                min={today}
                value={bookingDate}
                onChange={(e) => setBookingDate(e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label>Consultation Type:</label>
              <select
                value={consultationType}
                onChange={(e) => setConsultationType(e.target.value)}
              >
                <option value="Chat">Chat</option>
                <option value="Call">Call</option>
                <option value="Video">Video</option>
              </select>
            </div>

            <div className="pricing-estimate-box">
              <p>
                <strong>Price/Minute:</strong>{' '}
                {currentPricing
                  ? `${currentPricing.currency || astrologer.currency || 'INR'} ${currentPricing.price_per_minute}`
                  : 'Not configured'}
              </p>
              <p>
                <strong>Selected Slot Duration:</strong> {slotMinutes || 0} min
              </p>
              <p>
                <strong>Estimated Amount:</strong>{' '}
                {estimatedAmount !== null
                  ? `${currentPricing.currency || astrologer.currency || 'INR'} ${estimatedAmount}`
                  : 'Will be calculated at booking'}
              </p>
            </div>

            <div className="slot-list-section">
              <h3>Available Slots</h3>
              {!bookingDate && <p className="no-results">Select a date to view slots</p>}
              {bookingDate && !loading && slotInfoMessage && (
                <p className="no-results">{slotInfoMessage}</p>
              )}
              {bookingDate && !loading && availableSlots.length === 0 && (
                <p className="no-results">No slots available for selected date</p>
              )}

              {availableSlots.length > 0 && (
                <div className="slot-grid">
                  {availableSlots.map((slot, index) => {
                    const isSelected =
                      selectedSlot &&
                      selectedSlot.start_time === slot.start_time &&
                      selectedSlot.end_time === slot.end_time;

                    return (
                      <button
                        type="button"
                        key={`${slot.start_time}-${slot.end_time}-${index}`}
                        className={`slot-btn ${isSelected ? 'slot-btn-selected' : ''}`}
                        onClick={() => setSelectedSlot(slot)}
                      >
                        {slot.start_time} - {slot.end_time}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="pricing-estimate-box">
              <p>
                <strong>Selected Date:</strong> {bookingDate || 'Not selected'}
              </p>
              <p>
                <strong>Selected Time:</strong>{' '}
                {selectedSlot
                  ? `${formatTime(selectedSlot.start_time)} - ${formatTime(selectedSlot.end_time)}`
                  : 'Not selected'}
              </p>
            </div>

            <button
              type="button"
              className="book-consultation-btn"
              onClick={handleBookSlot}
              disabled={bookingLoading || !selectedSlot}
            >
              {bookingLoading
                ? 'Booking...'
                : selectedSlot && bookingDate
                  ? `Confirm Booking for ${bookingDate}, ${selectedSlotLabel}`
                  : 'Confirm Booking'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AstrologerSlotBooking;
