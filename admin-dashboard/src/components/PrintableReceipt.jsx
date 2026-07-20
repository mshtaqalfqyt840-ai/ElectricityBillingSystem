import React from 'react';
import './PrintableReceipt.css';

/**
 * PrintableReceipt Component
 * 
 * @param {Object} invoice - The invoice object containing reading and price data
 * @param {String} type - "invoice" (فاتورة الكهرباء) or "receipt" (سند قبض نقدي)
 */
const PrintableReceipt = React.forwardRef(({ invoice, type = 'invoice' }, ref) => {
  if (!invoice) return null;

  // Format date to locale string or use raw if already formatted
  const formattedDate = invoice.created_at 
    ? new Date(invoice.created_at).toLocaleDateString('en-GB') // DD/MM/YYYY
    : new Date().toLocaleDateString('en-GB');

  // Helper to extract building and floor from room QR/number
  // e.g. room "A-150" or "150". 1st digit is floor, remaining is room, A is building.
  let building = '-';
  let roomNumber = invoice.room_qr || '-';
  let floor = '-';

  if (roomNumber.includes('-')) {
    const parts = roomNumber.split('-');
    building = parts[0];
    roomNumber = parts[1];
  }
  
  if (roomNumber.length >= 3) {
    floor = roomNumber.charAt(0);
  }

  // Calculate fields
  const invoiceNumber = invoice.id ? invoice.id.toString().padStart(5, '0') : '00000';
  // If we don't have separate service_fee/price_per_kwh in invoice object natively mapped yet, we do fallback calculation.
  // Generally: final_amount = (consumption * price) + service_fee + previous_debt + overdue_fine
  // We will try to map existing fields or use 0
  const consumption = parseFloat(invoice.consumption) || 0;
  const oldReading = parseFloat(invoice.reading_old) || 0;
  const newReading = parseFloat(invoice.reading_new) || 0;
  const previousDebt = parseFloat(invoice.previous_debt) || 0;
  const serviceFee = 300; // Default service fee commonly used
  const totalAmount = parseFloat(invoice.final_amount) || 0;
  
  // Calculate Due Amount (Consumption * Price)
  // We subtract service fee and previous debt from final amount to get pure due amount
  const dueAmount = totalAmount - serviceFee - previousDebt;

  return (
    <div className="printable-container" ref={ref}>
      {type === 'invoice' ? (
        // ── تصميم فاتورة الكهرباء (Unpaid) ──
        <div className="receipt-paper invoice-paper">
          <div className="receipt-header">
            <div className="header-info">
              <p>رقم الفاتورة: <strong className="red-text">{invoiceNumber}</strong></p>
              <p>التاريخ: <strong>{formattedDate}</strong></p>
            </div>
            <div className="header-title">
              <h2>فاتورة الكهرباء</h2>
            </div>
            <div className="header-logo-placeholder"></div>
          </div>

          <div className="delegate-info">
            <p>اسم مندوب الغرفة: ..............................................................</p>
          </div>

          <table className="receipt-table">
            <thead>
              <tr>
                <th>المبنى</th>
                <th>رقم الغرفة</th>
                <th>القراءة السابقة</th>
                <th>القراءة الحالية</th>
                <th>فارق القراءة</th>
                <th>المبلغ المستحق</th>
                <th>رسوم الخدمات</th>
                <th>الرصيد</th>
                <th>الإجمالي</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{building}</td>
                <td>{roomNumber}</td>
                <td>{oldReading}</td>
                <td>{newReading}</td>
                <td>{consumption}</td>
                <td>{dueAmount > 0 ? dueAmount.toLocaleString() : 0}</td>
                <td>{serviceFee}</td>
                <td>{previousDebt > 0 ? previousDebt : 0}</td>
                <td><strong>{totalAmount.toLocaleString()}</strong></td>
              </tr>
            </tbody>
          </table>

          <div className="receipt-footer">
            <p>يجب سداد فاتورة الكهرباء خلال أقصاها ثلاثة أيام ابتداء من تاريخ صدورها.</p>
            <p>التأخير في سداد فاتورة الكهرباء يعرضك لفصل التيار عن الغرفة.</p>
            <p>لا يتم تسديد أي مبلغ إلا بسند قبض رسمي صادر عن لجنة الكهرباء.</p>
          </div>
        </div>
      ) : (
        // ── تصميم سند قبض نقدي (Paid) ──
        <div className="receipt-paper cash-receipt-paper">
          <div className="cash-receipt-header">
            <div className="cash-receipt-info">
              <p>رقم السند: <strong className="red-text">{invoiceNumber}</strong></p>
              <p>التاريخ: <strong>{formattedDate}</strong></p>
              <p>فاتورة شهر: <strong>{new Date(invoice.created_at || new Date()).toLocaleDateString('ar-SA', { month: 'long' })}</strong></p>
            </div>
            <div className="cash-receipt-title">
              <h2>سند قبض نقدي</h2>
            </div>
            <div className="cash-receipt-logo">
              <span className="logo-icon">⚡</span>
            </div>
          </div>

          <div className="cash-receipt-body">
            <div className="cash-section">
              <table className="cash-table">
                <tbody>
                  <tr>
                    <td>اسم مندوب الغرفة</td>
                    <td>............................................</td>
                  </tr>
                  <tr>
                    <td>رقم الغرفة</td>
                    <td><strong>{roomNumber}</strong></td>
                  </tr>
                  <tr>
                    <td>الدور</td>
                    <td>{floor}</td>
                  </tr>
                  <tr>
                    <td>المبنى</td>
                    <td>{building}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="cash-section">
              <table className="cash-table">
                <tbody>
                  <tr>
                    <td>الإجمالي على الغرفة</td>
                    <td>{totalAmount.toLocaleString()}</td>
                  </tr>
                  <tr>
                    <td>المبلغ المدفوع</td>
                    <td><strong>{totalAmount.toLocaleString()}</strong></td>
                  </tr>
                  <tr>
                    <td>المبلغ المتبقي</td>
                    <td>0</td>
                  </tr>
                  <tr>
                    <td>الملاحظات</td>
                    <td>............................................</td>
                  </tr>
                  <tr>
                    <td>اسم المحصل</td>
                    <td>{invoice.approved_by_username || '.........................'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="cash-receipt-footer">
            <p>يلزم التسجيل في رابط استمارة الكهرباء على قناة اللجنة الطلابية لجنة الكهرباء</p>
          </div>
        </div>
      )}
    </div>
  );
});

export default PrintableReceipt;
