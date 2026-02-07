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

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
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
    element: <RegistrationWizard />,
  },
  {
    path: '/dashboard',
    element: <Dashboard />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPassword />,
  },
  {
    path: '/subscription-plan',
    element: <SubscriptionPlan />,
  },
  {
    path: '/products',
    element: <Products/>,
  },
  {
    path: '/product-details/:productId',
    element: <ProductDetails/>,
  },
  {
    path: '/admin/productmaster',
    element: <ProductMaster />,
  },
]);