const AlarmList = ({ alarms }) => {
  const getSeverityClass = (severity) => {
    switch (severity) {
      case 'critical': return 'critical'
      case 'warning': return 'warning'
      case 'info': return 'info'
      default: return 'warning'
    }
  }

  return (
    <div className="alarm-list">
      <h3>Active Alarms ({alarms.length})</h3>
      {alarms.length === 0 ? (
        <div style={{ color: '#28a745', fontStyle: 'italic' }}>
          No active alarms
        </div>
      ) : (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {alarms.map(alarm => (
            <div 
              key={alarm.id} 
              className={`alarm-item ${getSeverityClass(alarm.severity)}`}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <strong>{alarm.message}</strong>
                  <div style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>
                    {alarm.building} / {alarm.device}
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: '#666', textAlign: 'right' }}>
                  {alarm.timestamp.toLocaleString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AlarmList
