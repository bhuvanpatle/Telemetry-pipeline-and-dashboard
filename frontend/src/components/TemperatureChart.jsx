import { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const TemperatureChart = ({ data }) => {
  const chartRef = useRef()

  const chartData = {
    labels: data.slice(-20).map(point => 
      new Date(point.ts).toLocaleTimeString()
    ),
    datasets: [
      {
        label: 'Outside Temp (°C)',
        data: data.slice(-20).map(point => point.points?.outside_temp || 0),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.1
      },
      {
        label: 'Supply Temp (°C)',
        data: data.slice(-20).map(point => point.points?.supply_temp || 0),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.1
      },
      {
        label: 'Setpoint (°C)',
        data: data.slice(-20).map(point => point.points?.setpoint || 0),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderDash: [5, 5],
        tension: 0.1
      }
    ]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: false,
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Temperature (°C)'
        },
        min: 10,
        max: 35
      }
    }
  }

  return (
    <div className="chart-container">
      <h3>Temperature Control</h3>
      {data.length > 0 ? (
        <Line ref={chartRef} data={chartData} options={options} />
      ) : (
        <div className="loading">No temperature data available</div>
      )}
    </div>
  )
}

export default TemperatureChart
