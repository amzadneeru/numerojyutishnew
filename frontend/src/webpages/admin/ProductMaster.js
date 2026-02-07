import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../../styles/ProductMaster.css';

function ProductMaster() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('products');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  // Auth
  const userEmail = localStorage.getItem('email') || 'User';
  const userInitials = userEmail.charAt(0).toUpperCase();
  const authToken = localStorage.getItem('authToken');

  const API_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');

  // Category Management State
  const [categories, setCategories] = useState([]);
  const [categoryForm, setCategoryForm] = useState({
    category_id: null,
    category_name: '',
    category_description: '',
    is_active: true
  });
  const [editingCategory, setEditingCategory] = useState(null);

  // Product Management State
  const [products, setProducts] = useState([]);
  const [productForm, setProductForm] = useState({
    product_id: null,
    category_id: '',
    product_name: '',
    product_description: '',
    is_active: true
  });
  const [editingProduct, setEditingProduct] = useState(null);

  // Product Images Management State
  const [productImages, setProductImages] = useState([]);
  const [imageForm, setImageForm] = useState({
    image_id: null,
    product_id: '',
    image_url: '',
    is_primary: false
  });
  const [editingImage, setEditingImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);

  const handleImageUrlChange = (e) => {
    const url = e.target.value;
    setImageForm({ ...imageForm, image_url: url });
    setImagePreview(url);
  };

  const handleImageFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError('Please select a valid image file');
        return;
      }
      // Validate file size (max 5MB)
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        setError('Image file size must be less than 5MB');
        return;
      }
      setImageFile(file);
      const preview = URL.createObjectURL(file);
      setImagePreview(preview);
      setError('');
    }
  };

  const uploadImageFile = async (productId) => {
    if (!imageFile) return null;

    try {
      setUploadingImage(true);
      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('product_id', productId);

      const res = await fetch(`${API_URL}/api/upload-product-image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        body: formData
      });

      if (!res.ok) {
        throw new Error('Failed to upload image');
      }

      const data = await res.json();
      return data.data?.image_url || null;
    } catch (err) {
      console.error('Image upload error:', err);
      throw err;
    } finally {
      setUploadingImage(false);
    }
  };

  // Pricing Management State
  const [pricings, setPricings] = useState([]);
  const [countries, setCountries] = useState([
    { code: 'IN', name: 'India' },
    { code: 'US', name: 'United States' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'CA', name: 'Canada' },
    { code: 'AU', name: 'Australia' }
  ]);
  const [pricingForm, setPricingForm] = useState({
    pricing_id: null,
    product_id: '',
    country_code: 'IN',
    currency_code: 'INR',
    base_price: '',
    discount_percent: 0,
    is_tax_inclusive: false,
    is_active: true
  });
  const [editingPricing, setEditingPricing] = useState(null);

  // Tax Management State
  const [taxes, setTaxes] = useState([]);
  const [taxForm, setTaxForm] = useState({
    tax_id: null,
    country_code: 'IN',
    state_code: '',
    tax_name: '',
    tax_percent: '',
    is_active: true,
    effective_from: '',
    effective_to: ''
  });
  const [editingTax, setEditingTax] = useState(null);

  // Fetch all data on component mount
  useEffect(() => {
    fetchCategories();
    fetchProducts();
    fetchPricings();
    fetchTaxes();
    fetchProductImages();
  }, [API_URL, authToken]);

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_URL}/api/product-categories`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/products`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProducts(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching products:', err);
    }
  };

  const fetchPricings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/product-pricing`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPricings(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching pricings:', err);
    }
  };

  const fetchTaxes = async () => {
    try {
      const res = await fetch(`${API_URL}/api/tax-master`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTaxes(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching taxes:', err);
    }
  };

  const fetchProductImages = async () => {
    try {
      const res = await fetch(`${API_URL}/api/product-images`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProductImages(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching product images:', err);
    }
  };

  // Category handlers
  const handleCategorySubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const method = editingCategory ? 'PUT' : 'POST';
      const url = editingCategory
        ? `${API_URL}/api/product-categories/${categoryForm.category_id}`
        : `${API_URL}/api/product-categories`;

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(categoryForm)
      });

      if (!res.ok) throw new Error('Failed to save category');

      setSuccessMessage(`Category ${editingCategory ? 'updated' : 'created'} successfully!`);
      setCategoryForm({ category_id: null, category_name: '', category_description: '', is_active: true });
      setEditingCategory(null);
      fetchCategories();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditCategory = (category) => {
    setCategoryForm(category);
    setEditingCategory(category.category_id);
  };

  const handleCancelEditCategory = () => {
    setCategoryForm({ category_id: null, category_name: '', category_description: '', is_active: true });
    setEditingCategory(null);
  };

  // Product handlers
  const handleProductSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const method = editingProduct ? 'PUT' : 'POST';
      const url = editingProduct
        ? `${API_URL}/api/products/${productForm.product_id}`
        : `${API_URL}/api/products`;

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(productForm)
      });

      if (!res.ok) throw new Error('Failed to save product');

      setSuccessMessage(`Product ${editingProduct ? 'updated' : 'created'} successfully!`);
      setProductForm({
        product_id: null,
        category_id: '',
        product_name: '',
        product_description: '',
        is_active: true
      });
      setEditingProduct(null);
      fetchProducts();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditProduct = (product) => {
    setProductForm(product);
    setEditingProduct(product.product_id);
  };

  const handleCancelEditProduct = () => {
    setProductForm({
      product_id: null,
      category_id: '',
      product_name: '',
      product_description: '',
      is_active: true
    });
    setEditingProduct(null);
  };

  // Pricing handlers
  const handlePricingSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const method = editingPricing ? 'PUT' : 'POST';
      const url = editingPricing
        ? `${API_URL}/api/product-pricing/${pricingForm.pricing_id}`
        : `${API_URL}/api/product-pricing`;

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(pricingForm)
      });

      if (!res.ok) throw new Error('Failed to save pricing');

      setSuccessMessage(`Pricing ${editingPricing ? 'updated' : 'created'} successfully!`);
      setPricingForm({
        pricing_id: null,
        product_id: '',
        country_code: 'IN',
        currency_code: 'INR',
        base_price: '',
        discount_percent: 0,
        is_tax_inclusive: false,
        is_active: true
      });
      setEditingPricing(null);
      fetchPricings();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditPricing = (pricing) => {
    setPricingForm(pricing);
    setEditingPricing(pricing.pricing_id);
  };

  const handleCancelEditPricing = () => {
    setPricingForm({
      pricing_id: null,
      product_id: '',
      country_code: 'IN',
      currency_code: 'INR',
      base_price: '',
      discount_percent: 0,
      is_tax_inclusive: false,
      is_active: true
    });
    setEditingPricing(null);
  };

  // Tax handlers
  const handleTaxSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const method = editingTax ? 'PUT' : 'POST';
      const url = editingTax
        ? `${API_URL}/api/tax-master/${taxForm.tax_id}`
        : `${API_URL}/api/tax-master`;

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(taxForm)
      });

      if (!res.ok) throw new Error('Failed to save tax');

      setSuccessMessage(`Tax ${editingTax ? 'updated' : 'created'} successfully!`);
      setTaxForm({
        tax_id: null,
        country_code: 'IN',
        state_code: '',
        tax_name: '',
        tax_percent: '',
        is_active: true,
        effective_from: '',
        effective_to: ''
      });
      setEditingTax(null);
      fetchTaxes();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditTax = (tax) => {
    setTaxForm(tax);
    setEditingTax(tax.tax_id);
  };

  const handleCancelEditTax = () => {
    setTaxForm({
      tax_id: null,
      country_code: 'IN',
      state_code: '',
      tax_name: '',
      tax_percent: '',
      is_active: true,
      effective_from: '',
      effective_to: ''
    });
    setEditingTax(null);
  };

  // Image handlers
  const handleImageSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      if (!imageForm.product_id) {
        setError('Product is required');
        setLoading(false);
        return;
      }

      let imageUrl = imageForm.image_url;

      // If a file is selected, upload it first
      if (imageFile && !editingImage) {
        imageUrl = await uploadImageFile(imageForm.product_id);
        if (!imageUrl) {
          setError('Failed to upload image file');
          setLoading(false);
          return;
        }
      } else if (!imageUrl && !imageFile) {
        setError('Please provide an image URL or upload an image file');
        setLoading(false);
        return;
      }

      const method = editingImage ? 'PUT' : 'POST';
      const url = editingImage
        ? `${API_URL}/api/product-images/${imageForm.image_id}`
        : `${API_URL}/api/product-images`;

      const payload = {
        product_id: imageForm.product_id,
        image_url: imageUrl,
        is_primary: imageForm.is_primary
      };

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to save image');

      setSuccessMessage(`Image ${editingImage ? 'updated' : 'created'} successfully!`);
      setImageForm({
        image_id: null,
        product_id: '',
        image_url: '',
        is_primary: false
      });
      setImageFile(null);
      setImagePreview(null);
      setEditingImage(null);
      fetchProductImages();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditImage = (image) => {
    setImageForm(image);
    setImagePreview(image.image_url);
    setEditingImage(image.image_id);
  };

  const handleDeleteImage = async (imageId) => {
    if (!window.confirm('Are you sure you want to delete this image?')) return;

    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${API_URL}/api/product-images/${imageId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (!res.ok) throw new Error('Failed to delete image');

      setSuccessMessage('Image deleted successfully!');
      fetchProductImages();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelEditImage = () => {
    setImageForm({
      image_id: null,
      product_id: '',
      image_url: '',
      is_primary: false
    });
    setImageFile(null);
    setImagePreview(null);
    setEditingImage(null);
    setError('');
  };

  const clearImageFile = () => {
    setImageFile(null);
    if (imagePreview && imagePreview.startsWith('blob:')) {
      URL.revokeObjectURL(imagePreview);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('email');
    navigate('/login');
  };

  const getCategoryName = (categoryId) => {
    const category = categories.find(c => c.category_id === categoryId);
    return category?.category_name || 'N/A';
  };

  const getProductName = (productId) => {
    const product = products.find(p => p.product_id === productId);
    return product?.product_name || 'N/A';
  };

  const getCountryName = (countryCode) => {
    const country = countries.find(c => c.code === countryCode);
    return country?.name || countryCode;
  };

  return (
    <div className="product-master-container">
      {/* Header */}
      <header className="master-header">
        <div className="logo">
          <h1>NUMRO</h1>
          <h2>JYOTISH</h2>
        </div>
        <h3 className="page-title">Product Master</h3>
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
              <button className="dropdown-item" onClick={() => navigate('/dashboard')}>
                📊 Dashboard
              </button>
              <div className="dropdown-divider"></div>
              <button className="dropdown-item logout" onClick={handleLogout}>
                🚪 Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="master-main">
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

        {/* Tabs Navigation */}
        <div className="tabs-navigation">
          <button
            className={`tab-btn ${activeTab === 'products' ? 'active' : ''}`}
            onClick={() => setActiveTab('products')}
          >
            📦 Products
          </button>
          <button
            className={`tab-btn ${activeTab === 'categories' ? 'active' : ''}`}
            onClick={() => setActiveTab('categories')}
          >
            📂 Categories
          </button>
          <button
            className={`tab-btn ${activeTab === 'pricing' ? 'active' : ''}`}
            onClick={() => setActiveTab('pricing')}
          >
            💰 Pricing
          </button>
          <button
            className={`tab-btn ${activeTab === 'taxes' ? 'active' : ''}`}
            onClick={() => setActiveTab('taxes')}
          >
            📊 Taxes
          </button>
          <button
            className={`tab-btn ${activeTab === 'images' ? 'active' : ''}`}
            onClick={() => setActiveTab('images')}
          >
            🖼️ Product Images
          </button>
        </div>

        <div className="tabs-content">
          {/* Categories Tab */}
          {activeTab === 'categories' && (
            <section className="tab-section">
              <h2>Manage Categories</h2>

              <div className="form-container">
                <form onSubmit={handleCategorySubmit} className="master-form">
                  <h3>{editingCategory ? 'Edit Category' : 'Create New Category'}</h3>

                  <div className="form-group">
                    <label>Category Name *</label>
                    <input
                      type="text"
                      required
                      value={categoryForm.category_name}
                      onChange={(e) => setCategoryForm({ ...categoryForm, category_name: e.target.value })}
                      placeholder="Enter category name"
                    />
                  </div>

                  <div className="form-group">
                    <label>Description</label>
                    <textarea
                      value={categoryForm.category_description}
                      onChange={(e) => setCategoryForm({ ...categoryForm, category_description: e.target.value })}
                      placeholder="Enter category description"
                      rows="4"
                    ></textarea>
                  </div>

                  <div className="form-group checkbox">
                    <label>
                      <input
                        type="checkbox"
                        checked={categoryForm.is_active}
                        onChange={(e) => setCategoryForm({ ...categoryForm, is_active: e.target.checked })}
                      />
                      Active
                    </label>
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Saving...' : editingCategory ? 'Update Category' : 'Create Category'}
                    </button>
                    {editingCategory && (
                      <button type="button" className="btn-secondary" onClick={handleCancelEditCategory}>
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Categories Table */}
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Description</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {categories.map(category => (
                      <tr key={category.category_id}>
                        <td>{category.category_id}</td>
                        <td>{category.category_name}</td>
                        <td>{category.category_description || 'N/A'}</td>
                        <td>
                          <span className={`status ${category.is_active ? 'active' : 'inactive'}`}>
                            {category.is_active ? '✓ Active' : '✗ Inactive'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => handleEditCategory(category)}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Products Tab */}
          {activeTab === 'products' && (
            <section className="tab-section">
              <h2>Manage Products</h2>

              <div className="form-container">
                <form onSubmit={handleProductSubmit} className="master-form">
                  <h3>{editingProduct ? 'Edit Product' : 'Create New Product'}</h3>

                  <div className="form-group">
                    <label>Category *</label>
                    <select
                      required
                      value={productForm.category_id}
                      onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}
                    >
                      <option value="">Select a category</option>
                      {categories.map(cat => (
                        <option key={cat.category_id} value={cat.category_id}>
                          {cat.category_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Product Name *</label>
                    <input
                      type="text"
                      required
                      value={productForm.product_name}
                      onChange={(e) => setProductForm({ ...productForm, product_name: e.target.value })}
                      placeholder="Enter product name"
                    />
                  </div>

                  <div className="form-group">
                    <label>Description</label>
                    <textarea
                      value={productForm.product_description}
                      onChange={(e) => setProductForm({ ...productForm, product_description: e.target.value })}
                      placeholder="Enter product description"
                      rows="4"
                    ></textarea>
                  </div>

                  <div className="form-group checkbox">
                    <label>
                      <input
                        type="checkbox"
                        checked={productForm.is_active}
                        onChange={(e) => setProductForm({ ...productForm, is_active: e.target.checked })}
                      />
                      Active
                    </label>
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Saving...' : editingProduct ? 'Update Product' : 'Create Product'}
                    </button>
                    {editingProduct && (
                      <button type="button" className="btn-secondary" onClick={handleCancelEditProduct}>
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Products Table */}
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Category</th>
                      <th>Name</th>
                      <th>Description</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {products.map(product => (
                      <tr key={product.product_id}>
                        <td>{product.product_id}</td>
                        <td>{getCategoryName(product.category_id)}</td>
                        <td>{product.product_name}</td>
                        <td>{product.product_description || 'N/A'}</td>
                        <td>
                          <span className={`status ${product.is_active ? 'active' : 'inactive'}`}>
                            {product.is_active ? '✓ Active' : '✗ Inactive'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => handleEditProduct(product)}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Pricing Tab */}
          {activeTab === 'pricing' && (
            <section className="tab-section">
              <h2>Manage Product Pricing</h2>

              <div className="form-container">
                <form onSubmit={handlePricingSubmit} className="master-form">
                  <h3>{editingPricing ? 'Edit Pricing' : 'Create New Pricing'}</h3>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Product *</label>
                      <select
                        required
                        value={pricingForm.product_id}
                        onChange={(e) => setPricingForm({ ...pricingForm, product_id: e.target.value })}
                      >
                        <option value="">Select a product</option>
                        {products.map(prod => (
                          <option key={prod.product_id} value={prod.product_id}>
                            {prod.product_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Country *</label>
                      <select
                        required
                        value={pricingForm.country_code}
                        onChange={(e) => setPricingForm({ ...pricingForm, country_code: e.target.value })}
                      >
                        {countries.map(country => (
                          <option key={country.code} value={country.code}>
                            {country.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Currency *</label>
                      <input
                        type="text"
                        required
                        maxLength="5"
                        value={pricingForm.currency_code}
                        onChange={(e) => setPricingForm({ ...pricingForm, currency_code: e.target.value.toUpperCase() })}
                        placeholder="e.g., INR, USD"
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Base Price *</label>
                      <input
                        type="number"
                        step="0.01"
                        required
                        value={pricingForm.base_price}
                        onChange={(e) => setPricingForm({ ...pricingForm, base_price: e.target.value })}
                        placeholder="0.00"
                      />
                    </div>

                    <div className="form-group">
                      <label>Discount %</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="100"
                        value={pricingForm.discount_percent}
                        onChange={(e) => setPricingForm({ ...pricingForm, discount_percent: e.target.value })}
                        placeholder="0"
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group checkbox">
                      <label>
                        <input
                          type="checkbox"
                          checked={pricingForm.is_tax_inclusive}
                          onChange={(e) => setPricingForm({ ...pricingForm, is_tax_inclusive: e.target.checked })}
                        />
                        Tax Inclusive
                      </label>
                    </div>

                    <div className="form-group checkbox">
                      <label>
                        <input
                          type="checkbox"
                          checked={pricingForm.is_active}
                          onChange={(e) => setPricingForm({ ...pricingForm, is_active: e.target.checked })}
                        />
                        Active
                      </label>
                    </div>
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Saving...' : editingPricing ? 'Update Pricing' : 'Create Pricing'}
                    </button>
                    {editingPricing && (
                      <button type="button" className="btn-secondary" onClick={handleCancelEditPricing}>
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Pricing Table */}
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Product</th>
                      <th>Country</th>
                      <th>Currency</th>
                      <th>Base Price</th>
                      <th>Discount %</th>
                      <th>Tax Inclusive</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pricings.map(pricing => (
                      <tr key={pricing.pricing_id}>
                        <td>{pricing.pricing_id}</td>
                        <td>{getProductName(pricing.product_id)}</td>
                        <td>{getCountryName(pricing.country_code)}</td>
                        <td>{pricing.currency_code}</td>
                        <td>{pricing.base_price}</td>
                        <td>{pricing.discount_percent}%</td>
                        <td>{pricing.is_tax_inclusive ? 'Yes' : 'No'}</td>
                        <td>
                          <span className={`status ${pricing.is_active ? 'active' : 'inactive'}`}>
                            {pricing.is_active ? '✓ Active' : '✗ Inactive'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => handleEditPricing(pricing)}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Taxes Tab */}
          {activeTab === 'taxes' && (
            <section className="tab-section">
              <h2>Manage Tax Master</h2>

              <div className="form-container">
                <form onSubmit={handleTaxSubmit} className="master-form">
                  <h3>{editingTax ? 'Edit Tax' : 'Create New Tax'}</h3>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Country *</label>
                      <select
                        required
                        value={taxForm.country_code}
                        onChange={(e) => setTaxForm({ ...taxForm, country_code: e.target.value })}
                      >
                        {countries.map(country => (
                          <option key={country.code} value={country.code}>
                            {country.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>State Code</label>
                      <input
                        type="text"
                        maxLength="10"
                        value={taxForm.state_code}
                        onChange={(e) => setTaxForm({ ...taxForm, state_code: e.target.value })}
                        placeholder="e.g., MH, CA"
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Tax Name *</label>
                    <input
                      type="text"
                      required
                      value={taxForm.tax_name}
                      onChange={(e) => setTaxForm({ ...taxForm, tax_name: e.target.value })}
                      placeholder="e.g., GST, VAT"
                    />
                  </div>

                  <div className="form-group">
                    <label>Tax Percent *</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={taxForm.tax_percent}
                      onChange={(e) => setTaxForm({ ...taxForm, tax_percent: e.target.value })}
                      placeholder="0.00"
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Effective From</label>
                      <input
                        type="date"
                        value={taxForm.effective_from}
                        onChange={(e) => setTaxForm({ ...taxForm, effective_from: e.target.value })}
                      />
                    </div>

                    <div className="form-group">
                      <label>Effective To</label>
                      <input
                        type="date"
                        value={taxForm.effective_to}
                        onChange={(e) => setTaxForm({ ...taxForm, effective_to: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="form-group checkbox">
                    <label>
                      <input
                        type="checkbox"
                        checked={taxForm.is_active}
                        onChange={(e) => setTaxForm({ ...taxForm, is_active: e.target.checked })}
                      />
                      Active
                    </label>
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Saving...' : editingTax ? 'Update Tax' : 'Create Tax'}
                    </button>
                    {editingTax && (
                      <button type="button" className="btn-secondary" onClick={handleCancelEditTax}>
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Taxes Table */}
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Country</th>
                      <th>State</th>
                      <th>Tax Name</th>
                      <th>Tax %</th>
                      <th>Effective From</th>
                      <th>Effective To</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {taxes.map(tax => (
                      <tr key={tax.tax_id}>
                        <td>{tax.tax_id}</td>
                        <td>{getCountryName(tax.country_code)}</td>
                        <td>{tax.state_code || 'N/A'}</td>
                        <td>{tax.tax_name}</td>
                        <td>{tax.tax_percent}%</td>
                        <td>{tax.effective_from || 'N/A'}</td>
                        <td>{tax.effective_to || 'N/A'}</td>
                        <td>
                          <span className={`status ${tax.is_active ? 'active' : 'inactive'}`}>
                            {tax.is_active ? '✓ Active' : '✗ Inactive'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => handleEditTax(tax)}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Product Images Tab */}
          {activeTab === 'images' && (
            <section className="tab-section">
              <h2>Manage Product Images</h2>

              <div className="form-container">
                <form onSubmit={handleImageSubmit} className="master-form">
                  <h3>{editingImage ? 'Edit Image' : 'Add New Image'}</h3>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Product *</label>
                      <select
                        required
                        value={imageForm.product_id}
                        onChange={(e) => setImageForm({ ...imageForm, product_id: e.target.value })}
                      >
                        <option value="">Select a product</option>
                        {products.map(prod => (
                          <option key={prod.product_id} value={prod.product_id}>
                            {prod.product_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Upload Image File</label>
                    <div className="file-input-wrapper">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageFileChange}
                        disabled={editingImage}
                        style={{ display: 'none' }}
                        id="image-file-input"
                      />
                      <label htmlFor="image-file-input" className="file-input-label">
                        📁 Choose Image File (JPG, PNG, WebP - Max 5MB)
                      </label>
                      {imageFile && (
                        <div className="file-selected" style={{ marginTop: '8px' }}>
                          ✓ {imageFile.name}
                          <button
                            type="button"
                            onClick={clearImageFile}
                            className="btn-clear"
                            style={{ marginLeft: '8px' }}
                          >
                            ✕ Clear
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="form-group" style={{ textAlign: 'center', margin: '16px 0' }}>
                    <span style={{ color: '#999' }}>— OR —</span>
                  </div>

                  <div className="form-group">
                    <label>Image URL (Alternative)</label>
                    <input
                      type="url"
                      value={imageForm.image_url}
                      onChange={handleImageUrlChange}
                      placeholder="https://example.com/image.jpg"
                      disabled={!!imageFile}
                    />
                    {imageFile && (
                      <small style={{ color: '#999', display: 'block', marginTop: '4px' }}>
                        File upload selected. URL field disabled.
                      </small>
                    )}
                  </div>

                  <div className="form-row">
                    <div className="form-group checkbox">
                      <label>
                        <input
                          type="checkbox"
                          checked={imageForm.is_primary}
                          onChange={(e) => setImageForm({ ...imageForm, is_primary: e.target.checked })}
                        />
                        Set as Primary
                      </label>
                    </div>
                  </div>

                  {imagePreview && (
                    <div className="image-preview" style={{ marginTop: 16, marginBottom: 16 }}>
                      <img 
                        src={imagePreview} 
                        alt="preview" 
                        style={{ maxWidth: '200px', maxHeight: '200px', borderRadius: '4px' }}
                        onError={(e) => {e.target.src = 'https://via.placeholder.com/200?text=Invalid+URL'; }}
                      />
                    </div>
                  )}

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading || uploadingImage}>
                      {uploadingImage ? 'Uploading...' : loading ? 'Saving...' : editingImage ? 'Update Image' : 'Add Image'}
                    </button>
                    {editingImage && (
                      <button type="button" className="btn-secondary" onClick={handleCancelEditImage}>
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Images Table */}
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Product</th>
                      <th>Image URL</th>
                      <th>Primary</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productImages.map(image => (
                      <tr key={image.image_id}>
                        <td>{image.image_id}</td>
                        <td>{getProductName(image.product_id)}</td>
                        <td>
                          <a href={image.image_url} target="_blank" rel="noopener noreferrer" style={{ color: '#007bff', textDecoration: 'none' }}>
                            View
                          </a>
                        </td>
                        <td>
                          <span style={{ color: image.is_primary ? '#28a745' : '#6c757d' }}>
                            {image.is_primary ? '⭐ Yes' : 'No'}
                          </span>
                        </td>
                        <td>{image.created_at ? new Date(image.created_at).toLocaleDateString() : 'N/A'}</td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => handleEditImage(image)}
                          >
                            Edit
                          </button>
                          <button
                            className="btn-delete"
                            onClick={() => handleDeleteImage(image.image_id)}
                            style={{ marginLeft: '8px', backgroundColor: '#dc3545' }}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {productImages.length === 0 && (
                  <p style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                    No images added yet. Create one using the form above.
                  </p>
                )}
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

export default ProductMaster;
