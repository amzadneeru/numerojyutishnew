import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import '../styles/ProductDetails.css';

function ProductDetails() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState(0);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const userEmail = localStorage.getItem('email') || 'User';
  const userInitials = userEmail.charAt(0).toUpperCase();
  const authToken = localStorage.getItem('authToken');
  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Check if user is authenticated
  useEffect(() => {
    if (!authToken) {
      navigate('/login');
    }
  }, [authToken, navigate]);

  useEffect(() => {
    const fetchProductDetails = async () => {
      try {
        setLoading(true);
        setError('');

        if (!productId) {
          throw new Error('Product ID is missing');
        }

        // Fetch product from the new endpoint
        const res = await fetch(
          `${API_URL}/api/product-details`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              ...(authToken && { 'Authorization': `Bearer ${authToken}` })
            }
          }
        );

        if (!res.ok) {
          throw new Error('Failed to fetch product details');
        }

        const data = await res.json();

        if (data.success && data.data) {
          // Find the specific product
          const foundProduct = data.data.find(p => p.product_id === parseInt(productId));
          
          if (!foundProduct) {
            throw new Error('Product not found');
          }

          setProduct(foundProduct);
        } else {
          throw new Error(data.message || 'Invalid response format');
        }
      } catch (err) {
        console.error('Error fetching product details:', err);
        setError(err.message || 'Failed to load product details. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    if (authToken) {
      fetchProductDetails();
    }
  }, [API_URL, productId, authToken]);

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    localStorage.removeItem('selectedPlan');
    navigate('/login');
  };

  const handleMyAccount = () => {
    setShowUserMenu(false);
    navigate('/my-account');
  };

  const handleSettings = () => {
    setShowUserMenu(false);
    navigate('/settings');
  };

  const handleMyProfile = () => {
    setShowUserMenu(false);
    navigate('/registration-wizard');
  };

  const handleAddToCart = () => {
    if (product && product.pricing_active) {
      console.log('Add to cart:', {
        product_id: product.product_id,
        quantity: quantity,
        price: product.base_price,
        tax_id: product.tax_id
      });
      // TODO: Implement add to cart functionality
    }
  };

  const handleQuantityChange = (e) => {
    const value = parseInt(e.target.value);
    if (value > 0) {
      setQuantity(value);
    }
  };

  const handleIncrementQuantity = () => {
    setQuantity(quantity + 1);
  };

  const handleDecrementQuantity = () => {
    if (quantity > 1) {
      setQuantity(quantity - 1);
    }
  };

  // Calculate final price with discount and tax
  const calculatePrice = () => {
    let basePrice = product?.base_price || 0;
    const discountPercent = product?.discount_percent || 0;
    const taxPercent = product?.tax_percent || 0;

    // Apply discount
    const discountAmount = (basePrice * discountPercent) / 100;
    const priceAfterDiscount = basePrice - discountAmount;

    // Apply tax if not inclusive
    let finalPrice = priceAfterDiscount;
    if (!product?.is_tax_inclusive && taxPercent > 0) {
      const taxAmount = (priceAfterDiscount * taxPercent) / 100;
      finalPrice = priceAfterDiscount + taxAmount;
    }

    return {
      basePrice,
      discountAmount,
      discountPercent,
      priceAfterDiscount,
      taxPercent,
      taxAmount: finalPrice - priceAfterDiscount,
      finalPrice
    };
  };

  return (
    <div className="product-details-container">
      {/* Header */}
      <header className="product-details-header">
        <div className="logo">
          <h1>NUMRO</h1>
          <h2>JYOTISH</h2>
        </div>
        <div className="header-actions">
          <button 
            className="back-button"
            onClick={() => navigate('/products')}
          >
            ← Back to Products
          </button>
          <button className="cart-button">
            🛒 Cart <span className="badge">0</span>
          </button>
          <div className="user-menu-container">
            <button
              className="user-button"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              {userInitials} ▼
            </button>
            {showUserMenu && (
              <div className="user-dropdown">
                <div className="dropdown-header">{userEmail}</div>
                <button className="dropdown-item" onClick={handleMyProfile}>
                  👤 My Profile
                </button>
                <button className="dropdown-item" onClick={handleMyAccount}>
                  ℹ️ My Account
                </button>
                <button className="dropdown-item" onClick={handleSettings}>
                  ⚙️ Settings
                </button>
                <button className="dropdown-item" onClick={() => {
                  setShowUserMenu(false);
                  navigate('/dashboard');
                }}>
                  📊 Dashboard
                </button>
                <div className="dropdown-divider"></div>
                <button className="dropdown-item logout" onClick={handleLogout}>
                  🚪 Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="product-details-main">
        {/* Loading State */}
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading product details...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="error-state">
            <p>❌ {error}</p>
            <button className="retry-button" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        )}

        {/* Product Details */}
        {!loading && !error && product && (
          <div className="product-details-content">
            <div className="product-details-grid">
              {/* Product Images */}
              <div className="product-images-section">
                <div className="main-image-container">
                  <img
                    src={`https://via.placeholder.com/500x500?text=${product.product_name}`}
                    alt={product.product_name}
                    className="main-image"
                  />
                  {!product.product_active && (
                    <div className="product-badge out-of-stock">Out of Stock</div>
                  )}
                </div>
              </div>

              {/* Product Information */}
              <div className="product-info-section">
                {/* Breadcrumb */}
                <div className="breadcrumb">
                  <span>Home</span> / <span>Products</span> / <span>{product.category_name}</span>
                </div>

                {/* Product Title and Category */}
                <h1 className="product-title">{product.product_name}</h1>
                <div className="product-meta">
                  <span className="category-badge">{product.category_name}</span>
                  <span className="country-badge">{product.country_code}</span>
                </div>

                {/* Description */}
                <div className="product-description-box">
                  <h3>Description</h3>
                  <p>{product.product_description || 'No description available'}</p>
                </div>

                {/* Category Description */}
                {product.category_description && (
                  <div className="category-description-box">
                    <h3>Category Information</h3>
                    <p>{product.category_description}</p>
                  </div>
                )}

                {/* Pricing Section */}
                <div className="pricing-section">
                  <h3>Pricing Details</h3>
                  {(() => {
                    const prices = calculatePrice();
                    return (
                      <div className="pricing-details">
                        <div className="price-row">
                          <span className="price-label">Base Price:</span>
                          <span className="price-value">
                            {product.currency_code || '₹'} {prices.basePrice.toLocaleString('en-IN')}
                          </span>
                        </div>

                        {prices.discountPercent > 0 && (
                          <>
                            <div className="price-row discount">
                              <span className="price-label">Discount ({prices.discountPercent}%):</span>
                              <span className="price-value">
                                - {product.currency_code || '₹'} {prices.discountAmount.toLocaleString('en-IN')}
                              </span>
                            </div>
                            <div className="price-row">
                              <span className="price-label">Price After Discount:</span>
                              <span className="price-value">
                                {product.currency_code || '₹'} {prices.priceAfterDiscount.toLocaleString('en-IN')}
                              </span>
                            </div>
                          </>
                        )}

                        {prices.taxPercent > 0 && (
                          <div className="price-row tax">
                            <span className="price-label">
                              Tax ({prices.taxPercent}%) {product.is_tax_inclusive ? '(Inclusive)' : '(Additional)'}:
                            </span>
                            <span className="price-value">
                              {product.currency_code || '₹'} {prices.taxAmount.toLocaleString('en-IN')}
                            </span>
                          </div>
                        )}

                        <div className="price-row final-price">
                          <span className="price-label">Final Price:</span>
                          <span className="price-value">
                            {product.currency_code || '₹'} {prices.finalPrice.toLocaleString('en-IN')}
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Tax Information */}
                {product.tax_id && (
                  <div className="tax-info-section">
                    <h3>Tax Information</h3>
                    <div className="tax-details">
                      <div className="tax-row">
                        <span className="tax-label">Tax Name:</span>
                        <span className="tax-value">{product.tax_name}</span>
                      </div>
                      <div className="tax-row">
                        <span className="tax-label">Tax Rate:</span>
                        <span className="tax-value">{product.tax_percent}%</span>
                      </div>
                      <div className="tax-row">
                        <span className="tax-label">Currency:</span>
                        <span className="tax-value">{product.currency_code}</span>
                      </div>
                      <div className="tax-row">
                        <span className="tax-label">Location:</span>
                        <span className="tax-value">{product.state_code}, {product.country_code}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Status Information */}
                <div className="status-section">
                  <h3>Status</h3>
                  <div className="status-badges">
                    <span className={`status-badge ${product.product_active ? 'active' : 'inactive'}`}>
                      Product: {product.product_active ? '✓ Active' : '✗ Inactive'}
                    </span>
                    <span className={`status-badge ${product.pricing_active ? 'active' : 'inactive'}`}>
                      Pricing: {product.pricing_active ? '✓ Active' : '✗ Inactive'}
                    </span>
                  </div>
                </div>

                {/* Quantity and Add to Cart */}
                {product.product_active && product.pricing_active && (
                  <div className="add-to-cart-section">
                    <div className="quantity-selector">
                      <label htmlFor="quantity">Quantity:</label>
                      <div className="quantity-input-group">
                        <button 
                          className="qty-btn"
                          onClick={handleDecrementQuantity}
                          disabled={quantity === 1}
                        >
                          −
                        </button>
                        <input
                          id="quantity"
                          type="number"
                          min="1"
                          value={quantity}
                          onChange={handleQuantityChange}
                          className="qty-input"
                        />
                        <button 
                          className="qty-btn"
                          onClick={handleIncrementQuantity}
                        >
                          +
                        </button>
                      </div>
                    </div>
                    <button 
                      className="add-to-cart-button"
                      onClick={handleAddToCart}
                    >
                      🛒 Add to Cart
                    </button>
                  </div>
                )}

                {(!product.product_active || !product.pricing_active) && (
                  <div className="unavailable-notice">
                    <p>❌ This product is currently unavailable for purchase.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="product-details-footer">
        <p>&copy; 2024 NUMRO JYOTISH. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default ProductDetails;
