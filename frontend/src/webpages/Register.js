import React, { useState } from 'react';
import '../styles/Login.css';
import { useNavigate } from 'react-router-dom';

function Register() {
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regDob, setRegDob] = useState('');
  const [regGender, setRegGender] = useState('');
  const [regMpin, setRegMpin] = useState('');
  const [regRole, setRegRole] = useState('End user who will buy subscription');
  const [regMsg, setRegMsg] = useState('');
  const navigate = useNavigate();
  // Prefer an explicit REACT_APP_API_URL for deployed builds.
  // While developing locally (NODE_ENV === 'development') use localhost.
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : 'https://your-production-api.example.com');

  const handleRegister = async () => {
    setRegMsg('');
    if (!regFullName || !regEmail || !regPhone || !regUsername || !regPassword || !regConfirmPassword || !regMpin || !regDob || !regGender) {
      setRegMsg('Please fill all required fields.');
      return;
    }
    if (!/^[0-9]{6}$/.test(regMpin)) {
      setRegMsg('MPIN must be 6 digits.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegMsg('Passwords do not match.');
      return;
    }

    try {
  const res = await fetch(`${API_URL}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: regFullName,
          email: regEmail,
          phoneNo: regPhone,
          username: regUsername,
          password: regPassword,
          mpin: regMpin,
          user_role: regRole,
          dob: regDob,
          gender: regGender
        }),
      });
      const data = await res.json();
      if (res.status === 201) {
        setRegMsg('Registration successful! You can now log in.');
        setTimeout(() => navigate('/'), 1200);
      } else {
        setRegMsg(data.message || 'Registration failed');
      }
    } catch (err) {
      setRegMsg('Could not connect to server.');
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-box">
        <h1 className="login-title">Create account</h1>
        <input type="text" placeholder="Full name" value={regFullName} onChange={e => setRegFullName(e.target.value)} className="login-input" />
        <input type="email" placeholder="Email" value={regEmail} onChange={e => setRegEmail(e.target.value)} className="login-input" />
        <input type="text" placeholder="Phone number" value={regPhone} onChange={e => setRegPhone(e.target.value)} className="login-input" />
        <input type="text" placeholder="Username" value={regUsername} onChange={e => setRegUsername(e.target.value)} className="login-input" />
        <input type="password" placeholder="Password" value={regPassword} onChange={e => setRegPassword(e.target.value)} className="login-input" />
        <input type="password" placeholder="Confirm Password" value={regConfirmPassword} onChange={e => setRegConfirmPassword(e.target.value)} className="login-input" />
        <input type="date" placeholder="Date of Birth" value={regDob} onChange={e => setRegDob(e.target.value)} className="login-input" />
        <select value={regGender} onChange={e => setRegGender(e.target.value)} className="login-input">
          <option value="">Select Gender</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
        <input type="text" placeholder="MPIN (6 digits)" value={regMpin} onChange={e => setRegMpin(e.target.value)} className="login-input" />
        <select value={regRole} onChange={e => setRegRole(e.target.value)} className="login-input">
          <option>End user who will buy subscription</option>
          <option>Internal user how will manage app</option>
          <option>Student</option>
          <option>Numerology consultant</option>
          <option>Super user</option>
          <option>Admin</option>
        </select>
        <div style={{display: 'flex', gap: '8px'}}>
          <button onClick={handleRegister} className="login-button">Register</button>
          <button className="forgot-link" onClick={() => navigate('/')}>Cancel</button>
        </div>
        {regMsg && <p className="login-msg">{regMsg}</p>}
      </div>
    </div>
  );
}

export default Register;
