import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/Shopping.css';

function Shopping() {
  const navigate = useNavigate();
  const [activeView, setActiveView] = useState('catalog'); // 'catalog', 'cart', 'checkout', 'confirmation'
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Auth
  const userEmail = localStorage.getItem('email') || 'Guest';
  const userId = localStorage.getItem('userId');
  console.info('Login successful:', userId);

  const userInitials = userEmail.charAt(0).toUpperCase();
  const authToken = localStorage.getItem('authToken');

  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Product and Cart State
  const [products, setProducts] = useState([]);
  const [productPricing, setProductPricing] = useState({});
  const [cart, setCart] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [lastOrder, setLastOrder] = useState(null);
  const [userDetails, setUserDetails] = useState(null);
  const [savedAddresses, setSavedAddresses] = useState([]);

  // Checkout Form
  const [checkoutForm, setCheckoutForm] = useState({
    customer_name: userEmail.split('@')[0] || '',
    customer_email: userEmail || '',
    customer_phone: '',
    delivery_address: '',
    city: '',
    postal_code: '',
    payment_method: 'card', // 'card', 'upi', 'bank'
    address_id: null // Selected saved address ID
  });

  // Load products, cart, and user details on mount
  useEffect(() => {
    console.log('🎬 Shopping page mounted, loading products...');
    fetchProducts();
    loadCart();
    if (userId) {
      fetchUserDetails(userId);
    }
  }, [API_URL, authToken, userId]);

  const fetchProducts = async () => {
    try {
      console.log('📦 Fetching products from:', `${API_URL}/api/products`);
      const res = await fetch(`${API_URL}/api/products`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        const prods = data.data || [];
        console.log('✅ Products fetched:', prods.length);
        setProducts(prods);
        
        // Fetch pricing for all products
        await fetchProductPricing();
      } else {
        setError('Failed to load products');
      }
    } catch (err) {
      console.error('❌ Error fetching products:', err);
      setError('Error loading products');
    }
  };

  const fetchProductPricing = async () => {
    try {
      const res = await fetch(`${API_URL}/api/product-pricing`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        const pricings = data.data || [];
        // Build a map of product_id -> base_price (prioritize India/default prices)
        const pricingMap = {};
        pricings.forEach(pricing => {
          const key = pricing.product_id;
          if (!pricingMap[key] || pricing.country_code === 'IN') {
            pricingMap[key] = pricing.base_price || 0;
          }
        });
        setProductPricing(pricingMap);
        console.log('✅ Product pricing fetched:', Object.keys(pricingMap).length);
      }
    } catch (err) {
      console.error('❌ Error fetching pricing:', err);
      // Don't fail if pricing fails, use fallback
    }
  };

  const loadCart = () => {
    try {
      const saved = localStorage.getItem('shoppingCart');
      const cartData = saved ? JSON.parse(saved) : [];
      console.log('📦 Loaded cart:', cartData.length, 'items');
      setCart(cartData);
    } catch (err) {
      console.error('Error loading cart:', err);
      setCart([]);
    }
  };

  const saveCart = (cartData) => {
    try {
      localStorage.setItem('shoppingCart', JSON.stringify(cartData));
    } catch (err) {
      console.error('Error saving cart:', err);
    }
  };

  const fetchUserDetails = async (uid) => {
    try {
      console.log('👤 Fetching user details for user:', uid);
      const res = await fetch(`${API_URL}/api/users/${uid}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        const data = await res.json();
        console.log('✅ User details fetched:', data.data);

        setUserDetails(data.data.user);
        setSavedAddresses(data.data.all_addresses || []);

        // Pre-fill checkout form with default address if available
        if (data.data.default_address) {
          const addr = data.data.default_address;
          setCheckoutForm(prev => ({
            ...prev,
            customer_name: addr.full_name || prev.customer_name,
            customer_phone: addr.phone || prev.customer_phone,
            delivery_address: addr.street_address || prev.delivery_address,
            city: addr.city || prev.city,
            postal_code: addr.postal_code || prev.postal_code,
            address_id: addr.address_id
          }));
        }
      } else {
        console.warn('Failed to fetch user details');
      }
    } catch (err) {
      console.error('❌ Error fetching user details:', err);
    }
  };

  const handleSaveAddress = async () => {
    if (!userId) {
      setError('User not authenticated');
      return;
    }

    try {
      setLoading(true);
      const addressPayload = {
        address_type: 'home',
        address_line1: checkoutForm.delivery_address,
        address_line2: '',
        city: checkoutForm.city,
        state: '',
        postal_code: checkoutForm.postal_code,
        country_code: 'IN',
        is_default: true
      };

      const res = await fetch(`${API_URL}/api/users/${userId}/addresses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(addressPayload)
      });

      if (res.ok) {
        const data = await res.json();
        setSuccessMessage('Address saved successfully!');
        setSavedAddresses([...savedAddresses, data.data]);
        setCheckoutForm(prev => ({ ...prev, address_id: data.data.address_id }));
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setError('Failed to save address');
      }
    } catch (err) {
      console.error('Error saving address:', err);
      setError('Error saving address');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSavedAddress = (address) => {
    const selectedName = address.full_name || checkoutForm.customer_name;
    setCheckoutForm(prev => ({
      ...prev,
      customer_name: selectedName,
      customer_phone: address.phone || prev.customer_phone,
      delivery_address: address.address_line1 || address.street_address || prev.delivery_address,
      city: address.city || prev.city,
      postal_code: address.postal_code || prev.postal_code,
      address_id: address.address_id
    }));
    setSuccessMessage(`✓ Address "${selectedName}" selected`);
    setTimeout(() => setSuccessMessage(''), 2000);
  };

  const handleAddToCart = (product) => {
    console.log('➕ Adding to cart:', product.product_name);
    const existingItem = cart.find(item => item.product_id === product.product_id);
    
    let updatedCart;
    if (existingItem) {
      updatedCart = cart.map(item =>
        item.product_id === product.product_id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      );
      setSuccessMessage(`Updated quantity: ${product.product_name}`);
    } else {
      const cartItem = {
        cart_id: Date.now(),
        product_id: product.product_id,
        product_name: product.product_name,
        price: getProductPricing(product.product_id),
        quantity: 1
      };
      updatedCart = [...cart, cartItem];
      setSuccessMessage(`Added: ${product.product_name}`);
    }
    
    setCart(updatedCart);
    saveCart(updatedCart);
    setTimeout(() => setSuccessMessage(''), 2000);
  };

  // Buy Now: place single product into cart and go to checkout
  const handleBuyNow = (product, quantity = 1) => {
    if (!product) return;
    const cartItem = {
      cart_id: Date.now(),
      product_id: product.product_id,
      product_name: product.product_name,
      price: getProductPricing(product.product_id),
      quantity: quantity
    };

    const singleCart = [cartItem];
    setCart(singleCart);
    saveCart(singleCart);
    // prefill checkout form with user email
    setCheckoutForm({
      ...checkoutForm,
      customer_name: userEmail.split('@')[0] || '',
      customer_email: userEmail || ''
    });
    // navigate directly to checkout view
    setSelectedProduct(product);
    setActiveView('checkout');
  };

  const handleUpdateQuantity = (cartId, quantity) => {
    if (quantity <= 0) {
      handleRemoveFromCart(cartId);
      return;
    }
    
    const updatedCart = cart.map(item =>
      item.cart_id === cartId
        ? { ...item, quantity }
        : item
    );
    setCart(updatedCart);
    saveCart(updatedCart);
    console.log('📝 Updated quantity for cart item:', cartId, 'to', quantity);
  };

  const handleRemoveFromCart = (cartId) => {
    const item = cart.find(i => i.cart_id === cartId);
    const updatedCart = cart.filter(item => item.cart_id !== cartId);
    setCart(updatedCart);
    saveCart(updatedCart);
    setSuccessMessage(`Removed: ${item?.product_name}`);
    setTimeout(() => setSuccessMessage(''), 2000);
    console.log('🗑️ Removed from cart:', cartId);
  };

  const handleCheckoutSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (cart.length === 0) {
        setError('Cart is empty');
        setLoading(false);
        return;
      }

      // Validate form
      if (!checkoutForm.customer_name || !checkoutForm.customer_email || !checkoutForm.delivery_address) {
        setError('Please fill in all required fields');
        setLoading(false);
        return;
      }

      const userId = localStorage.getItem('userId');
      if (!userId) {
        setError('User not authenticated');
        setLoading(false);
        return;
      }

      // Prepare order items for backend
      const orderItems = cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.price,
        discount: item.discount || 0,
        tax_percent: item.tax_percent || 0,
        tax_amount: (item.price * item.quantity * (item.tax_percent || 0)) / 100,
        total_amount: item.price * item.quantity + ((item.price * item.quantity * (item.tax_percent || 0)) / 100)
      }));

      // Create order payload for backend
      const orderPayload = {
        user_id: parseInt(userId),
        country_code: 'IN', // Can be made dynamic based on user selection
        items: orderItems,
        subtotal: calculateSubtotal(),
        discount: 0,
        taxable_amount: calculateSubtotal(),
        total_tax: calculateTax(),
        total_amount: calculateTotal()
      };

      console.log('📤 Sending order to backend:', orderPayload);

      // Send order to backend
      const response = await fetch(`${API_URL}/api/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(orderPayload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create order');
      }

      const orderData = await response.json();
      console.log('✅ Order created successfully:', orderData);

      // Also save to localStorage as backup
      const backupOrder = {
        order_id: orderData.data.order_id,
        customer_name: checkoutForm.customer_name,
        customer_email: checkoutForm.customer_email,
        customer_phone: checkoutForm.customer_phone,
        delivery_address: checkoutForm.delivery_address,
        city: checkoutForm.city,
        postal_code: checkoutForm.postal_code,
        payment_method: checkoutForm.payment_method,
        order_items: cart,
        order_date: new Date().toISOString(),
        total_amount: calculateTotal(),
        status: 'CREATED'
      };

      const orders = JSON.parse(localStorage.getItem('orders') || '[]');
      orders.push(backupOrder);
      localStorage.setItem('orders', JSON.stringify(orders));

      // Clear cart
      setCart([]);
      saveCart([]);

      // Set confirmation details with backend response
      setLastOrder({
        ...backupOrder,
        order_id: orderData.data.order_id,
        invoice_number: orderData.data.invoice_number,
        invoice_id: orderData.data.invoice_id,
        created_at: orderData.data.created_at
      });
      setActiveView('confirmation');
      setSuccessMessage('Order confirmed successfully!');

      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('❌ Error processing order:', err);
      setError(err.message || 'Failed to process order');
    } finally {
      setLoading(false);
    }
  };

  const calculateSubtotal = () => {
    return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  };

  const calculateTax = () => {
    return calculateSubtotal() * 0.18; // 18% GST
  };

  const calculateTotal = () => {
    return calculateSubtotal() + calculateTax();
  };

  const getProductPricing = (productId) => {
    // Return price from productPricing map, fallback to 0
    return productPricing[productId] || 0;
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    navigate('/login');
  };

  const handleContinueShopping = () => {
    setActiveView('catalog');
    setSelectedProduct(null);
    // Reset checkout form to fresh state with only basic user info
    setCheckoutForm({
      customer_name: userEmail.split('@')[0] || '',
      customer_email: userEmail || '',
      customer_phone: '',
      delivery_address: '',
      city: '',
      postal_code: '',
      payment_method: 'card',
      address_id: null
    });
  };

  return (
    <div className="shopping-container">
      <Header />
      {/* Header */}
      <header className="shopping-header">
        <div className="header-left">
          <div className="logo">
            <h1>NUMRO JYOTISH</h1>
          </div>
        </div>
        <h2 className="page-title">Online Store</h2>
        <div className="header-right">
          <button className="cart-button" onClick={() => setActiveView('cart')}>
            🛒 Cart ({cart.length})
          </button>
          <button
            className="user-button"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            {userInitials} ▼
          </button>
          {showUserMenu && (
            <div className="user-dropdown">
              <div className="dropdown-header">{userEmail}</div>
              {authToken && (
                <>
                  <button className="dropdown-item" onClick={() => navigate('/dashboard')}>
                    📊 Dashboard
                  </button>
                  <div className="dropdown-divider"></div>
                  <button className="dropdown-item logout" onClick={handleLogout}>
                    🚪 Logout
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="shopping-main">
        {/* Alerts */}
        {successMessage && (
          <div className="alert alert-success">
            ✅ {successMessage}
          </div>
        )}
        {error && (
          <div className="alert alert-error">
            ❌ {error}
          </div>
        )}

        {/* Catalog View */}
        {activeView === 'catalog' && !selectedProduct && (
          <section className="catalog-section">
            <h2>Our Products</h2>
            <div className="products-grid">
              {products.map(product => (
                <div key={product.product_id} className="product-card">
                  <div className="product-image-placeholder">
                    <span>📦 {product.product_name.substring(0, 1)}</span>
                  </div>
                  <div className="product-info">
                    <h3>{product.product_name}</h3>
                    <p className="product-desc">{product.product_description || 'Quality product'}</p>
                    <div className="product-price">₹{getProductPricing(product.product_id)}</div>
                    <div className="product-actions">
                      <button
                        className="btn-view"
                        onClick={() => setSelectedProduct(product)}
                      >
                        👁️ View Details
                      </button>
                      <button
                        className="btn-buy-now"
                        onClick={() => handleBuyNow(product)}
                      >
                        🛒 Buy Now
                      </button>
                      <button
                        className="btn-add-cart"
                        onClick={() => handleAddToCart(product)}
                      >
                        ➕ Add to Cart
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {products.length === 0 && (
              <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                <p>No products available at the moment.</p>
              </div>
            )}
          </section>
        )}

        {/* Product Details View */}
        {activeView === 'catalog' && selectedProduct && (
          <section className="product-details-section">
            <button className="btn-back" onClick={() => setSelectedProduct(null)}>
              ← Back to Products
            </button>
            
            <div className="product-details-container">
              <div className="details-image">
                <div className="image-placeholder">
                  <span>📦 {selectedProduct.product_name.substring(0, 1)}</span>
                </div>
              </div>

              <div className="details-content">
                <h2>{selectedProduct.product_name}</h2>
                <div className="details-price">₹{getProductPricing(selectedProduct.product_id)}</div>
                <p className="details-description">{selectedProduct.product_description}</p>

                <div className="details-info">
                  <div className="info-row">
                    <span className="label">Product ID:</span>
                    <span>{selectedProduct.product_id}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Status:</span>
                    <span>{selectedProduct.is_active ? '✓ In Stock' : '✗ Out of Stock'}</span>
                  </div>
                </div>

                <div className="details-actions">
                  <button
                    className="btn-primary"
                    onClick={() => handleAddToCart(selectedProduct)}
                  >
                    ➕ Add to Cart
                  </button>
                  <button
                    className="btn-buy-now"
                    onClick={() => handleBuyNow(selectedProduct)}
                  >
                    🛒 Buy Now
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => setSelectedProduct(null)}
                  >
                    Continue Shopping
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Cart View */}
        {activeView === 'cart' && (
          <section className="cart-section">
            <h2>Shopping Cart</h2>

            {cart.length > 0 ? (
              <>
                <div className="cart-items">
                  <table className="cart-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Quantity</th>
                        <th>Subtotal</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cart.map(item => (
                        <tr key={item.cart_id}>
                          <td>{item.product_name}</td>
                          <td>₹{item.price.toFixed(2)}</td>
                          <td>
                            <div className="quantity-input">
                              <button onClick={() => handleUpdateQuantity(item.cart_id, item.quantity - 1)}>−</button>
                              <input
                                type="number"
                                min="1"
                                value={item.quantity}
                                onChange={(e) => handleUpdateQuantity(item.cart_id, parseInt(e.target.value) || 1)}
                              />
                              <button onClick={() => handleUpdateQuantity(item.cart_id, item.quantity + 1)}>+</button>
                            </div>
                          </td>
                          <td>₹{(item.price * item.quantity).toFixed(2)}</td>
                          <td>
                            <button
                              className="btn-remove"
                              onClick={() => handleRemoveFromCart(item.cart_id)}
                            >
                              🗑️ Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="cart-summary">
                  <div className="summary-row">
                    <span>Subtotal:</span>
                    <span>₹{calculateSubtotal().toFixed(2)}</span>
                  </div>
                  <div className="summary-row">
                    <span>Tax (18% GST):</span>
                    <span>₹{calculateTax().toFixed(2)}</span>
                  </div>
                  <div className="summary-row total">
                    <span>Total:</span>
                    <span>₹{calculateTotal().toFixed(2)}</span>
                  </div>

                  <div className="cart-actions">
                    <button
                      className="btn-primary"
                      onClick={() => setActiveView('checkout')}
                    >
                      💳 Proceed to Checkout
                    </button>
                    <button
                      className="btn-secondary"
                      onClick={() => setActiveView('catalog')}
                    >
                      🛒 Continue Shopping
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px' }}>
                <p style={{ fontSize: '18px', color: '#999', marginBottom: '20px' }}>
                  Your cart is empty
                </p>
                <button
                  className="btn-primary"
                  onClick={() => setActiveView('catalog')}
                >
                  🛍️ Start Shopping
                </button>
              </div>
            )}
          </section>
        )}

        {/* Checkout View */}
        {activeView === 'checkout' && (
          <section className="checkout-section">
            <h2>Checkout</h2>

            <div className="checkout-container">
              <div className="checkout-form-wrapper">
                <form onSubmit={handleCheckoutSubmit} className="checkout-form">
                  <h3>Delivery Information</h3>

                  {savedAddresses.length > 0 && (
                    <div className="saved-addresses">
                      <label>📍 Saved Addresses</label>
                      <div className="address-selector">
                        {savedAddresses.map(addr => (
                          <button
                            key={addr.address_id}
                            type="button"
                            className={`address-btn ${checkoutForm.address_id === addr.address_id ? 'selected' : ''}`}
                            onClick={() => handleSelectSavedAddress(addr)}
                          >
                            <div className="address-item">
                              <strong>{addr.full_name}</strong>
                              <p>{addr.street_address}, {addr.city} - {addr.postal_code}</p>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="form-row">
                    <div className="form-group">
                      <label>Full Name *</label>
                      <input
                        type="text"
                        required
                        value={checkoutForm.customer_name}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, customer_name: e.target.value })}
                        placeholder="Your name"
                      />
                    </div>

                    <div className="form-group">
                      <label>Email *</label>
                      <input
                        type="email"
                        required
                        value={checkoutForm.customer_email}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, customer_email: e.target.value })}
                        placeholder="your@email.com"
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Phone Number</label>
                    <input
                      type="tel"
                      value={checkoutForm.customer_phone}
                      onChange={(e) => setCheckoutForm({ ...checkoutForm, customer_phone: e.target.value })}
                      placeholder="+91 9999999999"
                    />
                  </div>

                  <div className="form-group">
                    <label>Delivery Address *</label>
                    <textarea
                      required
                      value={checkoutForm.delivery_address}
                      onChange={(e) => setCheckoutForm({ ...checkoutForm, delivery_address: e.target.value })}
                      placeholder="Street address"
                      rows="3"
                    ></textarea>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>City *</label>
                      <input
                        type="text"
                        required
                        value={checkoutForm.city}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, city: e.target.value })}
                        placeholder="City"
                      />
                    </div>

                    <div className="form-group">
                      <label>Postal Code</label>
                      <input
                        type="text"
                        value={checkoutForm.postal_code}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, postal_code: e.target.value })}
                        placeholder="400001"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-save-address"
                    onClick={handleSaveAddress}
                    disabled={!checkoutForm.customer_name || !checkoutForm.delivery_address || !checkoutForm.city}
                  >
                    💾 Save This Address for Next Time
                  </button>

                  <h3 style={{ marginTop: '30px' }}>Payment Method</h3>

                  <div className="form-group">
                    <div className="radio-group">
                      <label>
                        <input
                          type="radio"
                          value="card"
                          checked={checkoutForm.payment_method === 'card'}
                          onChange={(e) => setCheckoutForm({ ...checkoutForm, payment_method: e.target.value })}
                        />
                        💳 Credit/Debit Card
                      </label>
                    </div>
                    <div className="radio-group">
                      <label>
                        <input
                          type="radio"
                          value="upi"
                          checked={checkoutForm.payment_method === 'upi'}
                          onChange={(e) => setCheckoutForm({ ...checkoutForm, payment_method: e.target.value })}
                        />
                        📱 UPI
                      </label>
                    </div>
                    <div className="radio-group">
                      <label>
                        <input
                          type="radio"
                          value="bank"
                          checked={checkoutForm.payment_method === 'bank'}
                          onChange={(e) => setCheckoutForm({ ...checkoutForm, payment_method: e.target.value })}
                        />
                        🏦 Bank Transfer
                      </label>
                    </div>
                  </div>

                  <div className="form-actions" style={{ marginTop: '30px' }}>
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Processing...' : '✅ Confirm Order'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setActiveView('cart')}
                    >
                      ← Back to Cart
                    </button>
                  </div>
                </form>
              </div>

              <div className="checkout-summary">
                <h3>Order Summary</h3>
                <div className="summary-items">
                  {cart.map(item => (
                    <div key={item.cart_id} className="summary-item">
                      <span>{item.product_name} × {item.quantity}</span>
                      <span>₹{(item.price * item.quantity).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
                <div className="summary-divider"></div>
                <div className="summary-row subtotal">
                  <span>Subtotal:</span>
                  <span>₹{calculateSubtotal().toFixed(2)}</span>
                </div>
                <div className="summary-row tax">
                  <span>Tax (18%):</span>
                  <span>₹{calculateTax().toFixed(2)}</span>
                </div>
                <div className="summary-row total">
                  <span>Total:</span>
                  <span>₹{calculateTotal().toFixed(2)}</span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Order Confirmation View */}
        {activeView === 'confirmation' && lastOrder && (
          <section className="confirmation-section">
            <div className="confirmation-card">
              <div className="confirmation-header">
                <div className="check-icon">✓</div>
                <h2>Order Confirmed!</h2>
                <p>Your order has been placed successfully</p>
                <p className="confirmation-time">Placed on {lastOrder?.order_date ? new Date(lastOrder.order_date).toLocaleString('en-IN') : 'Just now'}</p>
              </div>

              <div className="confirmation-details">
                <div className="order-number">
                  <span className="label">Order ID:</span>
                  <span className="value">{lastOrder.order_id}</span>
                </div>

                {lastOrder.invoice_number && (
                  <div className="invoice-number">
                    <span className="label">Invoice #:</span>
                    <span className="value">{lastOrder.invoice_number}</span>
                  </div>
                )}

                {lastOrder.status && (
                  <div className="order-status" style={{ marginTop: '12px', padding: '12px', backgroundColor: '#f0fff4', borderLeft: '4px solid #48bb78', borderRadius: '6px' }}>
                    <span className="label" style={{ color: '#333' }}>Status:</span>
                    <span className="value" style={{ color: '#48bb78', fontWeight: '600' }}>🔄 {lastOrder.status}</span>
                  </div>
                )}

                <div className="order-info">
                  <div className="info-section">
                    <h4>Customer Details</h4>
                    <div className="info-row">
                      <span>Name:</span>
                      <span>{lastOrder.customer_name}</span>
                    </div>
                    <div className="info-row">
                      <span>Email:</span>
                      <span>{lastOrder.customer_email}</span>
                    </div>
                    {lastOrder.customer_phone && (
                      <div className="info-row">
                        <span>Phone:</span>
                        <span>{lastOrder.customer_phone}</span>
                      </div>
                    )}
                  </div>

                  <div className="info-section">
                    <h4>Delivery Address</h4>
                    <div className="address">
                      {lastOrder.delivery_address}
                      {lastOrder.city && `, ${lastOrder.city}`}
                      {lastOrder.postal_code && ` - ${lastOrder.postal_code}`}
                    </div>
                  </div>

                  <div className="info-section">
                    <h4>Order Items</h4>
                    <div className="items-list">
                      {lastOrder.order_items.map(item => (
                        <div key={item.cart_id} className="item-row">
                          <span>{item.product_name} × {item.quantity}</span>
                          <span>₹{(item.price * item.quantity).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="info-section">
                    <h4>Payment Method</h4>
                    <div className="payment-method">
                      {lastOrder.payment_method === 'card' && '💳 Credit/Debit Card'}
                      {lastOrder.payment_method === 'upi' && '📱 UPI'}
                      {lastOrder.payment_method === 'bank' && '🏦 Bank Transfer'}
                    </div>
                  </div>

                  <div className="info-section total-section">
                    <div className="total-amount">
                      <span>Total Amount:</span>
                      <span>₹{lastOrder.total_amount.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="confirmation-actions">
                <button
                  className="btn-primary"
                  onClick={handleContinueShopping}
                >
                  🛍️ Continue Shopping
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => navigate('/dashboard')}
                >
                  📊 Go to Dashboard
                </button>
              </div>

              <p className="confirmation-note">
                A confirmation email will be sent to {lastOrder.customer_email}
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default Shopping;
