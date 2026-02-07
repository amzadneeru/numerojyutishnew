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

import { BrowserRouter, Routes, Route } from 'react-router-dom';

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
        <Route path="/admin/productmaster" element={<ProductMaster/>} />
        <Route path="/subscription-plan" element={<SubscriptionPlan />} />
        <Route path="/auth/callback/:provider" element={<SocialCallback />} />
        <Route path="/social-callback" element={<SocialCallback />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

reportWebVitals();
