import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import Dashboard from './Dashboard';
import ForgotPassword from './webpages/ForgotPassword';
import Register from './webpages/Register';
import Signup from './webpages/Signup';
import RegistrationWizard from './webpages/RegistrationWizard';
import SubscriptionPlan from './webpages/SubscriptionPlan';
import SocialCallback from './webpages/SocialCallback';
import reportWebVitals from './reportWebVitals';
import Products from './webpages/Products';
import ProductMaster from './webpages/admin/ProductMaster';
import ConsultAstrologers from './webpages/ConsultAstrologers';
import AstrologerMaster from './webpages/admin/AstrologerMaster';
import AdminDashboard from './webpages/admin/AdminDashboard';
import AstrologerBookingChargesAdmin from './webpages/admin/AstrologerBookingChargesAdmin';
import EnquiryAdmin from './webpages/admin/EnquiryAdmin';
import Shopping from './webpages/Shopping';
import AstrologerSlotBooking from './webpages/AstrologerSlotBooking';
import AstrologerBookingCharge from './webpages/AstrologerBookingCharge';
import MyConsultationBookings from './webpages/MyConsultationBookings';
import MySubscriptions from './webpages/MySubscriptions';
import SubscriptionPayment from './webpages/SubscriptionPayment';
import Enquiry from './webpages/Enquiry';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function isAdminUser() {
  const role = (localStorage.getItem('userRole') || localStorage.getItem('role') || '').toLowerCase();
  const isAdmin = (localStorage.getItem('isAdmin') || '').toLowerCase();
  return role === 'admin' || isAdmin === 'true' || isAdmin === '1';
}

function AdminRoute({ children }) {
  return children;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/register" element={<Register />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/registration-wizard" element={<RegistrationWizard />} />
        <Route path="/products" element={<Products/>} />
        <Route path="/admin/dashboard" element={<AdminRoute><AdminDashboard/></AdminRoute>} />
        <Route path="/admin/productmaster" element={<AdminRoute><ProductMaster/></AdminRoute>} />
        <Route path="/admin/booking-charges" element={<AdminRoute><AstrologerBookingChargesAdmin/></AdminRoute>} />
        <Route path="/admin/enquiries" element={<AdminRoute><EnquiryAdmin/></AdminRoute>} />
        <Route path="/subscription-plan" element={<SubscriptionPlan />} />
        <Route path="/auth/callback/:provider" element={<SocialCallback />} />
        <Route path="/social-callback" element={<SocialCallback />} />
        <Route path="/shopping" element={<Shopping/>} />
        <Route path="/consult-astrologers" element={<ConsultAstrologers />} />
        <Route path="/consult-astrologers/:astroId" element={<ConsultAstrologers />} />
        <Route path="/consult-astrologers/:astroId/book" element={<AstrologerSlotBooking />} />
        <Route path="/consult-bookings/:bookingId/charge" element={<AstrologerBookingCharge />} />
        <Route path="/my-consultation-bookings" element={<MyConsultationBookings />} />
        <Route path="/my-subscriptions" element={<MySubscriptions />} />
        <Route path="/subscription-payment" element={<SubscriptionPayment />} />
        <Route path="/enquiry" element={<Enquiry />} />
        <Route path="/admin/astrologermaster" element={<AdminRoute><AstrologerMaster /></AdminRoute>} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

reportWebVitals();
