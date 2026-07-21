import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReload = () => {
    // نمسح الكاش ونعيد التحميل
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.replace('/login');
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          color: '#e2e8f0',
          fontFamily: 'Tajawal, sans-serif',
          padding: '20px',
          textAlign: 'center',
          direction: 'rtl',
        }}>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '40px',
            maxWidth: '500px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.1)',
          }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>⚡</div>
            <h2 style={{ fontSize: '24px', marginBottom: '12px', color: '#f59e0b' }}>
              حدث خطأ غير متوقع
            </h2>
            <p style={{ fontSize: '16px', marginBottom: '24px', color: '#94a3b8' }}>
              لا تقلق! يمكنك إعادة تحميل الصفحة لحل المشكلة.
            </p>
            <button
              onClick={this.handleReload}
              style={{
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                color: '#fff',
                border: 'none',
                padding: '12px 32px',
                borderRadius: '10px',
                fontSize: '16px',
                cursor: 'pointer',
                fontFamily: 'Tajawal, sans-serif',
                fontWeight: '700',
                transition: 'transform 0.2s',
              }}
              onMouseOver={(e) => e.target.style.transform = 'scale(1.05)'}
              onMouseOut={(e) => e.target.style.transform = 'scale(1)'}
            >
              🔄 إعادة تحميل
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
