import { useEffect, useRef } from 'react';
import { bandMeta, formatProb } from './utils';

export default function RegionMap({ cells, onCellClick, selectedCell }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const layerGroupRef = useRef(null);

  useEffect(() => {
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    import('leaflet').then((L) => {
      if (leafletMapRef.current) return;

      const map = L.default.map(mapRef.current, {
        center: [20, 74],
        zoom: 7,
        scrollWheelZoom: true,
        zoomControl: true,
      });

      // Dark basemap tiles
      L.default.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        {
          attribution: '© OpenStreetMap, © CARTO',
          subdomains: 'abcd',
          maxZoom: 19,
        }
      ).addTo(map);

      leafletMapRef.current = map;
      layerGroupRef.current = L.default.layerGroup().addTo(map);
    });
  }, []);

  useEffect(() => {
    if (!leafletMapRef.current || !cells || cells.length === 0) return;

    import('leaflet').then((L) => {
      layerGroupRef.current.clearLayers();

      cells.forEach((cell) => {
        const meta = bandMeta(cell.bust_probability);
        const isSelected =
          selectedCell &&
          selectedCell.lat === cell.lat &&
          selectedCell.lon === cell.lon;

        const opacity = 0.55 + cell.bust_probability * 0.35; // more risk = more opaque

        const rect = L.default.rectangle(
          [
            [cell.lat - 0.125, cell.lon - 0.125],
            [cell.lat + 0.125, cell.lon + 0.125],
          ],
          {
            color: isSelected ? '#fff' : 'transparent',
            weight: isSelected ? 2 : 0,
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
  }, [cells, selectedCell, onCellClick]);

  return (
    <div
      ref={mapRef}
      style={{ height: '100%', width: '100%', borderRadius: '10px', minHeight: 300 }}
    />
  );
}
