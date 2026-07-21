import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

export default function FloorPlanSection({ buildings }) {
  const [selectedBuilding, setSelectedBuilding] = useState(buildings[0]?.id || '');
  const [floorPlanData, setFloorPlanData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (buildings.length > 0 && !selectedBuilding) {
      setSelectedBuilding(buildings[0].id);
    }
  }, [buildings]);

  useEffect(() => {
    if (selectedBuilding) {
      fetchFloorPlan();
    }
  }, [selectedBuilding]);

  const fetchFloorPlan = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get(`/buildings/${selectedBuilding}/floor_plan/`);
      setFloorPlanData(res.data);
    } catch (err) {
      console.error(err);
      alert('خطأ في جلب بيانات الخريطة');
    }
    setLoading(false);
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'green': return '#10b981'; // Paid
      case 'red': return '#ef4444'; // Overdue / Unpaid
      case 'black': return '#1f2937'; // Disconnected
      default: return '#9ca3af'; // Gray (No Data)
    }
  };

  // Group rooms by floors based on the first digit of search_code if it's 3 digits, or generic logic
  // For simplicity, we just display them in a grid.
  return (
    <div className="floor-plan-section" style={{ padding: '20px', animation: 'fadeIn 0.5s ease-out' }}>
      <div className="header-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>الخريطة التفاعلية للمباني 🗺️</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label>اختر المبنى:</label>
          <select 
            value={selectedBuilding} 
            onChange={(e) => setSelectedBuilding(e.target.value)}
            className="input-field"
            style={{ padding: '8px', minWidth: '150px' }}
          >
            {buildings.map(b => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', background: 'var(--surface)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><div style={{ width: '15px', height: '15px', background: '#10b981', borderRadius: '3px' }}></div> مسدد</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><div style={{ width: '15px', height: '15px', background: '#ef4444', borderRadius: '3px' }}></div> متأخر / مستحق</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><div style={{ width: '15px', height: '15px', background: '#1f2937', borderRadius: '3px' }}></div> مفصول</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><div style={{ width: '15px', height: '15px', background: '#9ca3af', borderRadius: '3px' }}></div> غير محدد</div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>جارٍ تحميل الخريطة التفاعلية...</div>
      ) : floorPlanData ? (
        <div className="rooms-grid" style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', 
          gap: '15px' 
        }}>
          {floorPlanData.rooms.map(room => (
            <div 
              key={room.id}
              className="room-box"
              style={{
                background: getStatusColor(room.status),
                color: '#fff',
                padding: '15px',
                borderRadius: '8px',
                textAlign: 'center',
                position: 'relative',
                cursor: 'pointer',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                transition: 'transform 0.2s'
              }}
              title={`الطالب: ${room.student_name}\nالاستهلاك: ${room.consumption} KWh\nالمطلوب: ${room.amount_due} ريال`}
              onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
              onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <div style={{ fontSize: '1.2em', fontWeight: 'bold' }}>{room.search_code}</div>
              <div style={{ fontSize: '0.8em', marginTop: '5px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {room.student_name}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '50px' }}>لا توجد بيانات متاحة لهذا المبنى.</div>
      )}
    </div>
  );
}
