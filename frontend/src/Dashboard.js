import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

function Dashboard() {

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [memberType, setMemberType] = useState('Unknown');
  const [custName, setCustName] = useState('');
  const [totalPrice, setTotalPrice] = useState(0);
  const [labels, setLabels] = useState([]);
  const [values, setValues] = useState([]);
  const [dateFilter, setDateFilter] = useState('today');
  const navigate = useNavigate();
  const userFullName = localStorage.getItem('userFullName')?.toLowerCase() || '';

  useEffect(() => {
    // First, check authentication
    fetch('https://numerojyotish.onrender.com/api/check-auth', {
      method: 'GET',
      credentials: 'include',
    })
      .then(res => res.json())
      .then(auth => {
        if (!auth.authenticated) {
          setError('Session expired. Please log in again.');
          setTimeout(() => navigate('/'), 2000);
          setLoading(false);
          return;
        }
        // If authenticated, fetch dashboard data
       
        fetch('https://numerojyotish.onrender.com/api/dashboard', {
        
          method: 'GET',
          credentials: 'include',
        })
          .then(res => {
            if (res.status === 401) throw new Error('Unauthorized');
            return res.json();
          })
          .then(data => {
            if (data.success) {
              setOrders(data.tableRows || []);
              setLabels(data.labels || []);
              setValues(data.values || []);
              setCustName(data.custName || '');
              setTotalPrice(data.totalPrice || 0);
              setMemberType(data.memberType || 'Unknown');
            } else {
              setError('Failed to load dashboard');
            }
          })
          .catch(() => {
            setError('You must be logged in to view the dashboard.');
            setTimeout(() => navigate('/'), 1500);
          })
          .finally(() => setLoading(false));
      })
      .catch(() => {
        setError('Session check failed. Please log in again.');
        setTimeout(() => navigate('/'), 2000);
        setLoading(false);
      });
  }, [navigate]);

  useEffect(() => {
    const now = new Date();
    const filtered = orders.filter((row) => {
      const orderDate = new Date(row[8]);
      const diffTime = now - orderDate;
      const diffDays = diffTime / (1000 * 3600 * 24);
      const fullNameInRow = `${row[0]} ${row[1]}`.toLowerCase();

      if (!fullNameInRow.includes(userFullName)) return false;

      switch (dateFilter) {
        case 'today':
          return orderDate.toDateString() === now.toDateString();
        case 'last_7_days':
          return diffDays <= 7;
        case 'last_1_months':
          return diffDays <= 30;
        case 'last_3_months':
          return diffDays <= 90;
        case 'last_6_months':
          return diffDays <= 180;
        case 'last_12_months':
          return diffDays <= 365;
        case 'lifetime':
        default:
          return true;
      }
    });

    setFilteredOrders(filtered);
  }, [orders, dateFilter, userFullName]);

  useEffect(() => {
    if (labels.length && values.length && window.Chart) {
      const existingChart = window.barChartInstance;
      if (existingChart) existingChart.destroy();
      const ctx = document.getElementById('monthBarChart')?.getContext('2d');
      if (ctx) {
        window.barChartInstance = new window.Chart(ctx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: 'Total Price',
              data: values,
              backgroundColor: '#A76545',
              borderColor: '#fff',
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'top' },
              title: { display: true, text: 'Monthly Sales Summary' }
            },
            scales: { y: { beginAtZero: true } }
          }
        });
      }
    }
  }, [labels, values]);

  function remainingToNextTier(total) {
    if (total <= 1500) return 1500 - total;
    if (total <= 3000) return 3000 - total;
    if (total <= 5000) return 5000 - total;
    return 0;
  }

  function nextTier(current) {
    const tiers = ["Brass", "Silver", "Gold", "Platinum"];
    const idx = tiers.indexOf(current);
    return idx >= 0 && idx < 3 ? tiers[idx + 1] : null;
  }

  if (loading) return <div className="dashboard-loading">Loading dashboard...</div>;
  if (error) return <div className="dashboard-error">{error}</div>;

  // Show special message for users with no orders
  if (filteredOrders.length === 0 && totalPrice === 0) {
    return (
      <div className="dashboard-container">
        <div className="empty-dashboard-card">
          <div className="welcome-title">Hey {custName.split(' ')[0] || 'there'}, welcome!</div>
          <p className="empty-message">Looks like you haven't placed any orders yet.</p>
          <p className="empty-subtext">Once you start shopping, your dashboard will come to life!</p>
          <button className="shop-button" onClick={() => navigate('/shop')}>Start Shopping</button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-center">
        <div className={`membership-card ${memberType.toLowerCase()}`}> 
          <div className="membership-header-flex" style={{ position: 'relative' }}>
            <div className="membership-header-right" style={{ position: 'absolute', top: 0, right: 0, zIndex: 2 }}>
              <div className="user-circle">
                <span>{custName.charAt(0)}</span>
              </div>
            </div>
            <div className="membership-header-left">
              <div className="dashboard-header-row">
                <span className="dashboard-bold dashboard-header-name">Hey {custName.split(' ')[0]}</span>
                <span className="dashboard-total-spent">- Total Spent (Last 365 Days) - <span className="dashboard-bold dashboard-total-amount">${totalPrice}</span></span>
              </div>
              <div className="member-type-row">
                <span className="member-tier">{memberType} Member</span>
              </div>
              {memberType !== 'Platinum' && (
                <div className="dashboard-upgrade-row">
                  <span className="upgrade-pill">Shop for ${remainingToNextTier(totalPrice).toFixed(2)} more to upgrade to <span className="next-tier-pill">{nextTier(memberType)}</span></span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="dashboard-chart">
          <div className="dashboard-chart-title-row">
            <span className="dashboard-chart-title">Monthly Sales Summary</span>
            <span className="dashboard-chart-legend"><span className="dashboard-legend-box"></span> Total Price</span>
          </div>
          <canvas id="monthBarChart" className="dashboard-canvas"></canvas>
        </div>

        <div className="dashboard-orders">
          <div className="filter-bar">
            <label htmlFor="date-filter">Filter Orders:</label>
            <select
              id="date-filter"
              name="date_filter"
              value={dateFilter}
              onChange={e => setDateFilter(e.target.value)}
            >
              <option value="today">Today</option>
              <option value="last_7_days">Last 7 Days</option>
              <option value="last_1_months">Last 1 Month</option>
              <option value="last_3_months">Last 3 Months</option>
              <option value="last_6_months">Last 6 Months</option>
              <option value="last_12_months">Last 12 Months</option>
              <option value="lifetime">Lifetime</option>
            </select>
          </div>
          <div className="custom-table">
            <div className="table-row header">
              <div>Name</div><div>Total</div><div>Discount</div><div>Status</div><div>Fulfilled</div><div>Financial</div><div>Cancel Reason</div>
            </div>
            {filteredOrders.map((row, i) => (
              <div key={i} className="table-row">
                <div>{`${row[0] ?? ''} ${row[1] ?? ''}`.trim()}</div>
                <div>{row[2]}</div>
                <div>{row[3]}</div>
                <div style={{ color: row[4]?.toLowerCase().includes('cancel') ? 'red' : 'green' }}>{row[4]}</div>
                <div>{row[5]}</div>
                <div>{row[6]}</div>
                <div>{row[7]}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;