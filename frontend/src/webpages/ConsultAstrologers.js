import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import '../styles/ConsultAstrologers.css';

function ConsultAstrologers() {
  const navigate = useNavigate();
  const { astroId } = useParams();

  // State Management
  const [view, setView] = useState(astroId ? 'profile' : 'list'); // 'list', 'profile', 'search', 'topRated'
  const [astrologers, setAstrologers] = useState([]);
  const [selectedAstrologer, setSelectedAstrologer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // User Auth
  const userId = localStorage.getItem('userId');
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Filters
  const [filters, setFilters] = useState({
    expertise: '',
    language: '',
    minRating: 0,
    verifiedOnly: false,
    searchQuery: ''
  });

  const [pagination, setPagination] = useState({
    limit: 20,
    offset: 0,
    total: 0
  });

  // Load astrologers on component mount
  useEffect(() => {
    if (astroId) {
      fetchAstrologerProfile(astroId);
    } else {
      fetchAstrologers();
    }
  }, [astroId]);

  // Fetch all astrologers with filters
  const fetchAstrologers = async (offset = 0) => {
    try {
      setLoading(true);
      setError('');

      const params = new URLSearchParams();
      if (filters.expertise) params.append('expertise', filters.expertise);
      if (filters.language) params.append('language', filters.language);
      if (filters.minRating) params.append('min_rating', filters.minRating);
      if (filters.verifiedOnly) params.append('verified_only', 'true');
      params.append('limit', pagination.limit);
      params.append('offset', offset);

      const res = await fetch(`${API_URL}/api/astrologers?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAstrologers(data.data);
        setPagination(prev => ({
          ...prev,
          total: data.pagination.total,
          offset: offset
        }));
        setView('list');
      } else {
        setError('Failed to load astrologers');
      }
    } catch (err) {
      console.error('Error fetching astrologers:', err);
      setError('Error loading astrologers');
    } finally {
      setLoading(false);
    }
  };

  // Fetch single astrologer profile
  const fetchAstrologerProfile = async (id) => {
    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/astrologers/${id}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        const data = await res.json();
        setSelectedAstrologer(data.data);
        setView('profile');
      } else {
        setError('Failed to load astrologer profile');
      }
    } catch (err) {
      console.error('Error fetching astrologer:', err);
      setError('Error loading astrologer');
    } finally {
      setLoading(false);
    }
  };

  // Search astrologers
  const handleSearch = async (query) => {
    if (!query.trim()) {
      fetchAstrologers();
      return;
    }

    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/astrologers/search?q=${encodeURIComponent(query)}&limit=50`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAstrologers(data.data);
        setView('search');
      } else {
        setError('Search failed');
      }
    } catch (err) {
      console.error('Error searching:', err);
      setError('Search error');
    } finally {
      setLoading(false);
    }
  };

  // Get top-rated astrologers
  const fetchTopRated = async () => {
    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${API_URL}/api/astrologers/top-rated?limit=20&min_reviews=5`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAstrologers(data.data);
        setView('topRated');
      } else {
        setError('Failed to load top-rated astrologers');
      }
    } catch (err) {
      console.error('Error fetching top-rated:', err);
      setError('Error loading top-rated astrologers');
    } finally {
      setLoading(false);
    }
  };

  // Submit rating
  const handleSubmitRating = async (rating) => {
    if (!userId) {
      setError('Please log in to submit a rating');
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/astrologers/${selectedAstrologer.astrologer_id}/rating`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          user_id: userId,
          rating: rating
        })
      });

      if (res.ok) {
        const data = await res.json();
        setSuccessMessage('Rating submitted successfully!');
        setSelectedAstrologer(prev => ({
          ...prev,
          rating: data.data.rating,
          total_reviews: data.data.total_reviews
        }));
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError('Failed to submit rating');
      }
    } catch (err) {
      console.error('Error submitting rating:', err);
      setError('Error submitting rating');
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const handleApplyFilters = () => {
    setPagination(prev => ({ ...prev, offset: 0 }));
    fetchAstrologers(0);
  };

  // Reset filters
  const handleResetFilters = () => {
    setFilters({
      expertise: '',
      language: '',
      minRating: 0,
      verifiedOnly: false,
      searchQuery: ''
    });
    fetchAstrologers(0);
  };

  // Pagination handlers
  const handleNextPage = () => {
    const newOffset = pagination.offset + pagination.limit;
    if (newOffset < pagination.total) {
      fetchAstrologers(newOffset);
      window.scrollTo(0, 0);
    }
  };

  const handlePrevPage = () => {
    const newOffset = Math.max(0, pagination.offset - pagination.limit);
    fetchAstrologers(newOffset);
    window.scrollTo(0, 0);
  };

  // Render Astrologer Card
  const renderAstrologerCard = (astro) => (
    <div key={astro.astrologer_id} className="astrologer-card">
      {astro.profile_image_url && (
        <img src={astro.profile_image_url} alt={astro.full_name} className="astro-avatar" />
      )}
      <div className="astro-info">
        <h3>{astro.display_name || astro.full_name}</h3>
        {astro.is_verified && <span className="verified-badge">✓ Verified</span>}
        
        <p className="expertise">{astro.expertise || 'Astrology'}</p>
        <p className="experience">📅 {astro.experience_years || 0} years experience</p>
        <p className="languages">🗣️ {astro.languages || 'Languages not specified'}</p>

        <div className="rating-section">
          <span className="star">⭐ {astro.rating || 0}/5.0</span>
          <span className="reviews">({astro.total_reviews || 0} reviews)</span>
        </div>

        <p className="fee">
          <strong>Fee: ₹{astro.consultation_fee}</strong>
        </p>

        {astro.bio && <p className="bio">{astro.bio.substring(0, 100)}...</p>}

        <button
          onClick={() => fetchAstrologerProfile(astro.astrologer_id)}
          className="view-profile-btn"
        >
          View Profile
        </button>
      </div>
    </div>
  );

  // Render Profile View
  if (view === 'profile' && selectedAstrologer) {
    return (
      <div className="consult-container profile-view">
        <button onClick={() => setView('list')} className="back-btn">← Back to Astrologers</button>

        <div className="profile-header">
          {selectedAstrologer.profile_image_url && (
            <img src={selectedAstrologer.profile_image_url} alt={selectedAstrologer.full_name} className="profile-avatar" />
          )}
          <div className="profile-details">
            <h1>{selectedAstrologer.full_name}</h1>
            {selectedAstrologer.is_verified && <span className="verified-badge">✓ Verified Astrologer</span>}
            
            <div className="rating-display">
              <span className="star">⭐ {selectedAstrologer.rating || 0}/5.0</span>
              <span className="reviews">({selectedAstrologer.total_reviews || 0} reviews)</span>
            </div>

            <div className="details-grid">
              <div className="detail-item">
                <label>Experience:</label>
                <span>{selectedAstrologer.experience_years || 0} years</span>
              </div>
              <div className="detail-item">
                <label>Gender:</label>
                <span>{selectedAstrologer.gender || 'Not specified'}</span>
              </div>
              <div className="detail-item">
                <label>Languages:</label>
                <span>{selectedAstrologer.languages || 'Not specified'}</span>
              </div>
              <div className="detail-item">
                <label>Expertise:</label>
                <span>{selectedAstrologer.expertise || 'Astrology'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="profile-content">
          <div className="bio-section">
            <h2>About</h2>
            <p>{selectedAstrologer.bio || 'No bio available'}</p>
          </div>

          <div className="consultation-section">
            <h2>Consultation Fee</h2>
            <p className="fee-display">
              {selectedAstrologer.currency} {selectedAstrologer.consultation_fee}
            </p>
            <button className="book-consultation-btn">
              Book Consultation
            </button>
          </div>

          <div className="rating-section">
            <h2>Rate This Astrologer</h2>
            <div className="rating-buttons">
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  onClick={() => handleSubmitRating(star)}
                  className="star-btn"
                  title={`Rate ${star} stars`}
                >
                  {star} ⭐
                </button>
              ))}
            </div>
          </div>
        </div>

        {successMessage && <p className="success-message">{successMessage}</p>}
        {error && <p className="error-message">{error}</p>}
      </div>
    );
  }

  // Default: List View
  return (
    <div className="consult-container">
      <div className="consult-header">
        <h1>Consult with Expert Astrologers</h1>
        <p>Connect with verified astrologers for personalized insights</p>
      </div>

      {/* Search Bar */}
      <div className="search-section">
        <input
          type="text"
          placeholder="Search by name or expertise..."
          value={filters.searchQuery}
          onChange={(e) => setFilters(prev => ({ ...prev, searchQuery: e.target.value }))}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch(filters.searchQuery)}
          className="search-input"
        />
        <button onClick={() => handleSearch(filters.searchQuery)} className="search-btn">
          Search
        </button>
        <button onClick={fetchTopRated} className="top-rated-btn">
          ⭐ Top Rated
        </button>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <div className="filter-group">
          <label>Expertise:</label>
          <input
            type="text"
            placeholder="e.g., Vedic, Tarot"
            value={filters.expertise}
            onChange={(e) => setFilters(prev => ({ ...prev, expertise: e.target.value }))}
          />
        </div>

        <div className="filter-group">
          <label>Language:</label>
          <input
            type="text"
            placeholder="e.g., English, Hindi"
            value={filters.language}
            onChange={(e) => setFilters(prev => ({ ...prev, language: e.target.value }))}
          />
        </div>

        <div className="filter-group">
          <label>Min Rating:</label>
          <select
            value={filters.minRating}
            onChange={(e) => setFilters(prev => ({ ...prev, minRating: parseFloat(e.target.value) }))}
          >
            <option value="0">All Ratings</option>
            <option value="3">3+ Stars</option>
            <option value="4">4+ Stars</option>
            <option value="4.5">4.5+ Stars</option>
          </select>
        </div>

        <div className="filter-group">
          <label>
            <input
              type="checkbox"
              checked={filters.verifiedOnly}
              onChange={(e) => setFilters(prev => ({ ...prev, verifiedOnly: e.target.checked }))}
            />
            Show Verified Only
          </label>
        </div>

        <div className="filter-buttons">
          <button onClick={handleApplyFilters} className="apply-filters-btn">
            Apply Filters
          </button>
          <button onClick={handleResetFilters} className="reset-filters-btn">
            Reset
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && <p className="error-message">{error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}

      {/* Loading State */}
      {loading && <p className="loading">Loading astrologers...</p>}

      {/* Astrologers Grid */}
      {!loading && astrologers.length > 0 && (
        <>
          <div className="astrologers-grid">
            {astrologers.map(astro => renderAstrologerCard(astro))}
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button
              onClick={handlePrevPage}
              disabled={pagination.offset === 0}
              className="page-btn"
            >
              ← Previous
            </button>
            <span className="page-info">
              Showing {pagination.offset + 1} - {Math.min(pagination.offset + pagination.limit, pagination.total)} of {pagination.total}
            </span>
            <button
              onClick={handleNextPage}
              disabled={pagination.offset + pagination.limit >= pagination.total}
              className="page-btn"
            >
              Next →
            </button>
          </div>
        </>
      )}

      {!loading && astrologers.length === 0 && (
        <p className="no-results">No astrologers found. Try adjusting your filters.</p>
      )}
    </div>
  );
}

export default ConsultAstrologers;
