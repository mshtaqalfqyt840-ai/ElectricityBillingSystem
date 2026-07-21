import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

export default function ReportsSection({ width }) {
  const [reportData, setReportData] = useState(null);
  const [periodType, setPeriodType] = useState('month');
  const [loading, setLoading] = useState(false);
  
  // Expenses form state
  const [expenses, setExpenses] = useState({
    expense_station_admin: 0,
    expense_maintenance: 0,
    expense_electricity_committee: 0,
    expense_student_committee: 0,
    expense_other_debts: 0
  });

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/archive-reports/current_summary/');
      setReportData(res.data);
    } catch (err) {
      console.error(err);
      alert('خطأ في جلب بيانات التقرير الحالي');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleExpenseChange = (e) => {
    setExpenses({
      ...expenses,
      [e.target.name]: parseFloat(e.target.value) || 0
    });
  };

  const handleArchive = async () => {
    if (!window.confirm("هل أنت متأكد من ترحيل هذا التقرير وإغلاق الفترة الحالية؟ هذه العملية لا يمكن التراجع عنها وسيتم تصفير المبالغ المعلقة للفترة القادمة.")) return;
    
    try {
      const payload = {
        period_type: periodType,
        total_kwh_consumption: reportData.total_kwh_consumption,
        total_amount_due: reportData.total_amount_due,
        total_service_fees: reportData.total_service_fees,
        total_paid: reportData.total_paid,
        remaining_balance: reportData.remaining_balance,
        net_balance: reportData.net_balance,
        ...expenses
      };
      
      await axiosClient.post('/archive-reports/', payload);
      alert("تم ترحيل التقرير بنجاح!");
      // Reset after archive
      fetchSummary();
      setExpenses({
        expense_station_admin: 0,
        expense_maintenance: 0,
        expense_electricity_committee: 0,
        expense_student_committee: 0,
        expense_other_debts: 0
      });
    } catch (err) {
      console.error(err);
      alert("حدث خطأ أثناء محاولة الترحيل");
    }
  };

  const printReport = () => {
    window.print();
  };

  if (loading || !reportData) {
    return <div style={{ padding: '20px' }}>جارٍ التحميل...</div>;
  }

  // Calculate some derived totals
  const totalExpenses = expenses.expense_station_admin + expenses.expense_maintenance + 
                        expenses.expense_electricity_committee + expenses.expense_student_committee + 
                        expenses.expense_other_debts;
  const netAfterExpenses = parseFloat(reportData.total_paid) - totalExpenses;

  return (
    <div className="reports-section" style={{ padding: '20px', animation: 'fadeIn 0.5s ease-out' }}>
      <div className="header-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>التقارير والأرشيف</h2>
        <div>
          <button onClick={printReport} className="btn btn-secondary" style={{ marginLeft: '10px' }}>طباعة التقرير</button>
          <button onClick={handleArchive} className="btn btn-primary" style={{ background: '#f59e0b', borderColor: '#f59e0b' }}>
            ترحيل التقرير / أرشفة الفترة
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        {/* ملخص استهلاك واشتراكات الطلاب */}
        <div className="card report-card print-section" style={{ flex: '1', minWidth: '300px', background: 'var(--surface)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <h3 style={{ borderBottom: '2px solid var(--primary)', paddingBottom: '10px', marginBottom: '15px' }}>تقرير النظام للجنة الكهرباء</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label>نوع الفترة: </label>
            <select value={periodType} onChange={e => setPeriodType(e.target.value)} style={{ padding: '5px', borderRadius: '4px' }}>
              <option value="half_month">نصف شهري</option>
              <option value="month">شهري</option>
              <option value="year">سنوي</option>
            </select>
          </div>

          <table className="table" style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
            <tbody>
              <tr>
                <td style={{ background: 'var(--bg)', padding: '10px', fontWeight: 'bold' }}>استهلاك الكهرباء (KWh)</td>
                <td style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold', color: 'var(--text)' }}>{parseFloat(reportData.total_kwh_consumption).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ background: 'var(--bg)', padding: '10px', fontWeight: 'bold' }}>المبلغ المستحق</td>
                <td style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold', color: 'var(--text)' }}>{parseFloat(reportData.total_amount_due).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ background: 'var(--bg)', padding: '10px', fontWeight: 'bold' }}>رسوم الخدمات</td>
                <td style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold', color: 'var(--text)' }}>{parseFloat(reportData.total_service_fees).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ background: 'var(--bg)', padding: '10px', fontWeight: 'bold' }}>المبلغ المدفوع / التحصيل</td>
                <td style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold', color: '#10b981' }}>{parseFloat(reportData.total_paid).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ background: 'var(--bg)', padding: '10px', fontWeight: 'bold' }}>المتبقي / الديون (المستقرات)</td>
                <td style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold', color: '#ef4444' }}>{parseFloat(reportData.remaining_balance).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* جدول المصروفات والخدمات التفصيلي */}
        <div className="card report-card print-section" style={{ flex: '1', minWidth: '300px', background: 'var(--surface)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <h3 style={{ borderBottom: '2px solid var(--primary)', paddingBottom: '10px', marginBottom: '15px' }}>تقرير السكن المالي للجنة الكهرباء (مصروفات)</h3>
          
          <div className="form-group" style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ flex: '1' }}>حساب المحطة / الإدارة:</label>
            <input type="number" name="expense_station_admin" value={expenses.expense_station_admin || ''} onChange={handleExpenseChange} style={{ flex: '1', padding: '8px' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ flex: '1' }}>أجور صيانة:</label>
            <input type="number" name="expense_maintenance" value={expenses.expense_maintenance || ''} onChange={handleExpenseChange} style={{ flex: '1', padding: '8px' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ flex: '1' }}>حساب لجنة الكهرباء:</label>
            <input type="number" name="expense_electricity_committee" value={expenses.expense_electricity_committee || ''} onChange={handleExpenseChange} style={{ flex: '1', padding: '8px' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ flex: '1' }}>لجنة طلابية / مناديب:</label>
            <input type="number" name="expense_student_committee" value={expenses.expense_student_committee || ''} onChange={handleExpenseChange} style={{ flex: '1', padding: '8px' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ flex: '1' }}>سداد ديون أخرى:</label>
            <input type="number" name="expense_other_debts" value={expenses.expense_other_debts || ''} onChange={handleExpenseChange} style={{ flex: '1', padding: '8px' }} />
          </div>

          <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid var(--primary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <strong>إجمالي المصروفات:</strong>
              <strong style={{ color: '#ef4444' }}>{totalExpenses.toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>صافي الباقي للسكن:</strong>
              <strong style={{ color: netAfterExpenses >= 0 ? '#10b981' : '#ef4444' }}>{netAfterExpenses.toFixed(2)}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
