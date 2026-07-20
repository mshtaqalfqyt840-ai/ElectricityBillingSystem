import { useState, useEffect } from 'react';
import './PaymentCountdown.css';

/**
 * PaymentCountdown — عداد تنازلي حي لمهلة سداد الفاتورة.
 *
 * Props:
 *   payment_deadline {string}  — تاريخ ووقت نهاية المهلة بتنسيق ISO من الـ API
 *   isOverdue        {boolean} — هل الفاتورة متأخرة فعلاً (من is_overdue)
 *   overdueFine      {number}  — قيمة الغرامة المطبقة (من overdue_fine)
 */
export default function PaymentCountdown({ payment_deadline, isOverdue, overdueFine }) {
  const [timeLeft, setTimeLeft] = useState(null);

  useEffect(() => {
    if (!payment_deadline) return;
    const deadlineMs = new Date(payment_deadline).getTime();

    const tick = () => {
      const diff = deadlineMs - Date.now();
      setTimeLeft(diff);
    };

    tick(); // تشغيل فوري بدون انتظار الثانية الأولى
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [payment_deadline]);

  // حالة الفاتورة المتأخرة (محدَّثة من الـ API أو محسوبة محلياً)
  if (isOverdue || (timeLeft !== null && timeLeft <= 0)) {
    return (
      <div className="countdown-badge overdue">
        <span className="countdown-icon">⛔</span>
        <span className="countdown-label-overdue">انتهت مهلة السداد</span>
        {overdueFine > 0 && (
          <span className="countdown-fine">غرامة: {Number(overdueFine).toFixed(2)} ريال</span>
        )}
      </div>
    );
  }

  if (timeLeft === null) return null;

  const totalSeconds = Math.floor(timeLeft / 1000);
  const hours        = Math.floor(totalSeconds / 3600);
  const minutes      = Math.floor((totalSeconds % 3600) / 60);
  const seconds      = totalSeconds % 60;

  const isUrgent = hours < 5; // أقل من 5 ساعات → تحذير أحمر

  const pad = (n) => String(n).padStart(2, '0');

  return (
    <div className={`countdown-badge ${isUrgent ? 'urgent' : 'normal'}`}>
      {isUrgent && (
        <span className="countdown-warning">⚠️ اقتربت المهلة!</span>
      )}
      <div className="countdown-display">
        <div className="countdown-unit">
          <span className="countdown-value">{pad(hours)}</span>
          <span className="countdown-unit-label">ساعة</span>
        </div>
        <span className="countdown-sep">:</span>
        <div className="countdown-unit">
          <span className="countdown-value">{pad(minutes)}</span>
          <span className="countdown-unit-label">دقيقة</span>
        </div>
        <span className="countdown-sep">:</span>
        <div className="countdown-unit">
          <span className="countdown-value">{pad(seconds)}</span>
          <span className="countdown-unit-label">ثانية</span>
        </div>
      </div>
    </div>
  );
}
