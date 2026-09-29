import { useEffect, useRef, useState } from 'react';
import { bandMeta, formatProb } from './utils';

export default function RegionMap({ cells, onCellClick, selectedCell }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const layerGroupRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  // Initialize Leaflet map once
  useEffect(() => {
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    let isMounted = true;
    import('leaflet').then((L) => {
      if (!isMounted || leafletMapRef.current || !mapRef.current) return;

      const map = L.default.map(mapRef.current, {
        center: [19.75, 74.25],
        zoom: 7,
        scrollWheelZoom: true,
        zoomControl: true,
      });

      // Free, high-performance Esri Dark Gray Canvas Basemap (Zero API Key required)
      L.default.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: '&copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
          maxZoom: 16,
        }
      ).addTo(map);

      // Add Esri Dark Gray reference label overlay (cities, district boundaries)
      L.default.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: '',
          maxZoom: 16,
          opacity: 0.75,
        }
      ).addTo(map);

      leafletMapRef.current = map;
      layerGroupRef.current = L.default.layerGroup().addTo(map);
      setMapReady(true);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  // Render grid cells whenever cells, selectedCell, or mapReady changes
  useEffect(() => {
    if (!mapReady || !leafletMapRef.current || !layerGroupRef.current || !cells || cells.length === 0) return;

    import('leaflet').then((L) => {
      layerGroupRef.current.clearLayers();

      cells.forEach((cell) => {
        const meta = bandMeta(cell.bust_probability);
        const isSelected =
          selectedCell &&
          selectedCell.lat === cell.lat &&
          selectedCell.lon === cell.lon;

        const opacity = 0.65 + cell.bust_probability * 0.3; // 0.65 to 0.95 opacity

        const rect = L.default.rectangle(
          [
            [cell.lat - 0.125, cell.lon - 0.125],
            [cell.lat + 0.125, cell.lon + 0.125],
          ],
          {
            color: isSelected ? '#ffffff' : 'rgba(0,0,0,0.4)',
            weight: isSelected ? 2.5 : 0.5,
            fillColor: meta.color,
            fillOpacity: opacity,
          }
        );

        rect.bindTooltip(
          `<div style="font-family:Inter,sans-serif;font-size:12px;line-height:1.6;padding:2px 0">` +
          `<b style="color:${meta.color}">${meta.label}</b><br/>` +
          `Bust prob: <b>${formatProb(cell.bust_probability)}</b><br/>` +
          `<span style="color:#8b93a8">${cell.lat}°N, ${cell.lon}°E</span>` +
          `</div>`,
          { sticky: true, className: 'dark-tooltip' }
        );

        rect.on('click', () => onCellClick && onCellClick(cell));
        rect.addTo(layerGroupRef.current);
      });
    });
  }, [cells, selectedCell, mapReady, onCellClick]);

  return (
    <div
      ref={mapRef}
      style={{ height: '100%', width: '100%', borderRadius: '10px', minHeight: 350 }}
    />
  );
}
