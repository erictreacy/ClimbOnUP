import React from 'react';

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

interface RouteListProps {
  routes: Route[];
  areaId: number;
}

export const RouteList: React.FC<RouteListProps> = ({ routes, areaId }) => {
  const areaRoutes = routes.filter(route => route.area_id === areaId);

  if (areaRoutes.length === 0) {
    return <div className="empty-message">No routes found for this area.</div>;
  }

  return (
    <div className="route-list">
      <h4>Routes ({areaRoutes.length})</h4>
      {areaRoutes.map(route => (
        <div key={route.id} className="route-card">
          <h5>
            {route.name}
            {route.grade && <span className="route-grade">{route.grade}</span>}
          </h5>
          <div className="route-info">
            {route.type && (
              <p>
                <strong>Type:</strong>
                {route.type}
              </p>
            )}
            {route.height && (
              <p>
                <strong>Height:</strong>
                {route.height}
              </p>
            )}
            {route.pitches > 0 && (
              <p>
                <strong>Pitches:</strong>
                {route.pitches}
              </p>
            )}
          </div>
          {route.description && (
            <div className="route-description">
              <p>{route.description}</p>
            </div>
          )}
          {(route.protection || route.first_ascent || route.location_description) && (
            <div className="route-details">
              {route.protection && (
                <p>
                  <strong>Protection:</strong>
                  {route.protection}
                </p>
              )}
              {route.first_ascent && (
                <p>
                  <strong>First Ascent:</strong>
                  {route.first_ascent}
                </p>
              )}
              {route.location_description && (
                <p>
                  <strong>Location:</strong>
                  {route.location_description}
                </p>
              )}
            </div>
          )}
          {route.photos && route.photos.length > 0 && (
            <div className="route-photos">
              {route.photos.map((photo, index) => (
                <figure key={index} className="route-photo">
                  <img src={photo.url} alt={photo.caption || route.name} loading="lazy" />
                  {photo.caption && <figcaption>{photo.caption}</figcaption>}
                </figure>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
