import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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

  return (
    <div className="astrologer-master-container">
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
