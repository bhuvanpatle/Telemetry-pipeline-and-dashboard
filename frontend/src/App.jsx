import { useState, useEffect } from 'react'
import TemperatureChart from './components/TemperatureChart'
import VFDChart from './components/VFDChart'
import AlarmList from './components/AlarmList'
import Controls from './components/Controls'
import MQTTClient from './components/MQTTClient'
import demoData from './data/demoData.json'

function App() {
  const [mode, setMode] = useState('demo') // 'live' or 'demo'
  const [telemetryData, setTelemetryData] = useState([])
  const [alarms, setAlarms] = useState([])
  const [mqttStatus, setMqttStatus] = useState('disconnected')
  const [lastUpdate, setLastUpdate] = useState(null)

  // Handle new telemetry data
  const handleTelemetryUpdate = (data) => {
    setTelemetryData(prev => {
      const newData = [...prev, data].slice(-100) // Keep last 100 points
      return newData
    })
    setLastUpdate(new Date())

    // Check for alarms
    if (data.points && data.points.alarm) {
      const newAlarm = {
        id: Date.now(),
        timestamp: new Date(data.ts),
        device: data.device,
        building: data.building,
        message: data.points.alarm,
        severity: 'warning'
      }
      setAlarms(prev => [newAlarm, ...prev.slice(0, 19)]) // Keep last 20 alarms
    }
  }

  // Initialize demo data
  useEffect(() => {
    if (mode === 'demo') {
      setTelemetryData(demoData.telemetry || [])
      setAlarms(demoData.alarms || [])
      setMqttStatus('disconnected')
    } else {
      setTelemetryData([])
      setAlarms([])
    }
  }, [mode])

  // Generate demo data periodically in demo mode
  useEffect(() => {
    if (mode === 'demo') {
      const interval = setInterval(() => {
        const now = Date.now()
        const demoPoint = {
          ts: now,
          device: 'ahu1',
          building: 'demo_building',
          points: {
            outside_temp: 20 + Math.sin(now / 60000) * 5 + Math.random() * 2,
            supply_temp: 18 + Math.random() * 2,
            setpoint: 18.0,
            vfd_speed: 50 + Math.random() * 30,
            fan_status: 'ON',
            alarm: Math.random() < 0.05 ? 'High Temperature' : null
          }
        }
        handleTelemetryUpdate(demoPoint)
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [mode])

  const downloadCSV = () => {
    if (telemetryData.length === 0) return

    const csvHeader = 'timestamp,device,building,outside_temp,supply_temp,setpoint,vfd_speed,fan_status,alarm\\n'
    const csvData = telemetryData.map(point => {
      const p = point.points || {}
      return [
        new Date(point.ts).toISOString(),
        point.device || '',
        point.building || '',
        p.outside_temp || '',
        p.supply_temp || '',
        p.setpoint || '',
        p.vfd_speed || '',
        p.fan_status || '',
        p.alarm || ''
      ].join(',')
    }).join('\\n')

    const blob = new Blob([csvHeader + csvData], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `telemetry_data_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Building Telemetry Dashboard</h1>
        <div className="mode-toggle">
          <span>Mode:</span>
          <button 
            className={mode === 'demo' ? 'active' : ''} 
            onClick={() => setMode('demo')}
          >
            Demo
          </button>
          <button 
            className={mode === 'live' ? 'active' : ''} 
            onClick={() => setMode('live')}
          >
            Live
          </button>
          <div style={{ marginLeft: '20px', display: 'flex', alignItems: 'center' }}>
            <span 
              className={`status-indicator ${mqttStatus}`}
            ></span>
            <span>MQTT: {mqttStatus}</span>
          </div>
          {lastUpdate && (
            <div style={{ marginLeft: '20px', fontSize: '14px', color: '#666' }}>
              Last update: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
        </div>
      </header>

      {mode === 'live' && (
        <MQTTClient 
          onMessage={handleTelemetryUpdate}
          onStatusChange={setMqttStatus}
        />
      )}

      <div className="dashboard-grid">
        <TemperatureChart data={telemetryData} />
        <VFDChart data={telemetryData} />
      </div>

      <AlarmList alarms={alarms} />

      <Controls 
        mode={mode}
        onDownloadCSV={downloadCSV}
        hasData={telemetryData.length > 0}
      />
    </div>
  )
}

export default App
