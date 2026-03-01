import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import '../styles/Products.css';

function Products() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [sortBy, setSortBy] = useState('name');
  const [countryCode, setCountryCode] = useState('IN');
  const [inventories, setInventories] = useState([]);
  const [cart, setCart] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [quickViewQuantity, setQuickViewQuantity] = useState(1);

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

  // Fetch categories
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await fetch(`${API_URL}/api/product-categories`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) {
          throw new Error('Failed to fetch categories');
        }

        const data = await res.json();
        if (data.success && data.data) {
          setCategories(data.data);
        }
      } catch (err) {
        console.error('Error fetching categories:', err);
      }
    };

    fetchCategories();
  }, [API_URL]);

  // Fetch inventory data
  useEffect(() => {
    const fetchInventories = async () => {
      try {
        console.log('📦 Fetching inventories from:', `${API_URL}/api/inventory-stock`);
        const res = await fetch(`${API_URL}/api/inventory-stock`, {
          method: 'GET',
          headers: { 
            'Content-Type': 'application/json',
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
          }
        });

        if (res.ok) {
          const data = await res.json();
          const inv = data.data || [];
          console.log('✅ Inventories fetched:', inv.length, 'items');
          setInventories(inv);
        } else {
          console.error('❌ Failed to fetch inventories. Status:', res.status);
          setInventories([]);
        }
      } catch (err) {
        console.error('❌ Error fetching inventories:', err);
        setInventories([]);
      }
    };

    fetchInventories();
  }, [API_URL, authToken]);

  // Fetch products with pricing and tax information
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        setError('');

        const res = await fetch(
          `${API_URL}/api/product-details${countryCode ? `?country_code=${countryCode}` : ''}`,
          {
            method: 'GET',
            headers: { 
              'Content-Type': 'application/json',
              ...(authToken && { 'Authorization': `Bearer ${authToken}` })
            }
          }
        );

        if (!res.ok) {
          throw new Error('Failed to fetch products');
        }

        const data = await res.json();

        if (data.success && data.data) {
          console.log('Fetched products:', data.data);
          // Transform the flat structure to include pricing array for compatibility
          const transformedProducts = data.data.map(product => ({
            ...product,
            pricing: [{
              final_price: product.base_price,
              base_price: product.base_price,
              tax_percent: product.tax_percent
            }]
          }));
          console.log('Transformed products:', transformedProducts);
          setProducts(transformedProducts);
        } else {
          throw new Error(data.message || 'Invalid response format');
        }
      } catch (err) {
        console.error('Error fetching products:', err);
        setError('Failed to load products. Please try again later.');
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [API_URL, countryCode, authToken]);

  // Load cart from localStorage on mount
  useEffect(() => {
    const savedCart = localStorage.getItem('shoppingCart');
    if (savedCart) {
      try {
        setCart(JSON.parse(savedCart));
      } catch (err) {
        console.error('Error loading cart:', err);
      }
    }
  }, []);

  // Filter and search products
  useEffect(() => {
    let result = products;

    // Filter by category
    if (selectedCategory !== 'all') {
      result = result.filter(p => p.category_id === parseInt(selectedCategory));
    }

    // Filter by search term
    if (searchTerm) {
      result = result.filter(p =>
        p.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.product_description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Sort products
    switch (sortBy) {
      case 'name':
        result.sort((a, b) => a.product_name.localeCompare(b.product_name));
        break;
      case 'price-low':
        result.sort((a, b) => {
          const priceA = a.pricing?.[0]?.final_price || 0;
          const priceB = b.pricing?.[0]?.final_price || 0;
          return priceA - priceB;
        });
        break;
      case 'price-high':
        result.sort((a, b) => {
          const priceA = a.pricing?.[0]?.final_price || 0;
          const priceB = b.pricing?.[0]?.final_price || 0;
          return priceB - priceA;
        });
        break;
      case 'newest':
        result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        break;
      default:
        break;
    }

    setFilteredProducts(result);
  }, [products, selectedCategory, searchTerm, sortBy]);

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

  const handleProductClick = (product) => {
    if (!product || !product.product_id) {
      console.error('Product data is missing');
      return;
    }
    setSelectedProduct(product);
    setQuickViewQuantity(1);
  };

  const closeProductDetail = () => {
    setSelectedProduct(null);
    setQuickViewQuantity(1);
  };

  const handleAddToCart = (e, productId) => {
    e.stopPropagation();
    
    const product = products.find(p => p.product_id === productId);
    if (!product) {
      console.error('Product not found:', productId);
      return;
    }

    const quantity = selectedProduct?.product_id === productId ? quickViewQuantity : 1;
    const stockQuantity = getProductQuantity(productId);

    // Check if product is out of stock
    if (stockQuantity === 0) {
      setSuccessMessage('❌ Product is out of stock');
      setTimeout(() => setSuccessMessage(''), 3000);
      return;
    }

    // Check if quantity exceeds available stock
    if (quantity > stockQuantity) {
      setSuccessMessage(`❌ Only ${stockQuantity} item(s) available in stock`);
      setTimeout(() => setSuccessMessage(''), 3000);
      return;
    }

    // Create cart item
    const cartItem = {
      product_id: productId,
      product_name: product.product_name,
      base_price: product.pricing?.[0]?.final_price || product.base_price,
      quantity: quantity,
      image: getProductImage(product),
      tax_percent: product.pricing?.[0]?.tax_percent || 0
    };

    // Add to cart
    const updatedCart = [...cart];
    const existingItem = updatedCart.find(item => item.product_id === productId);

    if (existingItem) {
      const newQty = existingItem.quantity + quantity;
      if (newQty > stockQuantity) {
        setSuccessMessage(`❌ Only ${stockQuantity} item(s) available in stock`);
        setTimeout(() => setSuccessMessage(''), 3000);
        return;
      }
      existingItem.quantity = newQty;
      setSuccessMessage(`✓ Updated quantity to ${newQty} in cart`);
    } else {
      updatedCart.push(cartItem);
      setSuccessMessage(`✓ ${product.product_name} added to cart`);
    }

    setCart(updatedCart);
    localStorage.setItem('shoppingCart', JSON.stringify(updatedCart));
    
    setTimeout(() => setSuccessMessage(''), 3000);
    closeProductDetail();
  };

  // Buy now from Products page: replace cart with single item and go to shopping checkout
  const handleBuyNow = (e, productId) => {
    e?.stopPropagation();
    const product = products.find(p => p.product_id === productId);
    if (!product) {
      console.error('Product not found for Buy Now:', productId);
      return;
    }

    const cartItem = {
      cart_id: Date.now(),
      product_id: product.product_id,
      product_name: product.product_name,
      price: product.pricing?.[0]?.final_price || product.base_price || 0,
      quantity: selectedProduct?.product_id === productId ? quickViewQuantity : 1
    };

    const singleCart = [cartItem];
    setCart(singleCart);
    localStorage.setItem('shoppingCart', JSON.stringify(singleCart));

    // Navigate to the shopping page checkout view
    navigate('/shopping');
    // ensure shopping page shows checkout - it reads localStorage; fallback: set query param
    closeProductDetail();
  };

  const getCategoryName = (categoryId) => {
    const category = categories.find(c => c.category_id === categoryId);
    return category?.category_name || 'Uncategorized';
  };

  const getProductQuantity = (productId) => {
    const inventory = inventories.find(i => i.product_id === productId);
    if (!inventory) return 0;
    return inventory.quantity_available !== undefined ? inventory.quantity_available : inventory.quantity || 0;
  };

  const getProductImage = (product) => {
    if (product.images && product.images.length > 0) {
      const primaryImage = product.images.find(img => img.is_primary);
      // Support both old (image_url) and new (imageUrl) format
      const imageUrl = primaryImage?.imageUrl || primaryImage?.image_url || product.images[0]?.imageUrl || product.images[0]?.image_url;
      console.log('🖼️ [GET_PRODUCT_IMAGE] Retrieved image URL:', imageUrl, 'from', primaryImage ? 'primary' : 'first', 'image');
      return imageUrl;
    }
    console.warn('⚠️ [GET_PRODUCT_IMAGE] No images found for product, using placeholder');
    return 'https://via.placeholder.com/300x200?text=Product+Image';
  };

  return (
    <div className="products-container">
      <Header />
      {/* Header */}
      <header className="products-header">
        <div className="logo">
          <h1>NUMRO</h1>
          <h2>JYOTISH</h2>
        </div>
        <div className="header-actions">
          <input
            type="text"
            className="search-input"
            placeholder="Search products..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="cart-button" onClick={() => navigate('/shop')}>
            🛒 Cart <span className="badge">{cart.length}</span>
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
      <main className="products-main">
        <div className="products-content">
          {/* Sidebar with Filters */}
          <aside className="products-sidebar">
            <div className="filter-section">
              <h3>Filters</h3>

              {/* Country Selection */}
              <div className="filter-group">
                <label htmlFor="country-select">Country</label>
                <select
                  id="country-select"
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                  className="filter-select"
                >
                  <option value="IN">India (IN)</option>
                  <option value="US">United States (US)</option>
                  <option value="GB">United Kingdom (GB)</option>
                  <option value="CA">Canada (CA)</option>
                  <option value="AU">Australia (AU)</option>
                </select>
              </div>

              {/* Category Filter */}
              <div className="filter-group">
                <label>Categories</label>
                <div className="category-list">
                  <button
                    className={`category-item ${selectedCategory === 'all' ? 'active' : ''}`}
                    onClick={() => setSelectedCategory('all')}
                  >
                    All Products
                  </button>
                  {categories.map(category => (
                    <button
                      key={category.category_id}
                      className={`category-item ${selectedCategory === String(category.category_id) ? 'active' : ''}`}
                      onClick={() => setSelectedCategory(String(category.category_id))}
                    >
                      {category.category_name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sort By */}
              <div className="filter-group">
                <label htmlFor="sort-select">Sort By</label>
                <select
                  id="sort-select"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="filter-select"
                >
                  <option value="name">Name (A-Z)</option>
                  <option value="price-low">Price (Low to High)</option>
                  <option value="price-high">Price (High to Low)</option>
                  <option value="newest">Newest First</option>
                </select>
              </div>
            </div>
          </aside>

          {/* Products Grid */}
          <section className="products-section">
            {/* Loading State */}
            {loading && (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Loading products...</p>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div className="error-state">
                <p>❌ {error}</p>
              </div>
            )}

            {/* Products Grid */}
            {!loading && !error && filteredProducts.length > 0 && (
              <>
                <div className="products-info">
                  <h2>Our Products</h2>
                  <div className="products-info-actions">
                    <p className="product-count">Showing {filteredProducts.length} product(s)</p>
                    <button
                      className="add-product-btn"
                      onClick={() => navigate('/admin/productmaster')}
                    >
                      + Add Product
                    </button>
                  </div>
                </div>
                <div className="products-grid">
                  {filteredProducts.map(product => {
                    const primaryPricing = product.pricing?.[0];
                    const finalPrice = primaryPricing?.final_price || 0;
                    const basePrice = primaryPricing?.base_price || 0;
                    const taxPercent = primaryPricing?.tax_percent || 0;
                    const quantity = getProductQuantity(product.product_id);
                    const isOutOfStock = quantity === 0;

                    return (
                      <div
                        key={product.product_id}
                        className={`product-card ${isOutOfStock ? 'out-of-stock' : ''}`}
                        onClick={() => handleProductClick(product)}
                      >
                        <div className="product-image-container">
                          <img
                            src={getProductImage(product)}
                            alt={product.product_name}
                            className="product-image"
                          />
                          {isOutOfStock && (
                            <div className="product-badge out-of-stock-badge">
                              <span>Out of Stock</span>
                            </div>
                          )}
                        </div>

                        <div className="product-info">
                          <span className="product-category">
                            {getCategoryName(product.category_id)}
                          </span>
                          <h3 className="product-name">{product.product_name}</h3>
                          <p className="product-description">
                            {product.product_description || 'No description available'}
                          </p>

                          <div className="product-pricing">
                            <div className="price-section">
                              <span className="final-price">₹ {finalPrice.toLocaleString('en-IN')}</span>
                              {basePrice !== finalPrice && (
                                <span className="base-price">₹ {basePrice.toLocaleString('en-IN')}</span>
                              )}
                            </div>
                            {taxPercent > 0 && (
                              <div className="tax-info">
                                Tax: {taxPercent}%
                              </div>
                            )}
                          </div>

                          <div className="product-stock">
                            <span className={`stock-badge ${getProductQuantity(product.product_id) > 0 ? 'in-stock' : 'out-of-stock'}`}>
                              {getProductQuantity(product.product_id) > 0 
                                ? `✓ In Stock (${getProductQuantity(product.product_id)})`
                                : '✗ Out of Stock'
                              }
                            </span>
                          </div>

                          <div className="card-actions">
                            <button
                              className={`buy-now-btn ${getProductQuantity(product.product_id) === 0 ? 'disabled' : ''}`}
                              onClick={(e) => handleBuyNow(e, product.product_id)}
                              disabled={getProductQuantity(product.product_id) === 0}
                            >
                              🛒 Buy Now
                            </button>

                            <button
                              className={`add-to-cart-btn ${getProductQuantity(product.product_id) === 0 ? 'disabled' : ''}`}
                              onClick={(e) => handleAddToCart(e, product.product_id)}
                              disabled={getProductQuantity(product.product_id) === 0}
                            >
                              {getProductQuantity(product.product_id) > 0 ? '➕ Add to Cart' : '❌ Out of Stock'}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {/* Empty State */}
            {!loading && !error && filteredProducts.length === 0 && (
              <div className="empty-state">
                <p>No products found. Try adjusting your filters.</p>
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="products-footer">
        <p>&copy; 2024 NUMRO JYOTISH. All rights reserved.</p>
      </footer>

      {/* Success Message */}
      {successMessage && (
        <div className="success-toast">
          {successMessage}
        </div>
      )}

      {/* Product Detail Modal */}
      {selectedProduct && (
        <div className="product-detail-overlay" onClick={closeProductDetail}>
          <div className="product-detail-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={closeProductDetail}>✕</button>
            
            <div className="modal-content">
              <div className="modal-image">
                <img src={getProductImage(selectedProduct)} alt={selectedProduct.product_name} />
              </div>

              <div className="modal-info">
                <h2>{selectedProduct.product_name}</h2>
                <p className="modal-category">{getCategoryName(selectedProduct.category_id)}</p>

                {selectedProduct.product_description && (
                  <p className="modal-description">{selectedProduct.product_description}</p>
                )}

                <div className="modal-pricing">
                  <div className="price-row">
                    <span>Base Price:</span>
                    <span className="original-price">₹{selectedProduct.base_price}</span>
                  </div>
                  <div className="price-row">
                    <span>Final Price:</span>
                    <span className="final-price">₹{selectedProduct.pricing?.[0]?.final_price || selectedProduct.base_price}</span>
                  </div>
                  {selectedProduct.pricing?.[0]?.tax_percent > 0 && (
                    <div className="price-row">
                      <span>Tax ({selectedProduct.pricing?.[0]?.tax_percent}%):</span>
                      <span>₹{((selectedProduct.pricing?.[0]?.final_price || selectedProduct.base_price) * selectedProduct.pricing?.[0]?.tax_percent / 100).toFixed(2)}</span>
                    </div>
                  )}
                </div>

                <div className="modal-stock">
                  {getProductQuantity(selectedProduct.product_id) > 0 ? (
                    <span className="in-stock">✓ In Stock ({getProductQuantity(selectedProduct.product_id)})</span>
                  ) : (
                    <span className="out-of-stock">✗ Out of Stock</span>
                  )}
                </div>

                <div className="modal-actions">
                  <div className="qty-selector">
                    <label>Quantity:</label>
                    <div className="qty-controls">
                      <button 
                        onClick={() => setQuickViewQuantity(Math.max(1, quickViewQuantity - 1))}
                        disabled={quickViewQuantity === 1}
                      >
                        −
                      </button>
                      <input 
                        type="number" 
                        min="1" 
                        max={getProductQuantity(selectedProduct.product_id)} 
                        value={quickViewQuantity}
                        onChange={(e) => setQuickViewQuantity(Math.min(getProductQuantity(selectedProduct.product_id), Math.max(1, parseInt(e.target.value))))}
                      />
                      <button 
                        onClick={() => setQuickViewQuantity(Math.min(getProductQuantity(selectedProduct.product_id), quickViewQuantity + 1))}
                        disabled={quickViewQuantity >= getProductQuantity(selectedProduct.product_id)}
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <button 
                    className="modal-add-to-cart-btn"
                    onClick={(e) => handleAddToCart(e, selectedProduct.product_id)}
                    disabled={getProductQuantity(selectedProduct.product_id) === 0}
                  >
                    🛒 Add to Cart
                  </button>
                  <button
                    className="modal-buy-now-btn"
                    onClick={(e) => handleBuyNow(e, selectedProduct.product_id)}
                    disabled={getProductQuantity(selectedProduct.product_id) === 0}
                    style={{ marginLeft: '8px' }}
                  >
                    🛒 Buy Now
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Products;
