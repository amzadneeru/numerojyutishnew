import React, { useState } from 'react';
import Header from '../components/Header';
import '../styles/Enquiry.css';

function Enquiry() {
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [formData, setFormData] = useState({
    name: '',
    gender: 'Male',
    phone_no: '',
    email: '',
    date_of_birth: '',
    birth_time: '',
    birth_place: '',
    enquiry_type: '',
    description: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);

    if (!formData.name.trim() || !formData.phone_no.trim()) {
      setIsError(true);
      setMessage('Name and phone number are required.');
      return;
    }

    const normalizedPhone = formData.phone_no.trim();
    if (!/^\d{10,15}$/.test(normalizedPhone)) {
      setIsError(true);
      setMessage('Phone number must contain only digits and be 10 to 15 digits long.');
      return;
    }

    const normalizedEmail = formData.email.trim();
    if (normalizedEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setIsError(true);
      setMessage('Please enter a valid email address.');
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch(`${API_URL}/api/enquiries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          name: formData.name.trim(),
          phone_no: normalizedPhone,
          email: normalizedEmail || null,
          birth_place: formData.birth_place.trim() || null,
          enquiry_type: formData.enquiry_type.trim() || null,
          description: formData.description.trim() || null
        })
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        setIsError(true);
        setMessage(data.message || 'Failed to submit enquiry.');
        return;
      }

      setIsError(false);
      setMessage(`Enquiry submitted successfully. Enquiry ID: ${data?.data?.enquiry_id || ''}`);
      setFormData({
        name: '',
        gender: 'Male',
        phone_no: '',
        email: '',
        date_of_birth: '',
        birth_time: '',
        birth_place: '',
        enquiry_type: '',
        description: ''
      });
    } catch (error) {
      setIsError(true);
      setMessage('Unable to submit enquiry right now. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="enquiry-page">
      <Header />
      <main className="enquiry-main">
        <section className="enquiry-card">
          <h1>Enquiry Form</h1>
          <p className="enquiry-subtitle">Share your details and our team will contact you.</p>

          <form className="enquiry-form" onSubmit={handleSubmit}>
            <div className="enquiry-grid">
              <label>
                Name *
                <input type="text" name="name" value={formData.name} onChange={handleChange} required />
              </label>

              <label>
                Gender
                <select name="gender" value={formData.gender} onChange={handleChange}>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </label>

              <label>
                Phone Number *
                <input type="text" name="phone_no" value={formData.phone_no} onChange={handleChange} required maxLength={15} inputMode="numeric" />
              </label>

              <label>
                Email
                <input type="email" name="email" value={formData.email} onChange={handleChange} maxLength={150} />
              </label>

              <label>
                Date of Birth
                <input type="date" name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} />
              </label>

              <label>
                Birth Time
                <input type="time" name="birth_time" value={formData.birth_time} onChange={handleChange} />
              </label>

              <label>
                Birth Place
                <input type="text" name="birth_place" value={formData.birth_place} onChange={handleChange} />
              </label>

              <label>
                Enquiry Type
                <input type="text" name="enquiry_type" value={formData.enquiry_type} onChange={handleChange} placeholder="Numerology / Astrology / Product" />
              </label>
            </div>

            <label>
              Description
              <textarea name="description" value={formData.description} onChange={handleChange} rows={4} placeholder="Write your enquiry..." />
            </label>

            {message && <p className={`enquiry-message ${isError ? 'error' : 'success'}`}>{message}</p>}

            <button className="enquiry-submit" type="submit" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Enquiry'}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}

export default Enquiry;
