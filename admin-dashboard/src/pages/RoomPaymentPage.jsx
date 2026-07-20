import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import PaymentCountdown from '../components/PaymentCountdown';
import ElectronicPaymentForm from '../components/ElectronicPaymentForm';
import PricingTransparencyPanel from '../components/PricingTransparencyPanel';
import './RoomPaymentPage.css';

export default function RoomPaymentPage() {
  const { qrCode } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchInvoiceData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axiosClient.get(`/public/room/${qrCode}/invoice/`);
      if (res.data.success) {
        setData(res.data);
      } else {
        setError(res.data.message || 'حدث خطأ غير متوقع.');
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(err.response?.data?.message || 'الغرفة أو الفاتورة غير موجودة.');
      } else {
        setError('تعذر الاتصال بالخادم. حاول مجدداً.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (qrCode) {
      fetchInvoiceData();
    }
  }, [qrCode]);

  if (loading) {
    return (
      <div className="payment-page-container loading">
        <div className="spinner"></div>
        <p>جاري تحميل بيانات الفاتورة...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="payment-page-container error">
        <div className="error-icon">⚠️</div>
        <h2>عذراً</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!data || !data.invoice) return null;

  const { room, invoice } = data;
  const isPaid = invoice.status === 'paid';

  return (
    <div className="payment-page-container">
      <header className="payment-header">
        <div className="logo-icon">⚡</div>
        <h1>بوابة سداد الفواتير</h1>
        <p>نظام إدارة الفواتير الكهربائية للمباني</p>
      </header>

      <main className="payment-main">
        <PricingTransparencyPanel />

        <div className="invoice-card">
          <div className="invoice-header">
            <div>
              <h2>الفاتورة الحالية</h2>
              <p className="room-info">{room.building_name} - غرفة {room.room_number}</p>
            </div>
            {!isPaid && (
              <PaymentCountdown 
                payment_deadline={invoice.payment_deadline} 
                isOverdue={invoice.is_overdue} 
                overdueFine={invoice.overdue_fine} 
              />
            )}
            {isPaid && (
              <span className="badge badge-paid" style={{ alignSelf: 'center', padding: '8px 16px', fontSize: '14px' }}>✅ مسددة</span>
            )}
          </div>

          <div className="invoice-details">
            <div className="detail-item">
              <span className="label">تاريخ الفاتورة</span>
              <span className="value">{new Date(invoice.created_at).toLocaleDateString('ar-SA')}</span>
            </div>
            <div className="detail-item">
              <span className="label">القراءة القديمة</span>
              <span className="value">{invoice.reading_old} ك.و.س</span>
            </div>
            <div className="detail-item">
              <span className="label">القراءة الحالية</span>
              <span className="value">{invoice.reading_new} ك.و.س</span>
            </div>
            <div className="detail-item highlight">
              <span className="label">حجم الاستهلاك</span>
              <span className="value">{invoice.consumption} ك.و.س</span>
            </div>
            <div className="detail-item">
              <span className="label">الديون السابقة</span>
              <span className="value">{invoice.previous_debt} ريال</span>
            </div>
          </div>

          <div className="invoice-total">
            <h3>المبلغ المطلوب سداده</h3>
            <div className="total-amount">
              {parseFloat(invoice.final_amount) + parseFloat(invoice.overdue_fine || 0)} <small>ريال</small>
            </div>
          </div>

          {!isPaid && (
            <div className="payment-actions">
              <ElectronicPaymentForm 
                invoice={invoice} 
                onPaymentSuccess={fetchInvoiceData} 
              />
            </div>
          )}
        </div>
      </main>

      <footer className="payment-footer">
        <p>© 2026 جميع الحقوق محفوظة لجهة السكن</p>
      </footer>
    </div>
  );
}
