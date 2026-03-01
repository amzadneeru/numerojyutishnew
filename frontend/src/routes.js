import { createBrowserRouter } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import App from './App';
import Login from './webpages/Login';
import Register from './webpages/Register';
import Signup from './webpages/Signup';
import RegistrationWizard from './webpages/RegistrationWizard';
import Dashboard from './Dashboard';
import ForgotPassword from './webpages/ForgotPassword';
import SubscriptionPlan from './webpages/SubscriptionPlan';
import Products from './webpages/Products';
import ProductDetails from './webpages/ProductDetails';
import ProductMaster from './webpages/admin/ProductMaster';
import AstrologerMaster from './webpages/admin/AstrologerMaster';
import AdminDashboard from './webpages/admin/AdminDashboard';
import AstrologerBookingChargesAdmin from './webpages/admin/AstrologerBookingChargesAdmin';
import Shopping from './webpages/Shopping';
import ConsultAstrologers from './webpages/ConsultAstrologers';
import AstrologerSlotBooking from './webpages/AstrologerSlotBooking';
import AstrologerBookingCharge from './webpages/AstrologerBookingCharge';
import Layout from './layouts/Layout';

function isAdminUser() {
  const role = (localStorage.getItem('userRole') || localStorage.getItem('role') || '').toLowerCase();
  const isAdmin = (localStorage.getItem('isAdmin') || '').toLowerCase();
  return role === 'admin' || isAdmin === 'true' || isAdmin === '1';
}

function AdminRoute({ children }) {
  return children;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout><App /></Layout>,
  },
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/register',
    element: <Register />,
  },
  {
    path: '/signup',
    element: <Signup />,
  },
  {
    path: '/registration-wizard',
    element: <Layout><RegistrationWizard /></Layout>,
  },
  {
    path: '/dashboard',
    element: <Layout><Dashboard /></Layout>,
  },
  {
    path: '/forgot-password',
    element: <ForgotPassword />,
  },
  {
    path: '/subscription-plan',
    element: <Layout><SubscriptionPlan /></Layout>,
  },
  {
    path: '/products',
    element: <Layout><Products /></Layout>,
  },
  {
    path: '/product-details/:productId',
    element: <Layout><ProductDetails /></Layout>,
  },
  {
    path: '/admin/dashboard',
    element: <AdminRoute><Layout><AdminDashboard /></Layout></AdminRoute>,
  },
  {
    path: '/admin/productmaster',
    element: <AdminRoute><Layout><ProductMaster /></Layout></AdminRoute>,
  },
  {
    path: '/admin/astrologermaster',
    element: <AdminRoute><Layout><AstrologerMaster /></Layout></AdminRoute>,
  },
  {
    path: '/admin/booking-charges',
    element: <AdminRoute><Layout><AstrologerBookingChargesAdmin /></Layout></AdminRoute>,
  },
  {
    path: '/shopping',
    element: <Layout><Shopping /></Layout>,
  },
  {
    path: '/consult-astrologers',
    element: <Layout><ConsultAstrologers /></Layout>,
  },
  {
    path: '/consult-astrologers/:astroId',
    element: <Layout><ConsultAstrologers /></Layout>,
  },
  {
    path: '/consult-astrologers/:astroId/book',
    element: <Layout><AstrologerSlotBooking /></Layout>,
  },
  {
    path: '/consult-bookings/:bookingId/charge',
    element: <Layout><AstrologerBookingCharge /></Layout>,
  },
]);