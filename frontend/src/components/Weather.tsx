import { useEffect, useState } from 'react'

interface WeatherData {
  temp: number
  description: string
  icon: string
  windSpeed: number
  humidity: number
}

interface WeatherProps {
  lat: number
  lng: number
}

export function Weather({ lat, lng }: WeatherProps) {
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        setLoading(true)
        const apiKey = import.meta.env.VITE_OPENWEATHER_API_KEY
        const response = await fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lng}&appid=${apiKey}&units=imperial`
        )
        
        if (!response.ok) {
          throw new Error('Failed to fetch weather data')
        }

        const data = await response.json()
        setWeather({
          temp: Math.round(data.main.temp),
          description: data.weather[0].description,
          icon: data.weather[0].icon,
          windSpeed: Math.round(data.wind.speed),
          humidity: data.main.humidity
        })
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load weather')
        console.error('Weather fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchWeather()
    // Refresh weather every 10 minutes
    const interval = setInterval(fetchWeather, 600000)
    return () => clearInterval(interval)
  }, [lat, lng])

  if (loading) {
    return <div className="weather-card loading">Loading weather...</div>
  }

  if (error) {
    return <div className="weather-card error">{error}</div>
  }

  if (!weather) {
    return null
  }

  return (
    <div className="weather-card">
      <div className="weather-main">
        <img
          src={`https://openweathermap.org/img/wn/${weather.icon}@2x.png`}
          alt={weather.description}
          className="weather-icon"
        />
        <div className="weather-temp">{weather.temp}°F</div>
      </div>
      <div className="weather-details">
        <div className="weather-description">
          {weather.description.charAt(0).toUpperCase() + weather.description.slice(1)}
        </div>
        <div className="weather-stats">
          <span>Wind: {weather.windSpeed} mph</span>
          <span>Humidity: {weather.humidity}%</span>
        </div>
      </div>
    </div>
  )
}
