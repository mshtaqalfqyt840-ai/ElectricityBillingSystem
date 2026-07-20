import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import './PricingTransparencyPanel.css';

export default function PricingTransparencyPanel() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await axiosClient.get('/settings/');
        if (res.data.success) {
          setSettings(res.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch system settings", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  if (loading) return <div className="transparency-panel loading">جاري تحميل إعدادات التسعير...</div>;
  if (!settings) return null;

  return (
    <div className="transparency-panel">
      <div className="transparency-header">
        <span className="transparency-icon">💡</span>
        <h4>شفافية التسعير</h4>
      </div>
      <div className="transparency-content">
        <div className="transparency-item">
          <span className="item-label">السعر الرسمي للكيلووات:</span>
          <span className="item-value">{parseFloat(settings.official_kwh_price).toFixed(2)} ريال/ك.و.س</span>
        </div>
        
        {parseFloat(settings.emergency_surcharge_min) > 0 && (
          <div className="transparency-item">
            <span className="item-label">الزيادة الطارئة:</span>
            <span className="item-value text-warning">
              {parseFloat(settings.emergency_surcharge_min).toFixed(2)} - {parseFloat(settings.emergency_surcharge_max).toFixed(2)} ريال
            </span>
          </div>
        )}

        <div className="transparency-item">
          <span className="item-label">رسوم الخدمة الثابتة:</span>
          <span className="item-value">{parseFloat(settings.service_fee).toFixed(2)} ريال</span>
        </div>
      </div>
      <div className="transparency-footer">
        <small>ℹ️ <strong>رسوم الخدمة الثابتة:</strong> تُغطي تكاليف صيانة العدادات الذكية، النظام الإلكتروني، وتكاليف الإدارة لضمان استمرارية الخدمة لك.</small>
      </div>
    </div>
  );
}
