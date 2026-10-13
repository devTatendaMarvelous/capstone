import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Macheke Default Coordinates
export const MACHEKE_CENTER = {
  lat: -18.136,
  lon: 31.849,
};

// Study Area Bounding Box
export const STUDY_AREA_BBOX = {
  minLat: -18.25,
  maxLat: -18.02,
  minLon: 31.75,
  maxLon: 31.95,
};

export function isInsideStudyArea(lat, lon) {
  return (
    lat >= STUDY_AREA_BBOX.minLat &&
    lat <= STUDY_AREA_BBOX.maxLat &&
    lon >= STUDY_AREA_BBOX.minLon &&
    lon <= STUDY_AREA_BBOX.maxLon
  );
}

// Marker icons
const confirmedIcon = L.divIcon({
  className: "farm-marker-confirmed",
  html: `<div style="background-color: #14613F; color: white; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.35); font-size: 16px;">🌱</div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 34],
});

const unconfirmedIcon = L.divIcon({
  className: "farm-marker-unconfirmed",
  html: `<div style="background-color: #D97706; color: white; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.35); font-size: 16px;">📍</div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 34],
});

function MapInteractionHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function MapViewController({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && Array.isArray(center) && center.length === 2) {
      map.setView(center, map.getZoom(), { animate: true });
    }
  }, [center, map]);
  return null;
}

