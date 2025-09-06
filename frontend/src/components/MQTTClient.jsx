import { useEffect, useRef } from 'react'
import mqtt from 'mqtt'

const MQTTClient = ({ onMessage, onStatusChange }) => {
  const clientRef = useRef(null)

  useEffect(() => {
    // Only connect in live mode and when running locally
    const isLocal = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1'
    
    if (!isLocal) {
      onStatusChange('unavailable')
      return
    }

    onStatusChange('connecting')

    try {
      // Connect to MQTT broker via WebSocket
      const client = mqtt.connect('ws://localhost:9001', {
        clientId: `dashboard-${Math.random().toString(16).substr(2, 8)}`,
        clean: true,
        connectTimeout: 4000,
        reconnectPeriod: 1000,
      })

      clientRef.current = client

      client.on('connect', () => {
        console.log('MQTT connected')
        onStatusChange('connected')
        
        // Subscribe to building telemetry topics
        client.subscribe('building/+/+/telemetry', (err) => {
          if (err) {
            console.error('Failed to subscribe:', err)
          } else {
            console.log('Subscribed to building telemetry topics')
          }
        })
      })

      client.on('message', (topic, message) => {
        try {
          const data = JSON.parse(message.toString())
          console.log('MQTT message received:', topic, data)
          onMessage(data)
        } catch (error) {
          console.error('Failed to parse MQTT message:', error)
        }
      })

      client.on('error', (error) => {
        console.error('MQTT error:', error)
        onStatusChange('error')
      })

      client.on('close', () => {
        console.log('MQTT disconnected')
        onStatusChange('disconnected')
      })

      client.on('reconnect', () => {
        console.log('MQTT reconnecting')
        onStatusChange('connecting')
      })

    } catch (error) {
      console.error('Failed to create MQTT client:', error)
      onStatusChange('error')
    }

    // Cleanup on unmount
    return () => {
      if (clientRef.current) {
        clientRef.current.end()
      }
    }
  }, [onMessage, onStatusChange])

  // This component doesn't render anything
  return null
}

export default MQTTClient
