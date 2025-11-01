import React, { useState } from 'react';
import '../styles/Login.css';
import { useNavigate } from 'react-router-dom';

function Register() {
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regMpin, setRegMpin] = useState('');
  const [regRole, setRegRole] = useState('End user who will buy subscription');
  const [regMsg, setRegMsg] = useState('');
  const navigate = useNavigate();

  const handleRegister = async () => {
    setRegMsg('');
    if (!regFullName || !regEmail || !regPhone || !regUsername || !regPassword || !regMpin) {
      setRegMsg('Please fill all required fields.');
      return;
    }
    if (!/^[0-9]{6}$/.test(regMpin)) {
      setRegMsg('MPIN must be 6 digits.');
      return;
    }

    try {
      const res = await fetch('http://localhost:5000/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: regFullName,
          email: regEmail,
          phoneNo: regPhone,
          username: regUsername,
          password: regPassword,
          mpin: regMpin,
          user_role: regRole
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
