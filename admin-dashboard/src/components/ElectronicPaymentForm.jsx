import { useState } from 'react';
import axiosClient from '../api/axiosClient';
import './ElectronicPaymentForm.css';

export default function ElectronicPaymentForm({ invoice, onPaymentSuccess }) {
  const [transactionId, setTransactionId] = useState('');
  const [walletProvider, setWalletProvider] = useState('stc_pay');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!transactionId.trim()) {
      setStatus('error');
      setMessage('يرجى إدخال كود التحويل');
      return;
    }

    setStatus('loading');
    setMessage('');

    try {
      // The amount is calculated on the backend from invoice if needed, or we pass final_amount
      // Actually the view expects amount. Let's pass invoice.final_amount + invoice.overdue_fine
      const totalAmount = parseFloat(invoice.final_amount || 0) + parseFloat(invoice.overdue_fine || 0);
      
      const response = await axiosClient.post('/verify-transaction/', {
        transaction_id: transactionId,
        wallet_provider: walletProvider,
        room_id: invoice.room,
        amount: totalAmount,
      });

      if (response.data.success) {
        setStatus('success');
        setMessage('تم قبول السداد وتحديث حالة الفاتورة');
        if (onPaymentSuccess) {
          onPaymentSuccess();
        }
      } else {
        setStatus('error');
        setMessage(response.data.message || 'حدث خطأ غير معروف');
      }
    } catch (error) {
      setStatus('error');
      setMessage(error.response?.data?.message || 'كود المدخل غير صحيح أو مستخدم سابقاً');
    }
  };

  return (
    <div className="electronic-payment-form">
      <h4 className="epf-title">السداد الإلكتروني</h4>
      <form onSubmit={handleSubmit} className="epf-container">
        <select 
          className="epf-select"
          value={walletProvider}
          onChange={(e) => setWalletProvider(e.target.value)}
          disabled={status === 'loading' || status === 'success'}
        >
          <option value="stc_pay">STC Pay</option>
          <option value="urpay">urpay</option>
          <option value="alinma_pay">AlinmaPay</option>
        </select>
        
        <input 
          type="text" 
          placeholder="كود التحويل..." 
          className="epf-input"
          value={transactionId}
          onChange={(e) => setTransactionId(e.target.value)}
          disabled={status === 'loading' || status === 'success'}
        />

        <button 
          type="submit" 
          className="btn btn-primary btn-xs epf-submit"
          disabled={status === 'loading' || status === 'success'}
        >
          {status === 'loading' ? 'جاري التحقق...' : 'إرسال'}
        </button>
      </form>

      {message && (
        <div className={`epf-message ${status}`}>
          {message}
        </div>
      )}
    </div>
  );
}