export default function FarmLocationPicker({ onLocationChange, selectedLocation }) {
  const [position, setPosition] = useState(
    selectedLocation ? [selectedLocation.latitude, selectedLocation.longitude] : null,
  );
  const [selectionMethod, setSelectionMethod] = useState(
    selectedLocation?.selectionMethod || "manual_map_selection",
  );
  const [isConfirmed, setIsConfirmed] = useState(Boolean(selectedLocation?.confirmed));
  const [latInput, setLatInput] = useState(
    selectedLocation ? String(selectedLocation.latitude) : "",
  );
  const [lonInput, setLonInput] = useState(
    selectedLocation ? String(selectedLocation.longitude) : "",
  );
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState("");
  const [coordError, setCoordError] = useState("");

  const markerRef = useRef(null);

  const studyAreaMatch = useMemo(() => {
    if (!position) return null;
    return isInsideStudyArea(position[0], position[1]);
  }, [position]);

  // Method A: Browser Geolocation
  function handleUseCurrentLocation() {
    setGeoError("");
    if (!navigator.geolocation) {
      setGeoError("Geolocation is not supported by your browser.");
      return;
    }

    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = parseFloat(pos.coords.latitude.toFixed(5));
        const lon = parseFloat(pos.coords.longitude.toFixed(5));
        setPosition([lat, lon]);
        setLatInput(String(lat));
        setLonInput(String(lon));
        setSelectionMethod("browser_geolocation");
        setIsConfirmed(false); // Must be confirmed explicitly by farmer
        setGeoLoading(false);
        setCoordError("");
        notifyParent(lat, lon, "browser_geolocation", false);
      },
      (err) => {
        setGeoLoading(false);
        let msg = "Could not obtain location.";
        if (err.code === 1 || err.code === err.PERMISSION_DENIED) {
          msg = "Location permission denied. Please allow location access or choose on the map.";
        } else if (err.code === 2 || err.code === err.POSITION_UNAVAILABLE) {
          msg = "Location information is unavailable. Try manual map selection.";
        } else if (err.code === 3 || err.code === err.TIMEOUT) {
          msg = "Location request timed out. Please retry or pick location on the map.";
        }
        setGeoError(msg);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 },
    );
  }

  // Method B: Click or drag on map
  function handleMapClick(lat, lng) {
    const roundedLat = parseFloat(lat.toFixed(5));
    const roundedLng = parseFloat(lng.toFixed(5));
    setPosition([roundedLat, roundedLng]);
    setLatInput(String(roundedLat));
    setLonInput(String(roundedLng));
    setSelectionMethod("manual_map_selection");
    setIsConfirmed(false);
    setCoordError("");
    notifyParent(roundedLat, roundedLng, "manual_map_selection", false);
  }

  const markerEventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker != null) {
          const latlng = marker.getLatLng();
          const roundedLat = parseFloat(latlng.lat.toFixed(5));
          const roundedLng = parseFloat(latlng.lng.toFixed(5));
          setPosition([roundedLat, roundedLng]);
          setLatInput(String(roundedLat));
          setLonInput(String(roundedLng));
          setSelectionMethod("manual_map_selection");
          setIsConfirmed(false);
          setCoordError("");
          notifyParent(roundedLat, roundedLng, "manual_map_selection", false);
        }
      },
    }),
    [],
  );

  // Method C: Manual coordinate input
  function handleApplyCoordinates(e) {
    if (e) e.preventDefault();
    setCoordError("");
    const lat = parseFloat(latInput);
    const lon = parseFloat(lonInput);

    if (Number.isNaN(lat) || lat < -90 || lat > 90) {
      setCoordError("Latitude must be a valid number between -90 and 90.");
      return;
    }
    if (Number.isNaN(lon) || lon < -180 || lon > 180) {
      setCoordError("Longitude must be a valid number between -180 and 180.");
      return;
    }

    const roundedLat = parseFloat(lat.toFixed(5));
    const roundedLng = parseFloat(lon.toFixed(5));
    setPosition([roundedLat, roundedLng]);
    setSelectionMethod("manual_coordinates");
    setIsConfirmed(false);
    notifyParent(roundedLat, roundedLng, "manual_coordinates", false);
  }

  // Confirmation
  function handleConfirmLocation() {
    if (!position) return;
    setIsConfirmed(true);
    notifyParent(position[0], position[1], selectionMethod, true);
  }

  function handleAdjustLocation() {
    setIsConfirmed(false);
    notifyParent(position[0], position[1], selectionMethod, false);
  }

  function notifyParent(lat, lon, method, confirmed) {
    if (onLocationChange) {
      onLocationChange({
        latitude: lat,
        longitude: lon,
        selectionMethod: method,
        confirmed: confirmed,
        isWithinStudyArea: isInsideStudyArea(lat, lon),
      });
    }
  }

  const mapCenter = position || [MACHEKE_CENTER.lat, MACHEKE_CENTER.lon];

  return (
    <div className="panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-moss">Farm Location</span>
          <h2 className="text-lg font-semibold text-ink">Select farm location</h2>
          <p className="text-xs text-ink/65">
            Choose using your device location, the interactive map, or manual coordinates.
          </p>
        </div>

        {/* Method A: Automatic Geolocation Button */}
        <div>
          <button
            type="button"
            onClick={handleUseCurrentLocation}
            disabled={geoLoading}
            className="btn-secondary text-xs font-medium py-2 px-3 inline-flex items-center gap-1.5"
          >
            {geoLoading ? (
              <>
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-leaf border-r-transparent" />
                <span>Locating…</span>
              </>
            ) : (
              <>
                <span>📡</span>
                <span>Use My Current Location</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Geolocation error / retry */}
      {geoError && (
        <div className="rounded-xl bg-clay/10 p-3 text-xs text-clay flex items-center justify-between gap-2" role="alert">
          <span>{geoError}</span>
          <button
            type="button"
            onClick={handleUseCurrentLocation}
            className="font-semibold underline hover:text-ink shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* Interactive Map (Method B) */}
      <div className="relative overflow-hidden rounded-2xl border border-line bg-mist shadow-inner h-72 sm:h-80 z-0">
        <MapContainer
          center={mapCenter}
          zoom={position ? 13 : 11}
          scrollWheelZoom={true}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />
          <MapInteractionHandler onMapClick={handleMapClick} />
          <MapViewController center={position} />

          {position && (
            <Marker
              position={position}
              draggable={!isConfirmed}
              eventHandlers={markerEventHandlers}
              ref={markerRef}
              icon={isConfirmed ? confirmedIcon : unconfirmedIcon}
            />
          )}
        </MapContainer>

        {/* Map overlay helper banner */}
        {!position && (
          <div className="absolute top-3 left-3 right-3 rounded-xl bg-white/95 px-3 py-2 text-xs text-ink/80 shadow backdrop-blur pointer-events-none z-[400]">
            💡 <strong>Map default center is Macheke town.</strong> Click anywhere on the map or use your current location to pick your farm.
          </div>
        )}
      </div>

      {/* Method C: Manual Coordinate Entry & Synchronised Inputs */}
      <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] items-end">
        <div>
          <label className="block text-xs font-medium text-ink/70">
            Latitude (°):
            <input
              type="number"
              step="any"
              value={latInput}
              onChange={(e) => {
                setLatInput(e.target.value);
                setIsConfirmed(false);
              }}
              placeholder="-18.1360"
              className="input text-xs py-2 mt-1"
            />
          </label>
        </div>
        <div>
          <label className="block text-xs font-medium text-ink/70">
            Longitude (°):
            <input
              type="number"
              step="any"
              value={lonInput}
              onChange={(e) => {
                setLonInput(e.target.value);
                setIsConfirmed(false);
              }}
              placeholder="31.8490"
              className="input text-xs py-2 mt-1"
            />
          </label>
        </div>
        <div>
          <button
            type="button"
            onClick={handleApplyCoordinates}
            className="btn-secondary text-xs py-2 px-3 w-full sm:w-auto"
          >
            Show on Map
          </button>
        </div>
      </div>

      {coordError && <p className="text-xs text-clay">{coordError}</p>}

      {/* Selected Location Details & Confirmation Status */}
      {position ? (
        <div className={`rounded-xl p-3.5 text-xs transition border ${isConfirmed ? "bg-leaf/5 border-leaf/20" : "bg-amber-500/10 border-amber-500/30"}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-1.5 font-semibold">
                <span>{isConfirmed ? "✅ Confirmed Farm Location:" : "⚠️ Unconfirmed Selection:"}</span>
                <span className="font-mono">{position[0].toFixed(5)}, {position[1].toFixed(5)}</span>
              </div>
              <p className="mt-0.5 text-ink/65">
                Method: {selectionMethod.replace(/_/g, " ")}
              </p>
            </div>

            <div>
              {isConfirmed ? (
                <button
                  type="button"
                  onClick={handleAdjustLocation}
                  className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-ink ring-1 ring-line hover:bg-mist"
                >
                  Adjust Location
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleConfirmLocation}
                  className="rounded-lg bg-leaf px-3.5 py-1.5 text-xs font-semibold text-white shadow hover:bg-[#0f4d32]"
                >
                  Confirm This Farm Location
                </button>
              )}
            </div>
          </div>

          {/* Scope validation notice */}
          <div className="mt-2.5 pt-2 border-t border-black/5">
            {studyAreaMatch ? (
              <span className="text-moss font-medium">
                🎯 Location is within the validated Macheke study area scope.
              </span>
            ) : (
              <span className="text-clay font-medium">
                ⚠️ Point is outside the validated Macheke study area scope (-18.25 to -18.02 S, 31.75 to 31.95 E). Predictions outside this scope are experimental.
              </span>
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-xl bg-black/[0.02] p-3 text-xs text-ink/60 text-center border border-dashed border-line">
          No location selected yet. Click the map or click &quot;Use My Current Location&quot;.
        </div>
      )}
    </div>
  );
}
