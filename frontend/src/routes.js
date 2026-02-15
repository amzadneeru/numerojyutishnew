import { createBrowserRouter } from 'react-router-dom';
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
import Shopping from './webpages/Shopping';
import ConsultAstrologers from './webpages/ConsultAstrologers';
import Layout from './layouts/Layout';

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
    path: '/admin/productmaster',
    element: <Layout><ProductMaster /></Layout>,
  },
  {
    path: '/admin/astrologermaster',
    element: <Layout><AstrologerMaster /></Layout>,
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
]);