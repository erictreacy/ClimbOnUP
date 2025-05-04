import { useEffect, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { Weather } from './components/Weather'
import { RouteList } from './components/RouteList'
import './App.css'

// Your Mapbox token from environment variable
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

// Add some global styles
const globalStyles = document.createElement('style');
globalStyles.innerHTML = `
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
  * { box-sizing: border-box; }
`;
document.head.appendChild(globalStyles);

interface Photo {
  url: string;
  caption: string;
}

interface Route {
  id: number;
  area_id: number;
  name: string;
  grade: string;
  type: string;
  height: string;
  pitches: number;
  first_ascent: string;
  description: string;
  protection: string;
  latitude: number | null;
  longitude: number | null;
  location_description: string;
  url: string;
  photos: Photo[];
}

interface ClimbingArea {
  id: number
  name: string
  url: string
  description: string
  latitude: number | null
  longitude: number | null
  type: string | null
  elevation: string | null
  season: string
  approach_time: string
  parent_area_id: string
  route_count: number
  routes?: Route[]
}

function App() {
  const [areas, setAreas] = useState<ClimbingArea[]>([])
  const [routes, setRoutes] = useState<Route[]>([])
  const [selectedArea, setSelectedArea] = useState<ClimbingArea | null>(null)
  const [expandedAreas, setExpandedAreas] = useState<Set<number>>(new Set())
  const [map, setMap] = useState<mapboxgl.Map | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Removed unused userLocation state

  useEffect(() => {
    // Load climbing areas data
    setIsLoading(true)
    fetch('climbing_data.json')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load climbing data')
        return res.json()
      })
      .then(data => {
        if (data.areas && Array.isArray(data.areas) && data.routes && Array.isArray(data.routes)) {
          // Associate routes with their areas
          const areasWithRoutes = data.areas.map((area: ClimbingArea) => ({
            ...area,
            routes: data.routes.filter((route: Route) => route.area_id === area.id)
          }))
          setAreas(areasWithRoutes)
          setRoutes(data.routes)
          console.log('Loaded', data.areas.length, 'climbing areas with', data.routes.length, 'routes')
          setError(null)
        } else {
          throw new Error('Invalid data format')
        }
      })
      .catch(err => {
        console.error('Error loading climbing data:', err)
        setError(err.message)
      })
      .finally(() => setIsLoading(false))

    // Initialize map
    const mapInstance = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/mapbox/outdoors-v11',
      center: [-87.4, 46.5], // Approximate center of UP Michigan
      zoom: 8
    })

    setMap(mapInstance)

    return () => mapInstance.remove()
  }, [])

  // Add markers when areas data is loaded
  useEffect(() => {
    if (!map || !areas.length) return

    // Clear existing markers if any
    const markers: mapboxgl.Marker[] = [];
    const bounds = new mapboxgl.LngLatBounds();
    
    areas.forEach(area => {
      if (area.latitude && area.longitude && area.name !== 'Printer-Friendly') {
        // Create marker element
        const el = document.createElement('div');
        el.className = 'marker';
        el.style.width = '25px';
        el.style.height = '25px';
        el.style.backgroundImage = 'url(/marker.svg)';
        el.style.backgroundSize = 'cover';
        el.style.cursor = 'pointer';

        // Create and store the marker
        const marker = new mapboxgl.Marker(el)
          .setLngLat([area.longitude, area.latitude])
          .setPopup(
            new mapboxgl.Popup({ offset: 25 })
              .setHTML(`<h3>${area.name}</h3>${area.type ? `<p>Type: ${area.type}</p>` : ''}`)
          )
          .addTo(map);

        markers.push(marker);
        bounds.extend([area.longitude, area.latitude]);
      }
    });
    
    // Fit map to bounds with padding
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, {
        padding: { top: 50, bottom: 50, left: 350, right: 50 },
        maxZoom: 12
      });
    }
    
    // Cleanup markers when component unmounts
    return () => markers.forEach(marker => marker.remove());
  }, [map, areas, routes]);

  const handleAreaClick = (area: ClimbingArea) => {
    setExpandedAreas(prev => {
      const newSet = new Set(prev)
      if (newSet.has(area.id)) {
        newSet.delete(area.id)
      } else {
        newSet.add(area.id)
      }
      return newSet
    })
    setSelectedArea(area)
    if (map && area.latitude && area.longitude) {
      map.flyTo({
        center: [area.longitude, area.latitude],
        zoom: 12
      })
    }
  }

  const handleLocationClick = () => {
    if (!map) return

    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords
          // Just fly to location, no need to store it
          map.flyTo({
            center: [longitude, latitude],
            zoom: 12
          })

          // Remove existing user location marker if any
          const existingMarker = document.querySelector('.user-location-marker')
          if (existingMarker) {
            existingMarker.remove()
          }

          // Add user location marker
          const el = document.createElement('div')
          el.className = 'user-location-marker'
          el.style.width = '20px'
          el.style.height = '20px'
          el.style.borderRadius = '50%'
          el.style.backgroundColor = '#007aff'
          el.style.border = '3px solid white'
          el.style.boxShadow = '0 0 0 2px rgba(0,122,255,0.3)'

          new mapboxgl.Marker(el)
            .setLngLat([longitude, latitude])
            .setPopup(new mapboxgl.Popup().setHTML('You are here'))
            .addTo(map)
        },
        (error) => {
          console.error('Error getting location:', error)
          setError('Could not get your location')
        }
      )
    } else {
      setError('Geolocation is not supported by your browser')
    }
  }

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>UP Climbing Areas</h1>
        {isLoading && <div className="loading-message">Loading climbing areas...</div>}
        {error && <div className="error-message">{error}</div>}
        {!isLoading && !error && areas.length === 0 && (
          <div className="empty-message">No climbing areas found</div>
        )}
        {areas.map(area => (
          <div key={area.id}>
            <button
              className={`area-card ${selectedArea?.id === area.id ? 'selected' : ''} ${expandedAreas.has(area.id) ? 'expanded' : ''}`}
              onClick={() => handleAreaClick(area)}
            >
              <h3>{area.name}</h3>
              <span className="route-count">
                ({area.route_count || 0})
              </span>
            </button>
            {expandedAreas.has(area.id) && (
              <div className="area-details">
                {area.type && <p>Type: {area.type}</p>}
                {area.elevation && <p>Elevation: {area.elevation}</p>}
                {area.season && <p>Season: {area.season}</p>}
                {area.approach_time && <p>Approach: {area.approach_time}</p>}
                {area.latitude && area.longitude && (
                  <Weather lat={area.latitude} lng={area.longitude} />
                )}
                <RouteList routes={routes} areaId={area.id} />
              </div>
            )}
          </div>
        ))}
      </div>
      <div id="map" style={{ flex: 1 }} />
      <button
        className="location-button"
        onClick={handleLocationClick}
        title="Find my location"
      >
        📍
      </button>
    </div>
  )
}

export default App
