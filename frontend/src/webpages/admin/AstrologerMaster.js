import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminHeader from '../../components/AdminHeader';
import '../../styles/AstrologerMaster.css';

function AstrologerMaster() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  // Auth
  const userId = localStorage.getItem('userId');
  const authToken = localStorage.getItem('authToken');

  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Astrologer Management State
  const [astrologers, setAstrologers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [astrologerForm, setAstrologerForm] = useState({
    astrologer_id: null,
    full_name: '',
    display_name: '',
    email: '',
    phone_number: '',
    gender: 'Male',
    experience_years: 0,
    expertise: '',
    languages: '',
    consultation_fee: 0,
    currency: 'INR',
    profile_image_url: '',
    bio: '',
    is_active: true,
    is_verified: false
  });
  const [editingAstrologer, setEditingAstrologer] = useState(null);

  // Image Upload State
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);

  // Astrologer Charges State
  const [showChargesModal, setShowChargesModal] = useState(false);
  const [selectedAstrologerForCharges, setSelectedAstrologerForCharges] = useState(null);
  const [charges, setCharges] = useState([]);
  const [chargesLoading, setChargesLoading] = useState(false);
  const [editingChargeId, setEditingChargeId] = useState(null);
  const [chargeForm, setChargeForm] = useState({
    consultation_type: 'Call',
    price_per_minute: '',
    currency: 'INR',
    is_active: true
  });

  // Astrologer Availability State
  const [showAvailabilityModal, setShowAvailabilityModal] = useState(false);
  const [selectedAstrologerForAvailability, setSelectedAstrologerForAvailability] = useState(null);
  const [availabilities, setAvailabilities] = useState([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [editingAvailabilityId, setEditingAvailabilityId] = useState(null);
  const [availabilityForm, setAvailabilityForm] = useState({
    day_of_week: 'Monday',
    start_time: '09:00',
    end_time: '17:00',
    is_available: true
  });

  // Check authentication
  useEffect(() => {
    if (!userId || !authToken) {
      navigate('/login');
    } else {
      fetchAstrologers();
    }
  }, [userId, authToken, navigate]);

  // Fetch all astrologers (including inactive)
  const fetchAstrologers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/astrologers?limit=100`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      
      if (data.success) {
        setAstrologers(data.data || []);
        setError('');
      } else {
        setError(data.message || 'Failed to fetch astrologers');
      }
    } catch (err) {
      console.error('Error fetching astrologers:', err);
      setError('Failed to load astrologers data');
    } finally {
      setLoading(false);
    }
  };

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setAstrologerForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  // Handle image file selection
  const handleImageFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      console.log('📁 Image file selected:', file.name, 'Size:', (file.size / 1024).toFixed(2) + 'KB');
      
      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError('Please select a valid image file');
        return;
      }
      
      // Validate file size (max 5MB)
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        setError('Image file size must be less than 5MB');
        return;
      }
      
      setImageFile(file);
      const preview = URL.createObjectURL(file);
      setImagePreview(preview);
      setError('');
    }
  };

  // Upload image file to server
  const uploadImageFile = async () => {
    if (!imageFile) {
      return null;
    }

    try {
      console.log('🚀 Starting image upload...');
      setUploadingImage(true);
      
      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('astrologer_id', editingAstrologer || 'new');

      const response = await fetch(`${API_URL}/api/upload-astrologer-image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        console.log('✅ Image uploaded successfully:', data.data.image_url);
        return data.data.image_url;
      } else {
        throw new Error(data.message || 'Upload failed');
      }
    } catch (err) {
      console.error('❌ Error uploading image:', err);
      setError(`Image upload failed: ${err.message}`);
      return null;
    } finally {
      setUploadingImage(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setAstrologerForm({
      astrologer_id: null,
      full_name: '',
      display_name: '',
      email: '',
      phone_number: '',
      gender: 'Male',
      experience_years: 0,
      expertise: '',
      languages: '',
      consultation_fee: 0,
      currency: 'INR',
      profile_image_url: '',
      bio: '',
      is_active: true,
      is_verified: false
    });
    setEditingAstrologer(null);
    setShowForm(false);
    setError('');
    setImageFile(null);
    setImagePreview(null);
  };

  // Create new astrologer
  const handleCreateAstrologer = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!astrologerForm.full_name || !astrologerForm.email) {
      setError('Full name and email are required');
      return;
    }

    try {
      setLoading(true);
      
      // Upload image first if file is selected
      let imageUrl = astrologerForm.profile_image_url;
      if (imageFile) {
        const uploadedUrl = await uploadImageFile();
        if (uploadedUrl) {
          imageUrl = uploadedUrl;
        } else {
          setError('Image upload failed. Please try again.');
          setLoading(false);
          return;
        }
      }
      const response = await fetch(`${API_URL}/api/astrologers`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          full_name: astrologerForm.full_name,
          display_name: astrologerForm.display_name || astrologerForm.full_name,
          email: astrologerForm.email,
          phone_number: astrologerForm.phone_number,
          gender: astrologerForm.gender,
          experience_years: parseInt(astrologerForm.experience_years) || 0,
          expertise: astrologerForm.expertise,
          languages: astrologerForm.languages,
          consultation_fee: parseFloat(astrologerForm.consultation_fee) || 0,
          currency: astrologerForm.currency,
          profile_image_url: imageUrl,
          bio: astrologerForm.bio,
          is_active: astrologerForm.is_active,
          is_verified: astrologerForm.is_verified
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setSuccessMessage('Astrologer created successfully!');
        resetForm();
        fetchAstrologers();
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError(data.message || 'Failed to create astrologer');
      }
    } catch (err) {
      console.error('Error creating astrologer:', err);
      setError('Failed to create astrologer');
    } finally {
      setLoading(false);
    }
  };

  // Update existing astrologer
  const handleUpdateAstrologer = async (e) => {
    e.preventDefault();
    
    if (!editingAstrologer) return;

    try {
      setLoading(true);
      
      // Upload image first if file is selected
      let imageUrl = astrologerForm.profile_image_url;
      if (imageFile) {
        const uploadedUrl = await uploadImageFile();
        if (uploadedUrl) {
          imageUrl = uploadedUrl;
        } else {
          setError('Image upload failed. Please try again.');
          setLoading(false);
          return;
        }
      }
      const response = await fetch(`${API_URL}/api/astrologers/${editingAstrologer}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          full_name: astrologerForm.full_name,
          display_name: astrologerForm.display_name,
          email: astrologerForm.email,
          phone_number: astrologerForm.phone_number,
          gender: astrologerForm.gender,
          experience_years: parseInt(astrologerForm.experience_years) || 0,
          expertise: astrologerForm.expertise,
          languages: astrologerForm.languages,
          consultation_fee: parseFloat(astrologerForm.consultation_fee) || 0,
          currency: astrologerForm.currency,
          profile_image_url: imageUrl,
          bio: astrologerForm.bio,
          is_active: astrologerForm.is_active
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setSuccessMessage('Astrologer updated successfully!');
        resetForm();
        fetchAstrologers();
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError(data.message || 'Failed to update astrologer');
      }
    } catch (err) {
      console.error('Error updating astrologer:', err);
      setError('Failed to update astrologer');
    } finally {
      setLoading(false);
    }
  };

  // Edit astrologer - populate form
  const handleEditAstrologer = (astrologer) => {
    setEditingAstrologer(astrologer.astrologer_id);
    setAstrologerForm({
      astrologer_id: astrologer.astrologer_id,
      full_name: astrologer.full_name || '',
      display_name: astrologer.display_name || '',
      email: astrologer.email || '',
      phone_number: astrologer.phone_number || '',
      gender: astrologer.gender || 'Male',
      experience_years: astrologer.experience_years || 0,
      expertise: astrologer.expertise || '',
      languages: astrologer.languages || '',
      consultation_fee: astrologer.consultation_fee || 0,
      currency: astrologer.currency || 'INR',
      profile_image_url: astrologer.profile_image_url || '',
      bio: astrologer.bio || '',
      is_active: astrologer.is_active !== false,
      is_verified: astrologer.is_verified === true
    });
    setImagePreview(astrologer.profile_image_url || null);
    setImageFile(null);
    setShowForm(true);
  };

  // Delete astrologer
  const handleDeleteAstrologer = async (astrologerId) => {
    if (!window.confirm('Are you sure you want to delete this astrologer?')) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/astrologers/${astrologerId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      
      if (data.success) {
        setSuccessMessage('Astrologer deleted successfully!');
        fetchAstrologers();
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError(data.message || 'Failed to delete astrologer');
      }
    } catch (err) {
      console.error('Error deleting astrologer:', err);
      setError('Failed to delete astrologer');
    } finally {
      setLoading(false);
    }
  };

  // Toggle verified status
  const handleToggleVerified = async (astrologerId, currentStatus) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/astrologers/${astrologerId}/verify`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          is_verified: !currentStatus
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setSuccessMessage(`Astrologer ${!currentStatus ? 'verified' : 'unverified'} successfully!`);
        fetchAstrologers();
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError(data.message || 'Failed to update verification status');
      }
    } catch (err) {
      console.error('Error updating verification:', err);
      setError('Failed to update verification status');
    } finally {
      setLoading(false);
    }
  };

  const resetChargeForm = () => {
    setChargeForm({
      consultation_type: 'Call',
      price_per_minute: '',
      currency: 'INR',
      is_active: true
    });
    setEditingChargeId(null);
  };

  const fetchAstrologerCharges = async (astrologerId) => {
    try {
      setChargesLoading(true);
      const response = await fetch(`${API_URL}/api/astrologers/${astrologerId}/pricing`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      if (data.success) {
        setCharges(data.data || []);
      } else {
        setError(data.message || 'Failed to fetch astrologer charges');
      }
    } catch (err) {
      console.error('Error fetching astrologer charges:', err);
      setError('Failed to load astrologer charges');
    } finally {
      setChargesLoading(false);
    }
  };

  const openChargesModal = async (astrologer) => {
    setSelectedAstrologerForCharges(astrologer);
    setShowChargesModal(true);
    resetChargeForm();
    await fetchAstrologerCharges(astrologer.astrologer_id);
  };

  const handleChargeSubmit = async (e) => {
    e.preventDefault();
    if (!selectedAstrologerForCharges) return;

    try {
      setLoading(true);
      setError('');

      const payload = {
        consultation_type: chargeForm.consultation_type,
        price_per_minute: parseFloat(chargeForm.price_per_minute) || 0,
        currency: chargeForm.currency,
        is_active: chargeForm.is_active
      };

      const url = editingChargeId
        ? `${API_URL}/api/astrologer-pricing/${editingChargeId}`
        : `${API_URL}/api/astrologers/${selectedAstrologerForCharges.astrologer_id}/pricing`;
      const method = editingChargeId ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (data.success) {
        setSuccessMessage(editingChargeId ? 'Charge updated successfully!' : 'Charge added successfully!');
        resetChargeForm();
        await fetchAstrologerCharges(selectedAstrologerForCharges.astrologer_id);
      } else {
        setError(data.message || 'Failed to save charge');
      }
    } catch (err) {
      console.error('Error saving charge:', err);
      setError('Failed to save charge');
    } finally {
      setLoading(false);
    }
  };

  const handleEditCharge = (charge) => {
    setEditingChargeId(charge.pricing_id);
    setChargeForm({
      consultation_type: charge.consultation_type || 'Call',
      price_per_minute: charge.price_per_minute || 0,
      currency: charge.currency || 'INR',
      is_active: charge.is_active !== false
    });
  };

  const handleDeleteCharge = async (chargeId) => {
    if (!window.confirm('Are you sure you want to delete this charge configuration?')) {
      return;
    }
    if (!selectedAstrologerForCharges) return;

    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/astrologer-pricing/${chargeId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      if (data.success) {
        setSuccessMessage('Charge deleted successfully!');
        await fetchAstrologerCharges(selectedAstrologerForCharges.astrologer_id);
      } else {
        setError(data.message || 'Failed to delete charge');
      }
    } catch (err) {
      console.error('Error deleting charge:', err);
      setError('Failed to delete charge');
    } finally {
      setLoading(false);
    }
  };

  const resetAvailabilityForm = () => {
    setAvailabilityForm({
      day_of_week: 'Monday',
      start_time: '09:00',
      end_time: '17:00',
      is_available: true
    });
    setEditingAvailabilityId(null);
  };

  const fetchAstrologerAvailability = async (astrologerId) => {
    try {
      setAvailabilityLoading(true);
      const response = await fetch(`${API_URL}/api/astrologers/${astrologerId}/availability`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      if (data.success) {
        setAvailabilities(data.data || []);
      } else {
        setError(data.message || 'Failed to fetch astrologer availability');
      }
    } catch (err) {
      console.error('Error fetching astrologer availability:', err);
      setError('Failed to load astrologer availability');
    } finally {
      setAvailabilityLoading(false);
    }
  };

  const openAvailabilityModal = async (astrologer) => {
    setSelectedAstrologerForAvailability(astrologer);
    setShowAvailabilityModal(true);
    resetAvailabilityForm();
    await fetchAstrologerAvailability(astrologer.astrologer_id);
  };

  const handleAvailabilitySubmit = async (e) => {
    e.preventDefault();
    if (!selectedAstrologerForAvailability) return;

    const startMinutes = Number((availabilityForm.start_time || '00:00').split(':')[0]) * 60
      + Number((availabilityForm.start_time || '00:00').split(':')[1]);
    const endMinutes = Number((availabilityForm.end_time || '00:00').split(':')[0]) * 60
      + Number((availabilityForm.end_time || '00:00').split(':')[1]);

    if (endMinutes <= startMinutes) {
      setError('End time must be greater than start time');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const endpoint = editingAvailabilityId
        ? `${API_URL}/api/astrologer-availability/${editingAvailabilityId}`
        : `${API_URL}/api/astrologers/${selectedAstrologerForAvailability.astrologer_id}/availability`;
      const response = await fetch(endpoint, {
        method: editingAvailabilityId ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          day_of_week: availabilityForm.day_of_week,
          start_time: availabilityForm.start_time,
          end_time: availabilityForm.end_time,
          is_available: availabilityForm.is_available
        })
      });

      const data = await response.json();
      if (data.success) {
        setSuccessMessage(editingAvailabilityId ? 'Availability updated successfully!' : 'Availability saved successfully!');
        resetAvailabilityForm();
        await fetchAstrologerAvailability(selectedAstrologerForAvailability.astrologer_id);
      } else {
        setError(data.message || 'Failed to save availability');
      }
    } catch (err) {
      console.error('Error saving availability:', err);
      setError('Failed to save availability');
    } finally {
      setLoading(false);
    }
  };

  const handleEditAvailability = (availability) => {
    setEditingAvailabilityId(availability.availability_id);
    setAvailabilityForm({
      day_of_week: availability.day_of_week || 'Monday',
      start_time: availability.start_time || '09:00',
      end_time: availability.end_time || '17:00',
      is_available: availability.is_available !== false
    });
  };

  const handleDeleteAvailability = async (availabilityId) => {
    if (!selectedAstrologerForAvailability) return;
    if (!window.confirm('Are you sure you want to delete this availability?')) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/astrologer-availability/${availabilityId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      if (data.success) {
        setSuccessMessage('Availability deleted successfully!');
        if (editingAvailabilityId === availabilityId) {
          resetAvailabilityForm();
        }
        await fetchAstrologerAvailability(selectedAstrologerForAvailability.astrologer_id);
      } else {
        setError(data.message || 'Failed to delete availability');
      }
    } catch (err) {
      console.error('Error deleting availability:', err);
      setError('Failed to delete availability');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="astrologer-master-container">
      <AdminHeader />
      <header className="astrologer-master-header">
        <h1>🔮 Astrologer Management</h1>
        <button 
          className="btn-add-new"
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
        >
          ➕ Add New Astrologer
        </button>
      </header>

      {/* Messages */}
      {error && (
        <div className="message error-message">
          ❌ {error}
          <button onClick={() => setError('')}>✕</button>
        </div>
      )}

      {successMessage && (
        <div className="message success-message">
          ✅ {successMessage}
          <button onClick={() => setSuccessMessage('')}>✕</button>
        </div>
      )}

      {/* Astrologer Form */}
      {showForm && (
        <div className="form-modal">
          <div className="form-container">
            <div className="form-header">
              <h2>{editingAstrologer ? '✏️ Edit Astrologer' : '➕ Add New Astrologer'}</h2>
              <button className="close-btn" onClick={resetForm}>✕</button>
            </div>

            <form onSubmit={editingAstrologer ? handleUpdateAstrologer : handleCreateAstrologer}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    name="full_name"
                    value={astrologerForm.full_name}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter full name"
                  />
                </div>

                <div className="form-group">
                  <label>Display Name</label>
                  <input
                    type="text"
                    name="display_name"
                    value={astrologerForm.display_name}
                    onChange={handleInputChange}
                    placeholder="Public display name"
                  />
                </div>

                <div className="form-group">
                  <label>Email *</label>
                  <input
                    type="email"
                    name="email"
                    value={astrologerForm.email}
                    onChange={handleInputChange}
                    required
                    placeholder="email@example.com"
                  />
                </div>

                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="text"
                    name="phone_number"
                    value={astrologerForm.phone_number}
                    onChange={handleInputChange}
                    placeholder="+91 XXXXXXXXXX"
                  />
                </div>

                <div className="form-group">
                  <label>Gender</label>
                  <select
                    name="gender"
                    value={astrologerForm.gender}
                    onChange={handleInputChange}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Experience (Years)</label>
                  <input
                    type="number"
                    name="experience_years"
                    value={astrologerForm.experience_years}
                    onChange={handleInputChange}
                    min="0"
                    placeholder="Years of experience"
                  />
                </div>

                <div className="form-group">
                  <label>Expertise</label>
                  <input
                    type="text"
                    name="expertise"
                    value={astrologerForm.expertise}
                    onChange={handleInputChange}
                    placeholder="e.g., Vedic, Tarot, Numerology"
                  />
                </div>

                <div className="form-group">
                  <label>Languages</label>
                  <input
                    type="text"
                    name="languages"
                    value={astrologerForm.languages}
                    onChange={handleInputChange}
                    placeholder="e.g., English, Hindi, Tamil"
                  />
                </div>

                <div className="form-group">
                  <label>Consultation Fee</label>
                  <input
                    type="number"
                    name="consultation_fee"
                    value={astrologerForm.consultation_fee}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                    placeholder="Fee amount"
                  />
                </div>

                <div className="form-group">
                  <label>Currency</label>
                  <select
                    name="currency"
                    value={astrologerForm.currency}
                    onChange={handleInputChange}
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>Profile Image</label>
                  <div className="image-upload-section">
                    {/* File Upload */}
                    <div className="upload-area">
                      <input
                        type="file"
                        id="astrologer-image-upload"
                        accept="image/*"
                        onChange={handleImageFileChange}
                        className="file-input"
                      />
                      <label htmlFor="astrologer-image-upload" className="file-input-label">
                        📁 Choose Image File
                      </label>
                      <span className="file-hint">or</span>
                      <input
                        type="url"
                        name="profile_image_url"
                        value={astrologerForm.profile_image_url}
                        onChange={handleInputChange}
                        placeholder="Enter image URL"
                        className="url-input"
                      />
                    </div>
                    
                    {/* Image Preview */}
                    {(imagePreview || astrologerForm.profile_image_url) && (
                      <div className="image-preview-container">
                        <img
                          src={imagePreview || astrologerForm.profile_image_url}
                          alt="Astrologer preview"
                          className="image-preview"
                        />
                        <button
                          type="button"
                          className="remove-image-btn"
                          onClick={() => {
                            setImagePreview(null);
                            setImageFile(null);
                            setAstrologerForm(prev => ({ ...prev, profile_image_url: '' }));
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    )}
                    
                    {uploadingImage && (
                      <div className="uploading-indicator">📤 Uploading image...</div>
                    )}
                  </div>
                </div>

                <div className="form-group full-width">
                  <label>Bio</label>
                  <textarea
                    name="bio"
                    value={astrologerForm.bio}
                    onChange={handleInputChange}
                    rows="4"
                    placeholder="Brief description about the astrologer"
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_active"
                      checked={astrologerForm.is_active}
                      onChange={handleInputChange}
                    />
                    Active
                  </label>
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_verified"
                      checked={astrologerForm.is_verified}
                      onChange={handleInputChange}
                    />
                    Verified
                  </label>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={resetForm}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Saving...' : editingAstrologer ? 'Update Astrologer' : 'Create Astrologer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Astrologer Charges Modal */}
      {showChargesModal && selectedAstrologerForCharges && (
        <div className="form-modal">
          <div className="form-container">
            <div className="form-header">
              <h2>💰 Manage Pricing - {selectedAstrologerForCharges.display_name || selectedAstrologerForCharges.full_name}</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowChargesModal(false);
                  setSelectedAstrologerForCharges(null);
                  resetChargeForm();
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleChargeSubmit}>
              <div className="charges-form-grid">
                <div className="form-group">
                  <label>Consultation Type *</label>
                  <select
                    value={chargeForm.consultation_type}
                    onChange={(e) => setChargeForm(prev => ({ ...prev, consultation_type: e.target.value }))}
                    required
                  >
                    <option value="Chat">Chat</option>
                    <option value="Call">Call</option>
                    <option value="Video">Video</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Price Per Minute *</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={chargeForm.price_per_minute}
                    onChange={(e) => setChargeForm(prev => ({ ...prev, price_per_minute: e.target.value }))}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Currency</label>
                  <select
                    value={chargeForm.currency}
                    onChange={(e) => setChargeForm(prev => ({ ...prev, currency: e.target.value }))}
                  >
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                  </select>
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={chargeForm.is_active}
                      onChange={(e) => setChargeForm(prev => ({ ...prev, is_active: e.target.checked }))}
                    />
                    Active
                  </label>
                </div>
              </div>

              <div className="form-actions">
                {editingChargeId && (
                  <button type="button" className="btn-cancel" onClick={resetChargeForm}>
                    Cancel Edit
                  </button>
                )}
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Saving...' : editingChargeId ? 'Update Charge' : 'Add Charge'}
                </button>
              </div>
            </form>

            <div className="charges-list-wrap">
              <h3>Defined Pricing</h3>
              {chargesLoading ? (
                <div className="loading">Loading pricing...</div>
              ) : charges.length === 0 ? (
                <div className="no-data">No pricing defined yet.</div>
              ) : (
                <div className="table-container">
                  <table className="astrologers-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Price / Min</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {charges.map(charge => (
                        <tr key={charge.pricing_id}>
                          <td>{charge.consultation_type}</td>
                          <td>{charge.currency} {charge.price_per_minute}</td>
                          <td>
                            <span className={`status-badge ${charge.is_active ? 'active' : 'inactive'}`}>
                              {charge.is_active ? '✅ Active' : '❌ Inactive'}
                            </span>
                          </td>
                          <td>
                            <div className="action-buttons">
                              <button type="button" className="btn-edit" onClick={() => handleEditCharge(charge)} title="Edit Charge">
                                ✏️
                              </button>
                              <button type="button" className="btn-delete" onClick={() => handleDeleteCharge(charge.pricing_id)} title="Delete Charge">
                                🗑️
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Astrologer Availability Modal */}
      {showAvailabilityModal && selectedAstrologerForAvailability && (
        <div className="form-modal">
          <div className="form-container">
            <div className="form-header">
              <h2>🗓️ Manage Availability - {selectedAstrologerForAvailability.display_name || selectedAstrologerForAvailability.full_name}</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowAvailabilityModal(false);
                  setSelectedAstrologerForAvailability(null);
                  resetAvailabilityForm();
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAvailabilitySubmit}>
              <div className="charges-form-grid">
                <div className="form-group">
                  <label>Day Of Week *</label>
                  <select
                    value={availabilityForm.day_of_week}
                    onChange={(e) => setAvailabilityForm(prev => ({ ...prev, day_of_week: e.target.value }))}
                    required
                  >
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Start Time *</label>
                  <input
                    type="time"
                    value={availabilityForm.start_time}
                    onChange={(e) => setAvailabilityForm(prev => ({ ...prev, start_time: e.target.value }))}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>End Time *</label>
                  <input
                    type="time"
                    value={availabilityForm.end_time}
                    onChange={(e) => setAvailabilityForm(prev => ({ ...prev, end_time: e.target.value }))}
                    required
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={availabilityForm.is_available}
                      onChange={(e) => setAvailabilityForm(prev => ({ ...prev, is_available: e.target.checked }))}
                    />
                    Active
                  </label>
                </div>
              </div>

              <div className="form-actions">
                {editingAvailabilityId && (
                  <button type="button" className="btn-cancel" onClick={resetAvailabilityForm}>
                    Cancel Edit
                  </button>
                )}
                <button type="button" className="btn-cancel" onClick={resetAvailabilityForm}>
                  Reset
                </button>
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Saving...' : editingAvailabilityId ? 'Update Availability' : 'Add Availability'}
                </button>
              </div>
            </form>

            <div className="charges-list-wrap">
              <h3>Weekly Availability</h3>
              {availabilityLoading ? (
                <div className="loading">Loading availability...</div>
              ) : availabilities.length === 0 ? (
                <div className="no-data">No availability configured yet.</div>
              ) : (
                <div className="table-container">
                  <table className="astrologers-table">
                    <thead>
                      <tr>
                        <th>Day</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {availabilities.map((item) => (
                        <tr key={item.availability_id}>
                          <td>{item.day_of_week}</td>
                          <td>{item.start_time}</td>
                          <td>{item.end_time}</td>
                          <td>
                            <span className={`status-badge ${item.is_available ? 'active' : 'inactive'}`}>
                              {item.is_available ? '✅ Active' : '❌ Inactive'}
                            </span>
                          </td>
                          <td>
                            <div className="action-buttons">
                              <button
                                type="button"
                                className="btn-edit"
                                onClick={() => handleEditAvailability(item)}
                                title="Edit Availability"
                              >
                                ✏️
                              </button>
                              <button
                                type="button"
                                className="btn-delete"
                                onClick={() => handleDeleteAvailability(item.availability_id)}
                                title="Delete Availability"
                              >
                                🗑️
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Astrologers List */}
      <div className="astrologers-list">
        <h2>📋 Astrologers List</h2>

        {loading && !showForm ? (
          <div className="loading">Loading astrologers...</div>
        ) : astrologers.length === 0 ? (
          <div className="no-data">No astrologers found. Add your first astrologer!</div>
        ) : (
          <div className="table-container">
            <table className="astrologers-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Expertise</th>
                  <th>Experience</th>
                  <th>Fee</th>
                  <th>Rating</th>
                  <th>Status</th>
                  <th>Verified</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {astrologers.map(astrologer => (
                  <tr key={astrologer.astrologer_id}>
                    <td>{astrologer.astrologer_id}</td>
                    <td>
                      <div className="astrologer-name">
                        {astrologer.profile_image_url && (
                          <img 
                            src={astrologer.profile_image_url} 
                            alt={astrologer.full_name}
                            className="astrologer-thumb"
                          />
                        )}
                        <div>
                          <div className="full-name">{astrologer.full_name}</div>
                          <div className="display-name">{astrologer.display_name}</div>
                        </div>
                      </div>
                    </td>
                    <td>{astrologer.email}</td>
                    <td>{astrologer.expertise || '-'}</td>
                    <td>{astrologer.experience_years}y</td>
                    <td>{astrologer.currency} {astrologer.consultation_fee}</td>
                    <td>
                      <div className="rating-cell">
                        ⭐ {astrologer.rating?.toFixed(1) || 'N/A'}
                        <span className="reviews-count">({astrologer.total_reviews || 0})</span>
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${astrologer.is_active ? 'active' : 'inactive'}`}>
                        {astrologer.is_active ? '✅ Active' : '❌ Inactive'}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`verify-btn ${astrologer.is_verified ? 'verified' : 'unverified'}`}
                        onClick={() => handleToggleVerified(astrologer.astrologer_id, astrologer.is_verified)}
                        title={astrologer.is_verified ? 'Click to unverify' : 'Click to verify'}
                      >
                        {astrologer.is_verified ? '✓ Verified' : '⚠ Unverified'}
                      </button>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="btn-edit"
                          onClick={() => handleEditAstrologer(astrologer)}
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-edit"
                          onClick={() => openChargesModal(astrologer)}
                          title="Manage Charges"
                        >
                          💰
                        </button>
                        <button
                          className="btn-edit"
                          onClick={() => openAvailabilityModal(astrologer)}
                          title="Manage Availability"
                        >
                          🗓️
                        </button>
                        <button
                          className="btn-delete"
                          onClick={() => handleDeleteAstrologer(astrologer.astrologer_id)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default AstrologerMaster;
