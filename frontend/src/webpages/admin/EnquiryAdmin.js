import React, { useEffect, useState } from 'react';
import AdminHeader from '../../components/AdminHeader';
import '../../styles/AdminEnquiry.css';

function EnquiryAdmin() {
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  const [enquiries, setEnquiries] = useState([]);
  const [editingMap, setEditingMap] = useState({});
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchEnquiries();
  }, [statusFilter]);

  const fetchEnquiries = async () => {
    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const query = statusFilter ? `?enquiry_status=${encodeURIComponent(statusFilter)}` : '';
      const response = await fetch(`${API_URL}/api/enquiries${query}`);
      const data = await response.json();

      if (!response.ok || !data.success) {
        setError(data.message || 'Failed to load enquiries');
        return;
      }

      const rows = data.data || [];
      setEnquiries(rows);

      const initial = {};
      rows.forEach((row) => {
        initial[row.enquiry_id] = {
          comment: row.comment || '',
          enquiry_status: row.enquiry_status || 'Pending'
        };
      });
      setEditingMap(initial);
    } catch (err) {
      setError('Unable to load enquiries');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (enquiryId) => {
    const draft = editingMap[enquiryId];
    if (!draft) return;

    try {
      setSavingId(enquiryId);
      setError('');
      setSuccess('');

      const response = await fetch(`${API_URL}/api/enquiries/${enquiryId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          comment: draft.comment,
          enquiry_status: draft.enquiry_status
        })
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        setError(data.message || 'Failed to update enquiry');
        return;
      }

      setSuccess(`Enquiry #${enquiryId} updated successfully`);
      fetchEnquiries();
    } catch (err) {
      setError('Unable to update enquiry');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="admin-enquiry-page">
      <AdminHeader />
      <main className="admin-enquiry-main">
        <h1>Enquiry Management</h1>
        <p className="admin-enquiry-subtitle">View all enquiries and update comment/status.</p>

        {error && <p className="error-message">{error}</p>}
        {success && <p className="success-message">{success}</p>}

        <div className="admin-enquiry-filters">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Status</option>
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <button type="button" onClick={fetchEnquiries}>Refresh</button>
        </div>

        {loading ? (
          <p className="loading">Loading enquiries...</p>
        ) : (
          <div className="admin-enquiry-table-wrap">
            <table className="admin-enquiry-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>User Info</th>
                  <th>Enquiry</th>
                  <th>Birth Details</th>
                  <th>Status</th>
                  <th>Comment</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {enquiries.map((item) => (
                  <tr key={item.enquiry_id}>
                    <td>#{item.enquiry_id}</td>
                    <td>
                      <div><strong>{item.name}</strong></div>
                      <div>{item.gender || '-'}</div>
                      <div>{item.phone_no}</div>
                      <div>{item.email || '-'}</div>
                    </td>
                    <td>
                      <div><strong>{item.enquiry_type || '-'}</strong></div>
                      <div className="enquiry-desc">{item.description || '-'}</div>
                    </td>
                    <td>
                      <div>DOB: {item.date_of_birth || '-'}</div>
                      <div>Time: {item.birth_time || '-'}</div>
                      <div>Place: {item.birth_place || '-'}</div>
                    </td>
                    <td>
                      <select
                        value={editingMap[item.enquiry_id]?.enquiry_status || 'Pending'}
                        onChange={(e) => {
                          const val = e.target.value;
                          setEditingMap((prev) => ({
                            ...prev,
                            [item.enquiry_id]: {
                              ...prev[item.enquiry_id],
                              enquiry_status: val
                            }
                          }));
                        }}
                      >
                        <option value="Pending">Pending</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Completed">Completed</option>
                        <option value="Cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td>
                      <textarea
                        rows={3}
                        value={editingMap[item.enquiry_id]?.comment || ''}
                        onChange={(e) => {
                          const val = e.target.value;
                          setEditingMap((prev) => ({
                            ...prev,
                            [item.enquiry_id]: {
                              ...prev[item.enquiry_id],
                              comment: val
                            }
                          }));
                        }}
                        placeholder="Add admin comment"
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => handleSave(item.enquiry_id)}
                        disabled={savingId === item.enquiry_id}
                      >
                        {savingId === item.enquiry_id ? 'Saving...' : 'Save'}
                      </button>
                    </td>
                  </tr>
                ))}
                {enquiries.length === 0 && (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center' }}>No enquiries found.</td>
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

export default EnquiryAdmin;
