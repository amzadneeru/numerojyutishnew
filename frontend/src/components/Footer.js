import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Footer.css';

function Footer() {
  const navigate = useNavigate();
  const currentYear = new Date().getFullYear();

  const handleNavigate = (path) => {
    navigate(path);
    window.scrollTo(0, 0);
  };

  return (
    <footer className="footer">
      <div className="footer-container">
        {/* Main Content */}
        <div className="footer-content">
          {/* Brand Section */}
          <div className="footer-section brand-section">
            <h3>NUMRO JYOTISH</h3>
            <p>Connect with expert astrologers and unlock the wisdom of the stars.</p>
            <div className="social-links">
              <a href="#" className="social-link" title="Facebook">f</a>
              <a href="#" className="social-link" title="Twitter">𝕏</a>
              <a href="#" className="social-link" title="Instagram">📷</a>
              <a href="#" className="social-link" title="LinkedIn">in</a>
            </div>
          </div>

          {/* Quick Links */}
          <div className="footer-section">
            <h4>Quick Links</h4>
            <ul>
              <li><button onClick={() => handleNavigate('/')}>Home</button></li>
              <li><button onClick={() => handleNavigate('/products')}>Products</button></li>
              <li><button onClick={() => handleNavigate('/consult-astrologers')}>Astrologers</button></li>
              <li><button onClick={() => handleNavigate('/subscription-plan')}>Plans</button></li>
            </ul>
          </div>

          {/* Services */}
          <div className="footer-section">
            <h4>Services</h4>
            <ul>
              <li><button onClick={() => handleNavigate('/shopping')}>Shopping</button></li>
              <li><a href="#features">Numerology Reading</a></li>
              <li><a href="#services">Astrology Consultation</a></li>
              <li><a href="#support">Live Chat Support</a></li>
            </ul>
          </div>

          {/* Support */}
          <div className="footer-section">
            <h4>Support</h4>
            <ul>
              <li><a href="mailto:support@numerojyotish.com">📧 Email</a></li>
              <li><a href="tel:+919999999999">📞 Call/WhatsApp</a></li>
              <li><a href="#faq">FAQ</a></li>
              <li><a href="#contact">Contact Us</a></li>
            </ul>
          </div>

          {/* Legal */}
          <div className="footer-section">
            <h4>Legal</h4>
            <ul>
              <li><a href="#privacy">Privacy Policy</a></li>
              <li><a href="#terms">Terms of Service</a></li>
              <li><a href="#cookies">Cookie Policy</a></li>
              <li><a href="#disclaimer">Disclaimer</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <p className="copyright">
            &copy; {currentYear} Numro Jyotish. All rights reserved.
          </p>
          <div className="footer-badges">
            <span className="badge">🔒 Secure</span>
            <span className="badge">📱 Mobile Friendly</span>
            <span className="badge">⚡ Fast</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
