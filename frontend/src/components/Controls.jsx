import { useState } from 'react'
import axios from 'axios'

const Controls = ({ mode, onDownloadCSV, hasData }) => {
  const [replayStatus, setReplayStatus] = useState('stopped')
  const [isLoading, setIsLoading] = useState(false)

  const startReplay = async () => {
    setIsLoading(true)
    try {
      const response = await axios.post('http://localhost:8000/replay/start', null, {
        params: {
          file_path: 'replay/samples/sample_electricity.csv',
          speed: 10.0
        }
      })
      setReplayStatus('running')
      console.log('Replay started:', response.data)
    } catch (error) {
      console.error('Failed to start replay:', error)
      alert('Failed to start replay. Make sure the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const stopReplay = async () => {
    setIsLoading(true)
    try {
      const response = await axios.post('http://localhost:8000/replay/stop')
      setReplayStatus('stopped')
      console.log('Replay stopped:', response.data)
    } catch (error) {
      console.error('Failed to stop replay:', error)
      alert('Failed to stop replay. Make sure the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const checkReplayStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/replay/status')
      setReplayStatus(response.data.status)
    } catch (error) {
      console.error('Failed to check replay status:', error)
    }
  }

  return (
    <div className="controls">
      <h3 style={{ margin: 0, marginRight: '20px' }}>Controls</h3>
      
      <button 
        className="success"
        onClick={onDownloadCSV}
        disabled={!hasData}
      >
        📥 Download CSV
      </button>

      {mode === 'live' && (
        <>
          <button 
            className="primary"
            onClick={startReplay}
            disabled={isLoading || replayStatus === 'running'}
          >
            {isLoading ? '⏳' : '▶️'} Start Replay
          </button>

          <button 
            className="danger"
            onClick={stopReplay}
            disabled={isLoading || replayStatus === 'stopped'}
          >
            {isLoading ? '⏳' : '⏹️'} Stop Replay
          </button>

          <button 
            className="secondary"
            onClick={checkReplayStatus}
            disabled={isLoading}
          >
            🔄 Check Status
          </button>

          <div style={{ 
            padding: '8px 12px', 
            border: '1px solid #ddd', 
            borderRadius: '4px',
            background: replayStatus === 'running' ? '#d4edda' : '#f8f9fa'
          }}>
            Replay: {replayStatus}
          </div>
        </>
      )}

      {mode === 'demo' && (
        <div style={{ 
          padding: '8px 12px', 
          border: '1px solid #ddd', 
          borderRadius: '4px',
          background: '#fff3cd',
          color: '#856404'
        }}>
          🎭 Demo Mode - Simulated data
        </div>
      )}
    </div>
  )
}

export default Controls
