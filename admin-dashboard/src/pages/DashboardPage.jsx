import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import PaymentCountdown from '../components/PaymentCountdown';
import ElectronicPaymentForm from '../components/ElectronicPaymentForm';
import PricingTransparencyPanel from '../components/PricingTransparencyPanel';
import QRCode from 'react-qr-code';
import Confetti from 'react-confetti';
import { useWindowSize } from 'react-use';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import * as XLSX from 'xlsx';
import './DashboardPage.css';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [currentTab, setCurrentTab] = useState('overview'); // overview, buildings, rooms, students, invoices, users
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // Sidebar toggle state
  
  // البيانات الأساسية
  const [buildings, setBuildings] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [students, setStudents] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [complaints, setComplaints] = useState([]);
  
  // حالات التحميل والخطأ
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // الميزات السحرية (Magical Features States)
  const [showConfetti, setShowConfetti] = useState(false);
  const { width, height } = useWindowSize();
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const [showFabMenu, setShowFabMenu] = useState(false);

  // تطبيق السمة (Theme)
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);


  // حالات النوافذ المنبثقة (Modals)
  const [showModal, setShowModal] = useState(null); // 'building', 'room', 'student', 'invoice', 'user', 'qr', 'image'
  const [activeQR, setActiveQR] = useState(null);
  const [activeImage, setActiveImage] = useState(null);

  // نماذج الإدخال (Form States)
  const [buildingForm, setBuildingForm] = useState({ name: '', code: '' });
  const [roomForm, setRoomForm] = useState({ room_number: '', building: '', qr_code: '' });
  const [studentForm, setStudentForm] = useState({ name: '', phone: '', room: '', status: 'active' });
  const [userForm, setUserForm] = useState({ username: '', password_hash: '', role: 'delegate', permissions: {} });
  const [invoiceForm, setInvoiceForm] = useState({
    room: '',
    reading_old: '',
    reading_new: '',
    unit_price: '0.18',
    previous_debt: '0',
    meter_image_url: ''
  });
  const [complaintForm, setComplaintForm] = useState({ student: '', subject: '', message: '' });

  // فلاتر البحث
  const [buildingFilter, setBuildingFilter] = useState('');
  const [roomFilter, setRoomFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    fetchData();
  }, [currentTab]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      if (currentTab === 'overview') {
        const [bRes, rRes, sRes, iRes] = await Promise.all([
          axiosClient.get('/buildings/'),
          axiosClient.get('/rooms/'),
          axiosClient.get('/students/'),
          axiosClient.get('/invoices/')
        ]);
        setBuildings(bRes.data);
        setRooms(rRes.data);
        setStudents(sRes.data);
        setInvoices(iRes.data);
      } else if (currentTab === 'buildings') {
        const res = await axiosClient.get('/buildings/');
        setBuildings(res.data);
      } else if (currentTab === 'rooms') {
        const [rRes, bRes] = await Promise.all([
          axiosClient.get('/rooms/'),
          axiosClient.get('/buildings/')
        ]);
        setRooms(rRes.data);
        setBuildings(bRes.data);
      } else if (currentTab === 'students') {
        const [sRes, rRes] = await Promise.all([
          axiosClient.get('/students/'),
          axiosClient.get('/rooms/')
        ]);
        setStudents(sRes.data);
        setRooms(rRes.data);
      } else if (currentTab === 'invoices') {
        const [iRes, rRes] = await Promise.all([
          axiosClient.get('/invoices/'),
          axiosClient.get('/rooms/')
        ]);
        setInvoices(iRes.data);
        setRooms(rRes.data);
      } else if (currentTab === 'users' && user?.role === 'admin') {
        const res = await axiosClient.get('/users/');
        setUsersList(res.data);
      } else if (currentTab === 'complaints') {
        const [cRes, sRes] = await Promise.all([
          axiosClient.get('/complaints/'),
          axiosClient.get('/students/')
        ]);
        setComplaints(cRes.data);
        setStudents(sRes.data);
      }
    } catch (err) {
      console.error(err);
      setError('فشل في جلب البيانات من السيرفر. تأكد من اتصالك.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const showNotification = (msg, isSuccess = true) => {
    if (isSuccess) {
      setSuccess(msg);
      setError('');
      setTimeout(() => setSuccess(''), 4000);
    } else {
      setError(msg);
      setSuccess('');
      setTimeout(() => setError(''), 4000);
    }
  };

  // ── عمليات الإضافة (Creation Handlers) ──

  const handleAddBuilding = async (e) => {
    e.preventDefault();
    try {
      await axiosClient.post('/buildings/', buildingForm);
      showNotification('تم إضافة المبنى بنجاح!');
      setShowModal(null);
      setBuildingForm({ name: '', code: '' });
      fetchData();
    } catch (err) {
      showNotification('فشل إضافة المبنى. تحقق من إدخال رمز فريد من حرف واحد.', false);
    }
  };

  const handleAddRoom = async (e) => {
    e.preventDefault();
    // توليد كود الـ QR تلقائياً إذا لم يدخله المستخدم
    const selectedBuilding = buildings.find(b => b.id === parseInt(roomForm.building));
    const generatedQR = roomForm.qr_code || (selectedBuilding ? `${selectedBuilding.code}-${roomForm.room_number}` : `QR-${roomForm.room_number}`);
    
    try {
      await axiosClient.post('/rooms/', {
        ...roomForm,
        qr_code: generatedQR
      });
      showNotification('تم إضافة الغرفة بنجاح!');
      setShowModal(null);
      setRoomForm({ room_number: '', building: '', qr_code: '' });
      fetchData();
    } catch (err) {
      showNotification('فشل إضافة الغرفة. قد تكون الغرفة موجودة بالفعل في هذا المبنى.', false);
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...studentForm,
        room: parseInt(studentForm.room)
      };
      await axiosClient.post('/students/', payload);
      showNotification('تم تسكين الطالب بنجاح!');
      setShowModal(null);
      setStudentForm({ name: '', phone: '', room: '', status: 'active' });
      fetchData();
    } catch (err) {
      console.error("Add student error:", err.response?.data);
      const errorMsg = err.response?.data?.room ? 'تأكد من اختيار الغرفة بشكل صحيح.' : 'فشل تسكين الطالب. تأكد من البيانات المدخلة.';
      showNotification(errorMsg, false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      await axiosClient.post('/users/', userForm);
      showNotification('تم إضافة المستخدم بنجاح!');
      setShowModal(null);
      setUserForm({ username: '', password_hash: '', role: 'delegate', permissions: {} });
      fetchData();
    } catch (err) {
      showNotification('فشل إضافة المستخدم. قد يكون اسم المستخدم مكرر.', false);
    }
  };

  const handleAddInvoice = async (e) => {
    e.preventDefault();
    try {
      // دالة مساعدة لسحب الـ CSRF Token من الـ Cookies
      const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
      };

      await axiosClient.post('/invoices/', {
        ...invoiceForm,
        reading_old: parseFloat(invoiceForm.reading_old),
        reading_new: parseFloat(invoiceForm.reading_new),
        unit_price: parseFloat(invoiceForm.unit_price),
        previous_debt: parseFloat(invoiceForm.previous_debt)
      }, {
        withCredentials: true,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') || getCookie('XSRF-TOKEN')
        }
      });
      showNotification('تم إنشاء الفاتورة بنجاح وهي قيد المراجعة!');
      setShowModal(null);
      setInvoiceForm({
        room: '',
        reading_old: '',
        reading_new: '',
        unit_price: '0.18',
        previous_debt: '0',
        meter_image_url: ''
      });
      fetchData();
    } catch (err) {
      const errorMsg = err.response?.data?.non_field_errors?.[0] || 'فشل إنشاء الفاتورة. تأكد من أن القراءة الجديدة أكبر من القديمة.';
      showNotification(errorMsg, false);
    }
  };

  // ── عمليات تحديث الفواتير (Invoice Actions) ──

  const handleApproveInvoice = async (id) => {
    try {
      await axiosClient.post(`/invoices/${id}/approve/`);
      showNotification('تم اعتماد الفاتورة بنجاح!');
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 5000); // إخفاء بعد 5 ثوانٍ
      fetchData();
    } catch (err) {
      showNotification('فشل اعتماد الفاتورة.', false);
    }
  };

  const handlePayInvoice = async (id) => {
    try {
      await axiosClient.post(`/invoices/${id}/mark_paid/`);
      showNotification('تم تسجيل دفع الفاتورة بنجاح!');
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 5000); // إخفاء بعد 5 ثوانٍ
      fetchData();
    } catch (err) {
      showNotification('فشل تسجيل دفع الفاتورة.', false);
    }
  };

  const handleSubmitComplaint = async (e) => {
    e.preventDefault();
    if (!complaintForm.student || !complaintForm.subject || !complaintForm.message) {
      showNotification('يرجى تعبئة جميع الحقول.', false);
      return;
    }
    try {
      await axiosClient.post('/complaints/', complaintForm);
      showNotification('تم إرسال الشكوى بنجاح!');
      setComplaintForm({ student: '', subject: '', message: '' });
      fetchData();
    } catch (err) {
      showNotification('فشل إرسال الشكوى.', false);
    }
  };

  const handleUpdateComplaintStatus = async (id, status) => {
    try {
      await axiosClient.patch(`/complaints/${id}/`, { status });
      showNotification('تم تحديث حالة الشكوى!');
      fetchData();
    } catch (err) {
      showNotification('فشل تحديث حالة الشكوى.', false);
    }
  };

  const getRoleLabel = (role) => {
    const roles = { admin: 'مشرف رئيسي', delegate: 'مندوب ميداني', accountant: 'محاسب مالي' };
    return roles[role] || role;
  };

  const getInvoiceStatusBadge = (status) => {
    const badges = {
      pending: <span className="badge badge-pending">⏳ قيد المراجعة</span>,
      approved: <span className="badge badge-approved">✅ معتمدة</span>,
      paid: <span className="badge badge-paid">💰 مدفوعة</span>
    };
    return badges[status] || status;
  };

  // ── تصدير إلى إكسل ──
  const handleExportInvoices = () => {
    const dataToExport = filteredInvoices.map(inv => ({
      'رقم الغرفة': inv.room_qr,
      'القراءة القديمة': inv.reading_old,
      'القراءة الجديدة': inv.reading_new,
      'الاستهلاك': inv.consumption,
      'السعر الإجمالي (ريال)': inv.final_amount,
      'حالة الفاتورة': inv.status === 'paid' ? 'مدفوعة' : inv.status === 'approved' ? 'معتمدة' : 'قيد المراجعة',
      'تاريخ الإنشاء': new Date(inv.created_at).toLocaleDateString('ar-SA')
    }));
    const worksheet = XLSX.utils.json_to_sheet(dataToExport);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "الفواتير");
    XLSX.writeFile(workbook, "تقرير_الفواتير.xlsx");
  };

  const handleExportStudents = () => {
    const dataToExport = filteredStudents.map(s => ({
      'اسم الطالب': s.name,
      'رقم الهاتف': s.phone,
      'الغرفة': s.room_qr,
      'الحالة': s.status === 'active' ? 'نشط' : 'مغادر',
      'تاريخ التسجيل': new Date(s.created_at).toLocaleDateString('ar-SA')
    }));
    const worksheet = XLSX.utils.json_to_sheet(dataToExport);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "الطلاب");
    XLSX.writeFile(workbook, "تقرير_الطلاب.xlsx");
  };

  // تصفية وتصفح الفواتير والغرف والطلاب
  const filteredRooms = rooms.filter(r => {
    return (!buildingFilter || r.building === parseInt(buildingFilter)) &&
           (!roomFilter || r.room_number.toString().includes(roomFilter));
  });

  const filteredInvoices = invoices.filter(i => {
    return (!statusFilter || i.status === statusFilter) &&
           (!roomFilter || i.room_qr.toLowerCase().includes(roomFilter.toLowerCase()));
  });

  const filteredStudents = students.filter(s => {
    return (!roomFilter || s.room_qr.toLowerCase().includes(roomFilter.toLowerCase())) &&
           (!statusFilter || s.status === statusFilter);
  });

  // ── تحضير بيانات الرسوم البيانية (Charts Data) ──
  const statusData = [
    { name: 'مدفوعة', value: invoices.filter(i => i.status === 'paid').length, color: '#10b981' },
    { name: 'معتمدة', value: invoices.filter(i => i.status === 'approved').length, color: '#6366f1' },
    { name: 'معلقة', value: invoices.filter(i => i.status === 'pending').length, color: '#f59e0b' }
  ].filter(d => d.value > 0);

  const topConsumers = [...invoices]
    .sort((a, b) => b.consumption - a.consumption)
    .slice(0, 5)
    .map(inv => ({
      room: inv.room_qr,
      consumption: inv.consumption,
      amount: inv.final_amount
    }));

  return (
    <div className="dashboard-container">
      {/* ── الاحتفال (Confetti) ── */}
      {showConfetti && <Confetti width={width} height={height} numberOfPieces={300} />}

      {/* ── Overlay للموبايل ── */}
      {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)}></div>}

      {/* ── الشريط الجانبي (Sidebar) ── */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <button className="close-sidebar-btn" onClick={() => setIsSidebarOpen(false)}>✕</button>
          <div className="logo-icon">⚡</div>
          <h2>نظام الفواتير</h2>
          <span>الكهربائية للمباني</span>
        </div>

        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${currentTab === 'overview' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('overview'); setIsSidebarOpen(false); }}
          >
            📊 لوحة التحكم
          </button>
          
          <button 
            className={`nav-item ${currentTab === 'buildings' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('buildings'); setIsSidebarOpen(false); }}
          >
            🏢 إدارة المباني
          </button>

          <button 
            className={`nav-item ${currentTab === 'rooms' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('rooms'); setIsSidebarOpen(false); }}
          >
            🔑 إدارة الغرف
          </button>

          <button 
            className={`nav-item ${currentTab === 'students' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('students'); setIsSidebarOpen(false); }}
          >
            👥 إدارة الطلاب
          </button>

          <button 
            className={`nav-item ${currentTab === 'invoices' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('invoices'); setIsSidebarOpen(false); }}
          >
            📄 فواتير الاستهلاك
          </button>

          <button 
            className={`nav-item ${currentTab === 'complaints' ? 'active' : ''}`}
            onClick={() => { setCurrentTab('complaints'); setIsSidebarOpen(false); }}
          >
            📩 الشكاوى والملاحظات
          </button>

          {user?.role === 'admin' && (
            <button 
              className={`nav-item ${currentTab === 'users' ? 'active' : ''}`}
              onClick={() => { setCurrentTab('users'); setIsSidebarOpen(false); }}
            >
              ⚙️ إدارة المستخدمين
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">👤</div>
            <div className="user-meta">
              <h4>{user?.username}</h4>
              <span>{getRoleLabel(user?.role)}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="logout-button">
            🚪 تسجيل الخروج
          </button>
          
          <div className="developer-badge" style={{ marginTop: '20px', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', textAlign: 'center' }}>
            <span style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>تطوير: <strong style={{ color: 'var(--primary)' }}>مشتاق الفقيه</strong></span>
            <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)' }} dir="ltr">+967 775 336 886</span>
            <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)' }}>صنعاء</span>
          </div>
        </div>
      </aside>

      {/* ── القسم الرئيسي (Main Content) ── */}
      <main className="main-content">
        <header className="content-header">
          <div className="header-left-side">
            <button className="menu-toggle" onClick={() => setIsSidebarOpen(true)}>
              ☰
            </button>
            <div className="welcome-text">
              <h1>لوحة التحكم الرقمية</h1>
              <p>مرحباً بك مجدداً، تدير هذا النظام بصفتك {getRoleLabel(user?.role)}</p>
            </div>
          </div>

          <div className="quick-actions">
            {/* زر تبديل الثيم */}
            <button 
              className="btn btn-secondary" 
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              style={{ borderRadius: '50%', width: '45px', height: '45px', padding: 0 }}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            {user?.role === 'admin' && (
              <>
                <button className="btn btn-primary" onClick={() => setShowModal('building')}>➕ مبنى جديد</button>
                <button className="btn btn-secondary" onClick={() => setShowModal('room')}>➕ غرفة جديدة</button>
                <button className="btn btn-accent" onClick={() => setShowModal('student')}>➕ تسكين طالب</button>
              </>
            )}
            {(user?.role === 'delegate' || user?.role === 'admin') && (
              <button className="btn btn-success" onClick={() => setShowModal('invoice')}>📝 فاتورة جديدة</button>
            )}
          </div>
        </header>

        {/* تنبيهات النجاح والخطأ */}
        {success && <div className="alert alert-success">{success}</div>}
        {error && <div className="alert alert-danger">{error}</div>}

        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>جاري تحميل البيانات...</p>
          </div>
        ) : (
          <div className="tab-content">
            
            {/* ── 1. قسم لوحة التحكم العامة (Overview) ── */}
            {currentTab === 'overview' && (
              <div className="overview-tab">
                <div className="stats-grid">
                  <div className="stat-card blue">
                    <h3>المباني</h3>
                    <p className="value">{buildings.length}</p>
                    <span className="desc">إجمالي المباني السكنية</span>
                  </div>
                  <div className="stat-card purple">
                    <h3>الغرف</h3>
                    <p className="value">{rooms.length}</p>
                    <span className="desc">إجمالي الغرف المسجلة</span>
                  </div>
                  <div className="stat-card green">
                    <h3>الطلاب المسكنين</h3>
                    <p className="value">{students.filter(s => s.status === 'active').length}</p>
                    <span className="desc">الطلاب النشطين حالياً</span>
                  </div>
                  <div className="stat-card gold">
                    <h3>الفواتير المعلقة</h3>
                    <p className="value">{invoices.filter(i => i.status === 'pending').length}</p>
                    <span className="desc">بانتظار الاعتماد المالي</span>
                  </div>
                </div>

                <div className="dashboard-charts-grid" style={{ marginBottom: '40px', display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                  {/* الدائرة البيانية لحالة الفواتير */}
                  <div className="panel" style={{ flex: '1', minWidth: '280px', padding: '24px' }}>
                    <div className="panel-header" style={{ marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '16px' }}>حالة تحصيل الفواتير</h3>
                    </div>
                    <div style={{ height: '220px', width: '100%' }}>
                      {statusData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie 
                              data={statusData} 
                              innerRadius={60} 
                              outerRadius={80} 
                              paddingAngle={5} 
                              dataKey="value"
                              stroke="none"
                            >
                              {statusData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip 
                              contentStyle={{ backgroundColor: 'var(--sidebar-bg)', borderColor: 'var(--border-color)', borderRadius: '12px', color: 'var(--text-primary)' }}
                              itemStyle={{ color: 'var(--text-primary)' }}
                              formatter={(value, name) => [value + ' فاتورة', name]}
                            />
                            <Legend verticalAlign="bottom" height={36} iconType="circle" />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ display: 'flex', height: '100%', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>لا توجد بيانات فواتير</div>
                      )}
                    </div>
                  </div>

                  {/* الرسم الشريطي لأعلى استهلاك */}
                  <div className="panel" style={{ flex: '2', minWidth: '320px', padding: '24px' }}>
                    <div className="panel-header" style={{ marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '16px' }}>أعلى 5 غرف استهلاكاً للكهرباء (كيلوواط)</h3>
                    </div>
                    <div style={{ height: '220px', width: '100%' }}>
                      {topConsumers.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={topConsumers} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="room" stroke="var(--text-secondary)" tick={{fontSize: 12}} tickMargin={10} axisLine={false} tickLine={false} />
                            <YAxis stroke="var(--text-secondary)" tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                            <Tooltip 
                              contentStyle={{ backgroundColor: 'var(--sidebar-bg)', borderColor: 'var(--border-color)', borderRadius: '12px', color: 'var(--text-primary)' }}
                              itemStyle={{ color: 'var(--accent)' }}
                              formatter={(value, name) => [value + ' KWh', 'الاستهلاك']}
                            />
                            <Bar dataKey="consumption" fill="var(--accent)" radius={[6, 6, 0, 0]} barSize={40} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ display: 'flex', height: '100%', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>لا توجد استهلاكات مسجلة</div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="dashboard-charts-grid">
                  {/* الفواتير الأخيرة */}
                  <div className="panel">
                    <div className="panel-header">
                      <h3>آخر الفواتير المضافة</h3>
                      <button className="panel-link" onClick={() => setCurrentTab('invoices')}>عرض الكل</button>
                    </div>
                    <div className="table-responsive">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>رقم الغرفة</th>
                            <th>الاستهلاك (ك.و.س)</th>
                            <th>المبلغ الإجمالي</th>
                            <th>الحالة</th>
                            <th>تاريخ الفاتورة</th>
                          </tr>
                        </thead>
                        <tbody>
                          {invoices.slice(0, 5).map(inv => (
                            <tr key={inv.id}>
                              <td data-label="رقم الغرفة"><strong>{inv.room_qr}</strong></td>
                              <td data-label="الاستهلاك (ك.و.س)">{inv.consumption || '0'} ك.و.س</td>
                              <td data-label="المبلغ الإجمالي">{inv.final_amount} ريال</td>
                              <td data-label="الحالة">{getInvoiceStatusBadge(inv.status)}</td>
                              <td data-label="تاريخ الفاتورة">{new Date(inv.created_at).toLocaleDateString('ar-SA')}</td>
                            </tr>
                          ))}
                          {invoices.length === 0 && (
                            <tr>
                              <td colSpan="5" className="empty-row">لا توجد فواتير مسجلة بعد.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── 2. قسم المباني (Buildings) ── */}
            {currentTab === 'buildings' && (
              <div className="panel">
                <div className="panel-header">
                  <h3>قائمة المباني السكنية</h3>
                  {user?.role === 'admin' && (
                    <button className="btn btn-primary btn-sm" onClick={() => setShowModal('building')}>➕ إضافة مبنى</button>
                  )}
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>رقم المعرف</th>
                        <th>اسم المبنى</th>
                        <th>رمز المبنى الفريد</th>
                      </tr>
                    </thead>
                    <tbody>
                      {buildings.map(b => (
                        <tr key={b.id}>
                          <td data-label="رقم المعرف">#{b.id}</td>
                          <td data-label="اسم المبنى"><strong>{b.name}</strong></td>
                          <td data-label="رمز المبنى الفريد"><span className="code-badge">{b.code}</span></td>
                        </tr>
                      ))}
                      {buildings.length === 0 && (
                        <tr>
                          <td colSpan="3" className="empty-row">لا توجد مبانٍ مسجلة.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── 3. قسم الغرف (Rooms) ── */}
            {currentTab === 'rooms' && (
              <div className="panel">
                <div className="panel-header">
                  <h3>إدارة الغرف والمفاتيح الذكية</h3>
                  <div className="filters">
                    <select 
                      value={buildingFilter} 
                      onChange={(e) => setBuildingFilter(e.target.value)}
                      className="filter-select"
                    >
                      <option value="">كل المباني</option>
                      {buildings.map(b => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </select>
                    <input 
                      type="text" 
                      placeholder="ابحث برقم الغرفة..." 
                      value={roomFilter} 
                      onChange={(e) => setRoomFilter(e.target.value)}
                      className="filter-input"
                    />
                  </div>
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>المبنى</th>
                        <th>رقم الغرفة</th>
                        <th>رمز الاستجابة QR Code</th>
                        <th>ملصق الباب الذكي</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRooms.map(r => (
                        <tr key={r.id}>
                          <td data-label="المبنى">{r.building_name}</td>
                          <td data-label="رقم الغرفة"><strong>الغرفة {r.room_number}</strong></td>
                          <td data-label="رمز الاستجابة QR Code"><code className="qr-text">{r.qr_code}</code></td>
                          <td data-label="ملصق الباب الذكي">
                            <button 
                              className="btn btn-secondary btn-xs"
                              onClick={() => { setActiveQR(r.qr_code); setShowModal('qr'); }}
                            >
                              🔍 استعراض ملصق QR
                            </button>
                          </td>
                        </tr>
                      ))}
                      {filteredRooms.length === 0 && (
                        <tr>
                          <td colSpan="4" className="empty-row">لا توجد غرف مطابقة للبحث.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── 4. قسم الطلاب (Students) ── */}
            {currentTab === 'students' && (
              <div className="panel">
                <div className="panel-header">
                  <h3>إدارة الطلاب وتسكين السكن</h3>
                  <div className="filters">
                    <button className="btn btn-success" onClick={handleExportStudents} style={{ marginLeft: '12px' }}>
                      📥 تصدير إلى Excel
                    </button>
                    <input 
                      type="text" 
                      placeholder="ابحث برمز الغرفة..." 
                      value={roomFilter} 
                      onChange={(e) => setRoomFilter(e.target.value)}
                      className="filter-input"
                    />
                    <select 
                      value={statusFilter} 
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="filter-select"
                    >
                      <option value="">كل الحالات</option>
                      <option value="active">نشط</option>
                      <option value="left">غادر السكن</option>
                    </select>
                  </div>
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>اسم الطالب</th>
                        <th>رقم الهاتف</th>
                        <th>الغرفة المخصصة</th>
                        <th>الحالة</th>
                        <th>تاريخ التسكين</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredStudents.map(s => (
                        <tr key={s.id}>
                          <td data-label="اسم الطالب"><strong>{s.name}</strong></td>
                          <td data-label="رقم الهاتف">{s.phone}</td>
                          <td data-label="الغرفة المخصصة">{s.room_qr}</td>
                          <td data-label="الحالة">
                            <span className={`status-dot ${s.status === 'active' ? 'active' : 'left'}`}>
                              {s.status === 'active' ? 'نشط بالسكن' : 'غادر السكن'}
                            </span>
                          </td>
                          <td data-label="تاريخ التسكين">{new Date(s.created_at).toLocaleDateString('ar-SA')}</td>
                        </tr>
                      ))}
                      {filteredStudents.length === 0 && (
                        <tr>
                          <td colSpan="5" className="empty-row">لا توجد سجلات طلاب مطابقة للبحث.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── 5. قسم الفواتير (Invoices) ── */}
            {currentTab === 'invoices' && (
              <>
                <PricingTransparencyPanel />
                <div className="panel">
                  <div className="panel-header">
                  <h3>إدارة الفواتير والتحقق من القراءات</h3>
                  <div className="filters">
                    <button className="btn btn-success" onClick={handleExportInvoices} style={{ marginLeft: '12px' }}>
                      📥 تصدير إلى Excel
                    </button>
                    <select 
                      value={statusFilter} 
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="filter-select"
                    >
                      <option value="">كل الحالات</option>
                      <option value="pending">قيد المراجعة</option>
                      <option value="approved">معتمدة</option>
                      <option value="paid">مدفوعة</option>
                    </select>
                    <input 
                      type="text" 
                      placeholder="ابحث برمز الغرفة..." 
                      value={roomFilter} 
                      onChange={(e) => setRoomFilter(e.target.value)}
                      className="filter-input"
                    />
                  </div>
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>رقم الغرفة</th>
                        <th>القراءة القديمة</th>
                        <th>القراءة الجديدة</th>
                        <th>الاستهلاك</th>
                        <th>السعر الإجمالي</th>
                        <th>سجل الفاتورة</th>
                        <th>مهلة السداد</th>
                        <th>الحالة والأكشن</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredInvoices.map(inv => (
                        <tr key={inv.id}>
                          <td data-label="رقم الغرفة"><strong>{inv.room_qr}</strong></td>
                          <td data-label="القراءة القديمة">{inv.reading_old} ك.و.س</td>
                          <td data-label="القراءة الجديدة">{inv.reading_new} ك.و.س</td>
                          <td data-label="الاستهلاك"><span className="consumption-text">{inv.consumption} ك.و.س</span></td>
                          <td data-label="السعر الإجمالي">
                            <div className="price-details">
                              <strong>{inv.final_amount} ريال</strong>
                              <small>السابق: {inv.previous_debt} ريال</small>
                            </div>
                          </td>
                          <td data-label="سجل الفاتورة">
                            <div className="user-logs">
                              <small>بواسطة: {inv.created_by_username || 'غير محدد'}</small>
                              <small>المعتمد: {inv.approved_by_username || 'معلقة'}</small>
                            </div>
                          </td>
                          <td data-label="مهلة السداد">
                            {inv.status !== 'paid' ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <PaymentCountdown 
                                  payment_deadline={inv.payment_deadline} 
                                  isOverdue={inv.is_overdue} 
                                  overdueFine={inv.overdue_fine} 
                                />
                                <ElectronicPaymentForm 
                                  invoice={inv} 
                                  onPaymentSuccess={fetchData} 
                                />
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>-</span>
                            )}
                          </td>
                          <td data-label="الحالة والأكشن">
                            <div className="action-cell">
                              {getInvoiceStatusBadge(inv.status)}
                              
                              {/* أزرار العمليات بناءً على الصلاحيات والحالة */}
                              {inv.status === 'pending' && (user?.role === 'accountant' || user?.role === 'admin') && (
                                <button 
                                  onClick={() => handleApproveInvoice(inv.id)}
                                  className="btn btn-secondary btn-xs"
                                >
                                  ⚖️ اعتماد
                                </button>
                              )}
                              {inv.status === 'approved' && (user?.role === 'accountant' || user?.role === 'admin') && (
                                <button 
                                  onClick={() => handlePayInvoice(inv.id)}
                                  className="btn btn-success btn-xs"
                                >
                                  💳 سداد
                                </button>
                              )}
                              
                              {inv.meter_image_url && (
                                <button 
                                  onClick={() => { setActiveImage(inv.meter_image_url); setShowModal('image'); }}
                                  className="btn btn-info btn-xs"
                                >
                                  🖼️ صورة العداد
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                      {filteredInvoices.length === 0 && (
                        <tr>
                          <td colSpan="7" className="empty-row">لا توجد فواتير مطابقة للبحث.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              </>
            )}

            {/* ── 6. قسم المستخدمين (Users) ── */}
            {currentTab === 'users' && user?.role === 'admin' && (
              <div className="panel">
                <div className="panel-header">
                  <h3>إدارة حسابات طاقم العمل</h3>
                  <button className="btn btn-primary btn-sm" onClick={() => setShowModal('user')}>➕ إضافة مستخدم</button>
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>المعرف</th>
                        <th>اسم المستخدم</th>
                        <th>الدور الوظيفي</th>
                        <th>تاريخ الإنشاء</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersList.map(u => (
                        <tr key={u.id}>
                          <td data-label="المعرف">#{u.id}</td>
                          <td data-label="اسم المستخدم"><strong>{u.username}</strong></td>
                          <td data-label="الدور الوظيفي"><span className={`role-badge ${u.role}`}>{getRoleLabel(u.role)}</span></td>
                          <td data-label="تاريخ الإنشاء">{new Date(u.created_at).toLocaleDateString('ar-SA')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── 7. قسم الشكاوى والملاحظات (Complaints) ── */}
            {currentTab === 'complaints' && (
              <div className="panel complaints-panel">
                <div className="panel-header">
                  <h3>الشكاوى والملاحظات</h3>
                </div>
                
                <div className="complaints-container" style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                  
                  {/* نموذج محاكاة الطالب */}
                  <div className="complaint-form-section" style={{ flex: '1', minWidth: '300px', background: 'var(--surface)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
                    <h4>إرسال شكوى (واجهة الطالب)</h4>
                    <form onSubmit={handleSubmitComplaint} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
                      <select 
                        value={complaintForm.student} 
                        onChange={(e) => setComplaintForm({...complaintForm, student: e.target.value})}
                        className="form-input"
                      >
                        <option value="">اختر الطالب...</option>
                        {students.map(s => <option key={s.id} value={s.id}>{s.name} ({s.room_qr})</option>)}
                      </select>
                      <input 
                        type="text" 
                        placeholder="موضوع الشكوى" 
                        value={complaintForm.subject}
                        onChange={(e) => setComplaintForm({...complaintForm, subject: e.target.value})}
                        className="form-input"
                      />
                      <textarea 
                        placeholder="اكتب تفاصيل الشكوى أو الملاحظة هنا..." 
                        value={complaintForm.message}
                        onChange={(e) => setComplaintForm({...complaintForm, message: e.target.value})}
                        className="form-input"
                        rows="4"
                      ></textarea>
                      <button type="submit" className="btn btn-primary">إرسال الشكوى</button>
                    </form>
                  </div>

                  {/* جدول الإدارة */}
                  <div className="complaint-list-section" style={{ flex: '2', minWidth: '400px' }}>
                    <div className="table-responsive">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>الطالب والغرفة</th>
                            <th>الموضوع</th>
                            <th>التاريخ</th>
                            <th>الحالة والأكشن</th>
                          </tr>
                        </thead>
                        <tbody>
                          {complaints.map(c => (
                            <tr key={c.id}>
                              <td data-label="الطالب والغرفة"><strong>{c.student_name}</strong><br/><small>{c.room_qr}</small></td>
                              <td data-label="الموضوع"><strong>{c.subject}</strong><br/><small style={{color: 'var(--text-muted)'}}>{c.message}</small></td>
                              <td data-label="التاريخ">{new Date(c.created_at).toLocaleDateString('ar-SA')}</td>
                              <td data-label="الحالة والأكشن">
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  <span className={`badge badge-${c.status === 'new' ? 'pending' : c.status === 'processing' ? 'warning' : 'paid'}`}>
                                    {c.status === 'new' ? 'جديدة' : c.status === 'processing' ? 'قيد المعالجة' : 'مغلقة'}
                                  </span>
                                  {user?.role !== 'delegate' && (
                                    <select 
                                      value={c.status}
                                      onChange={(e) => handleUpdateComplaintStatus(c.id, e.target.value)}
                                      className="form-input"
                                      style={{ padding: '2px 4px', fontSize: '12px' }}
                                    >
                                      <option value="new">جديدة</option>
                                      <option value="processing">قيد المعالجة</option>
                                      <option value="closed">إغلاق</option>
                                    </select>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                          {complaints.length === 0 && (
                            <tr><td colSpan="4" className="empty-row">لا توجد شكاوى حالياً.</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* ── الزر العائم للعمليات السريعة (FAB) ── */}
        <div className="fab-container">
          <div className={`fab-menu ${showFabMenu ? 'active' : ''}`}>
            {user?.role === 'admin' && (
              <>
                <button className="fab-item" onClick={() => { setShowFabMenu(false); setShowModal('building'); }} data-label="مبنى جديد">🏢</button>
                <button className="fab-item" onClick={() => { setShowFabMenu(false); setShowModal('room'); }} data-label="غرفة جديدة">🔑</button>
                <button className="fab-item" onClick={() => { setShowFabMenu(false); setShowModal('student'); }} data-label="تسكين طالب">👥</button>
              </>
            )}
            {(user?.role === 'delegate' || user?.role === 'admin') && (
              <button className="fab-item" onClick={() => { setShowFabMenu(false); setShowModal('invoice'); }} data-label="فاتورة جديدة">📝</button>
            )}
          </div>
          <button className="fab-button" onClick={() => setShowFabMenu(!showFabMenu)}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={showFabMenu ? 'rotate' : ''}>
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>
      </main>

      {/* ── 🔘 نافذة إضافة مبنى جديدة 🔘 ── */}
      {showModal === 'building' && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>إضافة مبنى سكن جديد</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <form onSubmit={handleAddBuilding}>
              <div className="form-group">
                <label>اسم المبنى</label>
                <input 
                  type="text" 
                  value={buildingForm.name} 
                  onChange={(e) => setBuildingForm({ ...buildingForm, name: e.target.value })}
                  placeholder="مثال: مبنى المهندسين أ" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>رمز المبنى (حرف واحد فريد)</label>
                <input 
                  type="text" 
                  value={buildingForm.code} 
                  onChange={(e) => setBuildingForm({ ...buildingForm, code: e.target.value.toUpperCase() })}
                  maxLength="1"
                  placeholder="مثال: A" 
                  required 
                />
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">حفظ المبنى</button>
                <button type="button" className="btn btn-dark" onClick={() => setShowModal(null)}>إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة إضافة غرفة جديدة 🔘 ── */}
      {showModal === 'room' && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>إضافة غرفة جديدة</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <form onSubmit={handleAddRoom}>
              <div className="form-group">
                <label>المبنى السكني</label>
                <select 
                  value={roomForm.building} 
                  onChange={(e) => setRoomForm({ ...roomForm, building: e.target.value })}
                  required
                >
                  <option value="">اختر المبنى...</option>
                  {buildings.map(b => (
                    <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>رقم الغرفة</label>
                <input 
                  type="number" 
                  value={roomForm.room_number} 
                  onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })}
                  placeholder="مثال: 105" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>رمز الـ QR المخصص (اختياري - يتم توليده تلقائياً إن ترك فارغاً)</label>
                <input 
                  type="text" 
                  value={roomForm.qr_code} 
                  onChange={(e) => setRoomForm({ ...roomForm, qr_code: e.target.value })}
                  placeholder="مثال: A-105" 
                />
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">حفظ الغرفة</button>
                <button type="button" className="btn btn-dark" onClick={() => setShowModal(null)}>إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة إضافة طالب جديدة 🔘 ── */}
      {showModal === 'student' && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>تسكين طالب جديد</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <form onSubmit={handleAddStudent}>
              <div className="form-group">
                <label>اسم الطالب الكامل</label>
                <input 
                  type="text" 
                  value={studentForm.name} 
                  onChange={(e) => setStudentForm({ ...studentForm, name: e.target.value })}
                  placeholder="مثال: محمد بن عبد العزيز" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>رقم هاتف الطالب</label>
                <input 
                  type="text" 
                  value={studentForm.phone} 
                  onChange={(e) => setStudentForm({ ...studentForm, phone: e.target.value })}
                  placeholder="مثال: +966500000000" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>الغرفة السكنية</label>
                <select 
                  value={studentForm.room} 
                  onChange={(e) => setStudentForm({ ...studentForm, room: e.target.value })}
                  required
                >
                  <option value="">اختر الغرفة للتسكين...</option>
                  {rooms.map(r => (
                    <option key={r.id} value={r.id}>{r.building_name} - غرفة {r.room_number}</option>
                  ))}
                </select>
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">تأكيد التسكين</button>
                <button type="button" className="btn btn-dark" onClick={() => setShowModal(null)}>إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة إضافة مستخدم جديدة 🔘 ── */}
      {showModal === 'user' && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>إنشاء حساب جديد للموظفين</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <form onSubmit={handleAddUser}>
              <div className="form-group">
                <label>اسم المستخدم (الدخول)</label>
                <input 
                  type="text" 
                  value={userForm.username} 
                  onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                  placeholder="مثال: delegate_2" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>كلمة المرور</label>
                <input 
                  type="password" 
                  value={userForm.password_hash} 
                  onChange={(e) => setUserForm({ ...userForm, password_hash: e.target.value })}
                  placeholder="أدخل كلمة المرور السرية" 
                  required 
                />
              </div>
              <div className="form-group">
                <label>الدور الوظيفي والصلاحية</label>
                <select 
                  value={userForm.role} 
                  onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  required
                >
                  <option value="delegate">ميداني / مندوب</option>
                  <option value="accountant">محاسب مالي</option>
                  <option value="admin">مشرف رئيسي</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">إنشاء الحساب</button>
                <button type="button" className="btn btn-dark" onClick={() => setShowModal(null)}>إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة إضافة فاتورة استهلاك جديدة 🔘 ── */}
      {showModal === 'invoice' && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>تسجيل قراءة العداد وإنشاء فاتورة</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <form onSubmit={handleAddInvoice}>
              <div className="form-group">
                <label>الغرفة السكنية</label>
                <select 
                  value={invoiceForm.room} 
                  onChange={(e) => setInvoiceForm({ ...invoiceForm, room: e.target.value })}
                  required
                >
                  <option value="">اختر الغرفة...</option>
                  {rooms.map(r => (
                    <option key={r.id} value={r.id}>{r.building_name} - غرفة {r.room_number} ({r.qr_code})</option>
                  ))}
                </select>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>القراءة السابقة (ك.و.س)</label>
                  <input 
                    type="number" 
                    step="0.01"
                    value={invoiceForm.reading_old} 
                    onChange={(e) => setInvoiceForm({ ...invoiceForm, reading_old: e.target.value })}
                    placeholder="مثال: 1205.50" 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>القراءة الحالية (ك.و.س)</label>
                  <input 
                    type="number" 
                    step="0.01"
                    value={invoiceForm.reading_new} 
                    onChange={(e) => setInvoiceForm({ ...invoiceForm, reading_new: e.target.value })}
                    placeholder="مثال: 1350.20" 
                    required 
                  />
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>سعر الكيلوواط (ريال)</label>
                  <input 
                    type="number" 
                    step="0.01"
                    value={invoiceForm.unit_price} 
                    onChange={(e) => setInvoiceForm({ ...invoiceForm, unit_price: e.target.value })}
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>الديون والتعثرات السابقة</label>
                  <input 
                    type="number" 
                    step="0.01"
                    value={invoiceForm.previous_debt} 
                    onChange={(e) => setInvoiceForm({ ...invoiceForm, previous_debt: e.target.value })}
                    required 
                  />
                </div>
              </div>

              <div className="form-group">
                <label>رابط صورة قراءة عداد الكهرباء (تم التحقق منها)</label>
                <input 
                  type="url" 
                  value={invoiceForm.meter_image_url} 
                  onChange={(e) => setInvoiceForm({ ...invoiceForm, meter_image_url: e.target.value })}
                  placeholder="مثال: https://images.unsplash.com/... (أو اتركها فارغة)" 
                />
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">تصدير الفاتورة</button>
                <button type="button" className="btn btn-dark" onClick={() => setShowModal(null)}>إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة ملصق QR كود للغرفة 🔘 ── */}
      {showModal === 'qr' && (
        <div className="modal-backdrop" onClick={() => setShowModal(null)}>
          <div className="modal-card qr-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>ملصق الباب الذكي - QR Code</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <div className="qr-container">
              <div className="qr-badge">
                <div className="qr-graphics" style={{ background: '#fff', padding: '16px', borderRadius: '12px' }}>
                  <QRCode value={`${window.location.origin}/payment/${activeQR}`} size={180} />
                </div>
                <h3>{activeQR}</h3>
                <p>امسح الرمز لتسجيل قراءة العداد فوراً</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => window.print()}>🖨️ طباعة ملصق الباب</button>
              <button className="btn btn-dark" onClick={() => setShowModal(null)}>إغلاق</button>
            </div>
          </div>
        </div>
      )}

      {/* ── 🔘 نافذة صورة العداد للتحقق 🔘 ── */}
      {showModal === 'image' && (
        <div className="modal-backdrop" onClick={() => setShowModal(null)}>
          <div className="modal-card image-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>صورة قراءة عداد الكهرباء للغرفة</h3>
              <button className="close-btn" onClick={() => setShowModal(null)}>×</button>
            </div>
            <div className="image-container">
              <img src={activeImage} alt="صورة عداد الاستهلاك" onError={(e) => {
                e.target.src = 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?q=80&w=600';
              }} />
            </div>
            <div className="modal-footer">
              <button className="btn btn-dark" onClick={() => setShowModal(null)}>إغلاق المعاينة</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
