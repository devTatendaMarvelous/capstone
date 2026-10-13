import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import FarmLocationPicker, {
  isInsideStudyArea,
  MACHEKE_CENTER,
  STUDY_AREA_BBOX,
} from "../components/FarmLocationPicker";
import PredictionForm from "../components/PredictionForm";

// Mock Leaflet and React-Leaflet for headless jsdom test environment
vi.mock("react-leaflet", () => {
  return {
    MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
    TileLayer: () => <div data-testid="tile-layer" />,
    Marker: React.forwardRef(({ position, eventHandlers }, ref) => (
      <div
        ref={ref}
        data-testid="map-marker"
        data-position={JSON.stringify(position)}
        onClick={() => eventHandlers?.dragend?.()}
      />
    )),
    useMap: () => ({
      setView: vi.fn(),
      getZoom: vi.fn(() => 12),
    }),
    useMapEvents: ({ click }) => {
      return null;
    },
  };
});

describe("Study Area Bounding Box Calculation", () => {
  it("identifies points inside Macheke study area bbox", () => {
    expect(isInsideStudyArea(-18.136, 31.849)).toBe(true);
    expect(isInsideStudyArea(-18.20, 31.80)).toBe(true);
  });

  it("identifies points outside Macheke study area bbox", () => {
    // Harare
    expect(isInsideStudyArea(-17.82, 31.05)).toBe(false);
    // Bulawayo
    expect(isInsideStudyArea(-20.15, 28.58)).toBe(false);
  });
});

describe("FarmLocationPicker Component", () => {
  it("renders default map and inputs without initial confirmed location", () => {
    render(<FarmLocationPicker />);
    expect(screen.getByText("Select farm location")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Use My Current Location/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("-18.1360")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("31.8490")).toBeInTheDocument();
  });

  it("synchronises manual coordinate entry with the map and notifies parent", async () => {
    const user = userEvent.setup();
    const onLocationChange = vi.fn();
    render(<FarmLocationPicker onLocationChange={onLocationChange} />);

    const latInput = screen.getByPlaceholderText("-18.1360");
    const lonInput = screen.getByPlaceholderText("31.8490");

    await user.clear(latInput);
    await user.type(latInput, "-18.1500");
    await user.clear(lonInput);
    await user.type(lonInput, "31.8600");

    await user.click(screen.getByRole("button", { name: /Show on Map/i }));

    expect(onLocationChange).toHaveBeenCalledWith(
      expect.objectContaining({
        latitude: -18.15,
        longitude: 31.86,
        selectionMethod: "manual_coordinates",
        confirmed: false,
        isWithinStudyArea: true,
      }),
    );

    // Verify unconfirmed badge appears
    expect(screen.getByText(/Unconfirmed Selection:/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirm This Farm Location/i })).toBeInTheDocument();
  });

  it("validates invalid coordinate bounds", async () => {
    const user = userEvent.setup();
    render(<FarmLocationPicker />);

    const latInput = screen.getByPlaceholderText("-18.1360");
    await user.clear(latInput);
    await user.type(latInput, "120.0"); // Invalid latitude > 90

    await user.click(screen.getByRole("button", { name: /Show on Map/i }));
    expect(screen.getByText(/Latitude must be a valid number between -90 and 90/i)).toBeInTheDocument();
  });

  it("handles automatic browser geolocation success", async () => {
    const user = userEvent.setup();
    const onLocationChange = vi.fn();

    const mockGeolocation = {
      getCurrentPosition: vi.fn((success) => {
        success({
          coords: {
            latitude: -18.14,
            longitude: 31.85,
          },
        });
      }),
    };
    vi.stubGlobal("navigator", { geolocation: mockGeolocation });

    render(<FarmLocationPicker onLocationChange={onLocationChange} />);
    await user.click(screen.getByRole("button", { name: /Use My Current Location/i }));

    expect(mockGeolocation.getCurrentPosition).toHaveBeenCalled();
    expect(onLocationChange).toHaveBeenCalledWith(
      expect.objectContaining({
        latitude: -18.14,
        longitude: 31.85,
        selectionMethod: "browser_geolocation",
        confirmed: false,
      }),
    );
  });

  it("handles automatic browser geolocation denial and allows retry", async () => {
    const user = userEvent.setup();
    const mockGeolocation = {
      getCurrentPosition: vi.fn((success, error) => {
        error({
          code: 1, // PERMISSION_DENIED
        });
      }),
    };
    vi.stubGlobal("navigator", { geolocation: mockGeolocation });

    render(<FarmLocationPicker />);
    await user.click(screen.getByRole("button", { name: /Use My Current Location/i }));

    expect(await screen.findByText(/Location permission denied/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });

  it("requires explicit confirmation before marking confirmed", async () => {
    const user = userEvent.setup();
    const onLocationChange = vi.fn();
    render(<FarmLocationPicker onLocationChange={onLocationChange} />);

    const latInput = screen.getByPlaceholderText("-18.1360");
    const lonInput = screen.getByPlaceholderText("31.8490");
    await user.type(latInput, "-18.136");
    await user.type(lonInput, "31.849");
    await user.click(screen.getByRole("button", { name: /Show on Map/i }));

    // Click confirmation button
    const confirmBtn = screen.getByRole("button", { name: /Confirm This Farm Location/i });
    await user.click(confirmBtn);

    expect(onLocationChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        latitude: -18.136,
        longitude: 31.849,
        confirmed: true,
      }),
    );

    expect(screen.getByText(/Confirmed Farm Location:/i)).toBeInTheDocument();
  });
});

describe("PredictionForm with Location Integration", () => {
  it("blocks submission if location is not confirmed", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PredictionForm onSubmit={onSubmit} busy={false} />);

    // Fill area
    const areaInput = screen.getByPlaceholderText("e.g. 2.5");
    await user.type(areaInput, "2.0");

    await user.click(screen.getByRole("button", { name: "Estimate yield" }));
    expect(onSubmit).toHaveBeenCalled();
    const errors = onSubmit.mock.calls[0][1];
    expect(errors.location).toBeTruthy();
  });
});
