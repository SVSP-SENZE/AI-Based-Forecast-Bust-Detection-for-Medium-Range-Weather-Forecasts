import { useEffect, useRef } from 'react';
import { probColor } from './utils';

// We import leaflet dynamically to avoid SSR issues
export default function RegionMap({ cells, onCellClick, selectedCell }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const layerGroupRef = useRef(null);

  useEffect(() => {
    // Load leaflet CSS once
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    import('leaflet').then((L) => {
      if (leafletMapRef.current) return; // already initialized

      const map = L.default.map(mapRef.current, {
        center: [20, 74],
        zoom: 7,
        scrollWheelZoom: true,
      });

      L.default.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(map);

      leafletMapRef.current = map;
      layerGroupRef.current = L.default.layerGroup().addTo(map);
    });
  }, []);

  useEffect(() => {
    if (!leafletMapRef.current || !cells || cells.length === 0) return;

    import('leaflet').then((L) => {
      layerGroupRef.current.clearLayers();

      cells.forEach((cell) => {
        const color = probColor(cell.bust_probability);
        const isSelected =
          selectedCell &&
          selectedCell.lat === cell.lat &&
          selectedCell.lon === cell.lon;

        const rect = L.default.rectangle(
          [
            [cell.lat - 0.125, cell.lon - 0.125],
            [cell.lat + 0.125, cell.lon + 0.125],
          ],
          {
            color: isSelected ? '#1e40af' : '#475569',
            weight: isSelected ? 2 : 0.5,
            fillColor: color,
            fillOpacity: 0.65,
          }
        );

        rect.bindTooltip(
          `Lat ${cell.lat}, Lon ${cell.lon}<br/>` +
            `Bust prob: ${(cell.bust_probability * 100).toFixed(1)}%<br/>` +
            `Confidence: <b>${cell.confidence_band}</b>`,
          { sticky: true }
        );

        rect.on('click', () => onCellClick && onCellClick(cell));
        rect.addTo(layerGroupRef.current);
      });
    });
  }, [cells, selectedCell, onCellClick]);

  return (
    <div
      ref={mapRef}
      style={{ height: '450px', width: '100%', borderRadius: '8px' }}
    />
  );
}
