import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import './styles/registration.css';

const DEFAULT_API = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

function RegistrationWizard() {
  const navigate = useNavigate();
  const API_URL = DEFAULT_API;

  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    full_name: '',
    dob: '',
    gender: 'female',
    relationship_status: '',
    professional_status: '',
    profession: '',
    email: '',
    phoneNo: '',
    username: '',
    password: '',
    mpin: ''
  });

  const [relationshipList, setRelationshipList] = useState([]);
  const [professionalStatusList, setProfessionalStatusList] = useState([]);
  const [professionList, setProfessionList] = useState([]);

  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (patch) => setForm(prev => ({ ...prev, ...patch }));

  const next = () => setStep(s => Math.min(4, s + 1));
  const back = () => setStep(s => Math.max(1, s - 1));

  const submit = async () => {
    setMsg('');
    // basic validation for required fields
    if (!form.full_name || !form.dob || !form.gender) {
      setMsg('Please fill all required fields');
      return;
    }
    if (!/^\d{6}$/.test(form.mpin || '')) {
      setMsg('MPIN must be 6 digits');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        full_name: form.full_name,
        email: form.email,
        phoneNo: form.phoneNo,
        username: form.username,
        password: form.password,
        mpin: form.mpin,
        dob: form.dob,
        gender: form.gender,
        relationship_status_key: form.relationship_status,
        professional_status_key: form.professional_status,
        profession_key: form.profession,
        authtoken: '7fl1hNmYcQiQXm47i1YWZ9eh08oycCqrm5xgYvu_L4s'
      };

      const userId = localStorage.getItem('userId');
      const authToken = localStorage.getItem('authToken');
      const isEditing = userId && authToken;

      // Use PUT for updating existing profile or POST for new registration
      const url = isEditing ? `${API_URL}/api/user-profile/${userId}` : `${API_URL}/api/register`;
      const method = isEditing ? 'PUT' : 'POST';
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (isEditing) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const res = await fetch(url, {
        method: method,
        headers: headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setMsg(isEditing ? 'Profile updated successfully' : 'Registration successful');
        // optionally store token if returned
        if (data.token) localStorage.setItem('authToken', data.token);
        setTimeout(() => navigate('/subscription-plan'), 1200);
      } else {
        setMsg(data.message || (isEditing ? 'Profile update failed' : 'Registration failed'));
      }
    } catch (err) {
      console.error(err);
      setMsg('Error connecting to server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch user profile data if editing existing profile
    const fetchUserProfile = async () => {
      try {
        const userId = localStorage.getItem('userId');
        const authToken = localStorage.getItem('authToken');
        
        if (userId && authToken) {
          const res = await fetch(`${API_URL}/api/user-profile/${userId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${authToken}`
            }
          });
          
          if (res.ok) {
            const data = await res.json();
            if (data.success && data.user) {
              // Pre-fill the form with user data
              setForm(prev => ({
                ...prev,
                full_name: data.user.full_name || '',
                dob: data.user.dob || '',
                gender: data.user.gender || 'female',
                relationship_status: data.user.relationship_status || '',
                professional_status: data.user.professional_status || '',
                profession: data.user.profession || '',
                email: data.user.email || '',
                phoneNo: data.user.phoneNo || '',
                username: data.user.username || '',
                password: data.user.password || '',
                mpin: data.user.mpin || ''
              }));
            }
          }
        }
      } catch (err) {
        console.error('Error fetching user profile:', err);
      }
    };

    fetchUserProfile();
    
    // fetch lookup lists from backend
    const fetchLists = async () => {
      try {
        const [relRes, profStatRes, profRes] = await Promise.all([
          fetch(`${API_URL}/api/relationship-statuses`),
          fetch(`${API_URL}/api/professional-statuses`),
          fetch(`${API_URL}/api/professions`)
        ]);

        if (relRes.ok) {
          const relData = await relRes.json();
          setRelationshipList(relData.data || []);
        }
        if (profStatRes.ok) {
          const ps = await profStatRes.json();
          setProfessionalStatusList(ps.data || []);
        }
        if (profRes.ok) {
          const pr = await profRes.json();
          setProfessionList(pr.data || []);
        }
      } catch (err) {
        console.error('Error fetching lookup lists', err);
        // do not block the wizard; show a small message
        setMsg('Could not load some lookup lists — using defaults');
      }
    };
    fetchLists();
  }, [API_URL]);

  return (
    <div className="reg-hero">
      <Header />
      <div className="reg-card">
        <div className="reg-icon">{step === 1 ? '👤' : step === 2 ? '💜' : step === 3 ? '💼' : '✅'}</div>
        <h2 className="reg-title">{step}. {step === 1 ? 'Personal Details' : step === 2 ? 'Relationship Details' : step === 3 ? 'Professional Details' : 'Confirmation'}</h2>

        {step === 1 && (
          <div className="reg-step">
            <label className="reg-label">Your Name</label>
            <input className="reg-input" value={form.full_name} onChange={e => update({ full_name: e.target.value })} placeholder="Your Name" />

            <label className="reg-label" style={{ marginTop: 16 }}>Date Of Birth</label>
            <input type="date" className="reg-input" value={form.dob} onChange={e => update({ dob: e.target.value })} />

            <div style={{ marginTop: 12 }}>
              <label className="reg-label">Gender</label>
              <div className="reg-row">
                <label><input type="radio" name="gender" checked={form.gender === 'female'} onChange={() => update({ gender: 'female' })} /> Female</label>
                <label><input type="radio" name="gender" checked={form.gender === 'male'} onChange={() => update({ gender: 'male' })} /> Male</label>
                <label><input type="radio" name="gender" checked={form.gender === 'other'} onChange={() => update({ gender: 'other' })} /> Other</label>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="reg-step">
            <p className="reg-sub">Tell us about your relationship status. Numerology can help you discover what's waiting for you</p>
            <label className="reg-label">Relationship Status</label>
            <select className="reg-input" value={form.relationship_status} onChange={e => update({ relationship_status: e.target.value })}>
              <option value="">Select</option>
              {relationshipList.length > 0 ? (
                relationshipList.map(r => (
                  <option key={r.code} value={r.display_value}>{r.display_value}</option>
                ))
              ) : (
                // fallback options
                <>
                  <option value="single">Single</option>
                  <option value="in_relationship">In a Relationship</option>
                  <option value="married">Married</option>
                  <option value="complicated">It's Complicated</option>
                </>
              )}
            </select>
          </div>
        )}

        {step === 3 && (
          <div className="reg-step">
            <p className="reg-sub">Looking for job or success in job, numerology can bring better solutions to achieve your career goals.</p>
            <label className="reg-label">Professional Status</label>
            <select className="reg-input" value={form.professional_status} onChange={e => update({ professional_status: e.target.value })}>
              <option value="">Select</option>
              {professionalStatusList.length > 0 ? (
                professionalStatusList.map(p => (
                  <option key={p.code} value={p.display_value}>{p.display_value}</option>
                ))
              ) : (
                <>
                  <option value="student">Student</option>
                  <option value="employed">Employed</option>
                  <option value="self_employed">Self Employed</option>
                  <option value="unemployed">Unemployed</option>
                </>
              )}
            </select>

            <label className="reg-label">Choose Your Profession</label>
            <select className="reg-input" value={form.profession} onChange={e => update({ profession: e.target.value })}>
              <option value="">Select</option>
              {professionList.length > 0 ? (
                professionList.map(p => (
                  <option key={p.code} value={p.display_value}>{p.display_value}</option>
                ))
              ) : (
                <>
                  <option value="engineer">Engineer</option>
                  <option value="doctor">Doctor</option>
                  <option value="teacher">Teacher</option>
                  <option value="business">Business</option>
                </>
              )}
            </select>

            <div style={{ marginTop: 12 }}>
              <label className="reg-label">Contact Email</label>
              <input className="reg-input" value={form.email} onChange={e => update({ email: e.target.value })} placeholder="Email" />

              <label className="reg-label" style={{ marginTop: 8 }}>Phone</label>
              <input className="reg-input" value={form.phoneNo} onChange={e => update({ phoneNo: e.target.value })} placeholder="Phone (with country code)" />
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="reg-step">
            <label className="reg-label">Create Username</label>
            <input className="reg-input" value={form.username} onChange={e => update({ username: e.target.value })} />

            <label className="reg-label">Set Password</label>
            <input type="password" className="reg-input" value={form.password} onChange={e => update({ password: e.target.value })} />

            <label className="reg-label">Set 6-digit MPIN</label>
            <input className="reg-input" value={form.mpin} onChange={e => update({ mpin: e.target.value })} placeholder="123456" />
          </div>
        )}

        <div className="reg-actions">
          {step > 1 && <button className="reg-back" onClick={back}>Back</button>}
          {step < 4 && <button className="reg-next" onClick={next}>Next</button>}
          {step === 4 && <button className="reg-submit" onClick={submit} disabled={loading}>{loading ? 'Submitting...' : 'Submit'}</button>}
        </div>

        {msg && <div className="reg-msg">{msg}</div>}
      </div>
    </div>
  );
}

export default RegistrationWizard;
