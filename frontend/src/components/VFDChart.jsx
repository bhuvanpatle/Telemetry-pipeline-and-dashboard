import { useRef } from 'react'
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

const VFDChart = ({ data }) => {
  const chartRef = useRef()

  const chartData = {
    labels: data.slice(-20).map(point => 
      new Date(point.ts).toLocaleTimeString()
    ),
    datasets: [
      {
        label: 'VFD Speed (%)',
        data: data.slice(-20).map(point => point.points?.vfd_speed || 0),
        borderColor: 'rgb(153, 102, 255)',
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        tension: 0.1,
        fill: true
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
          text: 'Speed (%)'
        },
        min: 0,
        max: 100
      }
    }
  }

  return (
    <div className="chart-container">
      <h3>Fan Speed (VFD)</h3>
      {data.length > 0 ? (
        <Line ref={chartRef} data={chartData} options={options} />
      ) : (
        <div className="loading">No VFD data available</div>
      )}
    </div>
  )
}

export default VFDChart
