<template>
  <section class="map-panel" aria-labelledby="map-panel-heading">
    <div class="map-panel-header">
      <div>
        <p class="eyebrow">Map</p>
        <h2 id="map-panel-heading">Mapped Stops</h2>
      </div>
      <p>{{ validStops.length }} mapped stop{{ validStops.length === 1 ? "" : "s" }}</p>
    </div>

    <div v-if="validStops.length === 0" class="placeholder-panel">
      <p>No valid POI coordinates are available for this itinerary.</p>
    </div>

    <div
      v-else
      ref="mapContainer"
      class="itinerary-map"
      role="img"
      :aria-label="mapLabel"
      aria-describedby="map-alternative"
    />

    <div id="map-alternative" class="map-stop-alternative">
      <h3>Mapped stop list</h3>
      <ol v-if="validStops.length > 0">
        <li v-for="(mappedStop, index) in validStops" :key="mappedStop.stop.id">
          {{ index + 1 }}. Day {{ mappedStop.dayNumber }}:
          {{ mappedStop.stop.poi?.name ?? mappedStop.stop.title }}
        </li>
      </ol>
      <p v-else>No stops can be shown on the map.</p>
    </div>

    <p v-if="missingStopCount > 0" class="map-note">
      {{ missingStopCount }} stop{{ missingStopCount === 1 ? "" : "s" }} could not be mapped because coordinates are missing.
    </p>
    <p class="map-note">{{ routeLineNote }}</p>
  </section>
</template>

<script setup lang="ts">
import "leaflet/dist/leaflet.css";
import L, { type LatLngExpression, type Map as LeafletMap } from "leaflet";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { Itinerary, ItineraryStop } from "../../types";

const props = defineProps<{
  itinerary: Itinerary;
}>();

interface MappedStop {
  dayNumber: number;
  stop: ItineraryStop;
  latitude: number;
  longitude: number;
}

const mapContainer = ref<HTMLElement | null>(null);
let map: LeafletMap | null = null;
let layerGroup: L.LayerGroup | null = null;

const allStops = computed<MappedStop[]>(() =>
  props.itinerary.days.flatMap((day) =>
    day.stops.map((stop) => ({
      dayNumber: day.dayNumber,
      stop,
      latitude: stop.poi?.latitude,
      longitude: stop.poi?.longitude,
    })),
  ),
);

const validStops = computed(() =>
  allStops.value.filter(
    (item) =>
      typeof item.latitude === "number" &&
      typeof item.longitude === "number" &&
      Number.isFinite(item.latitude) &&
      Number.isFinite(item.longitude),
  ),
);

const missingStopCount = computed(() => allStops.value.length - validStops.value.length);
const routeGeometry = computed<LatLngExpression[]>(() =>
  props.itinerary.days.flatMap((day) =>
    (day.routeGeometry ?? [])
      .filter(
        (coordinate) =>
          Array.isArray(coordinate) &&
          coordinate.length >= 2 &&
          Number.isFinite(coordinate[0]) &&
          Number.isFinite(coordinate[1]),
      )
      .map((coordinate) => [coordinate[0], coordinate[1]] as LatLngExpression),
  ),
);
const routeLineNote = computed(() =>
  routeGeometry.value.length > 1
    ? "Route line uses available provider geometry when present."
    : "Route lines are straight segments when provider geometry is unavailable.",
);
const mapLabel = computed(
  () =>
    `Map preview for ${props.itinerary.title} with ${validStops.value.length} mapped stops. A text stop list follows.`,
);

onMounted(() => {
  void renderMap();
});

watch(
  () => props.itinerary,
  () => {
    void renderMap();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
  }
});

async function renderMap(): Promise<void> {
  await nextTick();

  if (!mapContainer.value || validStops.value.length === 0) {
    return;
  }

  if (!map) {
    map = L.map(mapContainer.value, {
      scrollWheelZoom: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);
  }

  if (layerGroup) {
    layerGroup.clearLayers();
  } else {
    layerGroup = L.layerGroup().addTo(map);
  }

  const points: LatLngExpression[] = [];

  validStops.value.forEach((mappedStop, index) => {
    const point: LatLngExpression = [mappedStop.latitude, mappedStop.longitude];
    points.push(point);

    L.marker(point, {
      icon: createNumberedIcon(index + 1),
      title: mappedStop.stop.poi?.name ?? mappedStop.stop.title,
    })
      .bindPopup(
        `<strong>${index + 1}. ${escapeHtml(mappedStop.stop.poi?.name ?? mappedStop.stop.title)}</strong><br />` +
          `Day ${mappedStop.dayNumber}<br />${escapeHtml(mappedStop.stop.poi?.description ?? "")}`,
      )
      .addTo(layerGroup as L.LayerGroup);
  });

  const linePoints = routeGeometry.value.length > 1 ? routeGeometry.value : points;

  if (linePoints.length > 1 && layerGroup) {
    L.polyline(linePoints, {
      color: "#6059f6",
      opacity: 0.7,
      weight: 3,
    }).addTo(layerGroup);
  }

  const bounds = L.latLngBounds(points);
  map.fitBounds(bounds, { padding: [32, 32], maxZoom: 15 });
  map.invalidateSize();
}

function createNumberedIcon(number: number): L.DivIcon {
  return L.divIcon({
    className: "numbered-map-marker",
    html: `<span>${number}</span>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
</script>
