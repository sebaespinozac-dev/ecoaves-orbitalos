(() => {
  const DEFAULT = {
    lat: -23.6509,
    lon: -70.3975,
    display_name: "Antofagasta, Región de Antofagasta, Chile",
  };

  const state = {
    lat: DEFAULT.lat,
    lon: DEFAULT.lon,
    display_name: DEFAULT.display_name,
    layer: "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    date: isoDaysAgo(1),
  };

  let map;
  let marker;

  function isoDaysAgo(n) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - n);
    return d.toISOString().slice(0, 10);
  }

  function qs(id) {
    return document.getElementById(id);
  }

  function initMap() {
    map = L.map("map", { zoomControl: true }).setView([state.lat, state.lon], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 18,
    }).addTo(map);
    marker = L.marker([state.lat, state.lon]).addTo(map);
    const box = L.rectangle(
      [
        [state.lat - 1, state.lon - 1],
        [state.lat + 1, state.lon + 1],
      ],
      { color: "#1f4e79", weight: 1, fillOpacity: 0.05 }
    ).addTo(map);
    marker._bbox = box;
  }

  function setLocation(lat, lon, displayName) {
    state.lat = lat;
    state.lon = lon;
    state.display_name = displayName;
    qs("location-label").textContent = displayName;
    marker.setLatLng([lat, lon]);
    if (marker._bbox) {
      map.removeLayer(marker._bbox);
    }
    marker._bbox = L.rectangle(
      [
        [lat - 1, lon - 1],
        [lat + 1, lon + 1],
      ],
      { color: "#1f4e79", weight: 1, fillOpacity: 0.05 }
    ).addTo(map);
    map.setView([lat, lon], 8);
  }

  async function loadLayers() {
    const select = qs("layer-select");
    try {
      const res = await fetch("/api/layers");
      const layers = await res.json();
      select.innerHTML = layers
        .map(
          (l) =>
            `<option value="${l.id}">${l.name} (${l.type})</option>`
        )
        .join("");
      select.value = state.layer;
    } catch (err) {
      select.innerHTML =
        '<option value="VIIRS_SNPP_CorrectedReflectance_TrueColor">Color verdadero (VIIRS)</option>';
    }
  }

  function snapshotUrl() {
    const params = new URLSearchParams({
      lat: String(state.lat),
      lon: String(state.lon),
      date: state.date,
      layer: state.layer,
      width: "1024",
      height: "1024",
    });
    return `/api/imagery?${params.toString()}`;
  }

  function layerLabel() {
    const select = qs("layer-select");
    const opt = select.options[select.selectedIndex];
    return opt ? opt.textContent : state.layer;
  }

  function loadImagery() {
    const img = qs("snapshot-img");
    const meta = qs("snapshot-meta");
    meta.textContent = "Cargando imagen NASA Worldview…";
    img.onload = () => {
      meta.textContent = `${layerLabel()} · ${state.date} · fuente: NASA GIBS/Worldview · ~1 km/px`;
    };
    img.onerror = () => {
      meta.textContent =
        "No se pudo cargar la imagen. Prueba otra fecha o capa.";
    };
    img.src = snapshotUrl() + "&_=" + Date.now();
  }

  async function loadSentinel() {
    const status = qs("sentinel-status");
    const grid = qs("sentinel-gallery");
    status.textContent = "Buscando productos Sentinel-2…";
    grid.innerHTML = "";
    try {
      const params = new URLSearchParams({
        lat: String(state.lat),
        lon: String(state.lon),
        days: "7",
      });
      const res = await fetch(`/api/sentinel?${params}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const products = data.products || [];
      if (!products.length) {
        status.textContent = "Sin productos en los últimos 7 días para esta zona.";
        return;
      }
      status.textContent = `${products.length} producto(s) encontrados`;
      grid.innerHTML = products
        .map((p) => {
          const dt = (p.datetime || "").slice(0, 10) || "—";
          const clouds =
            p.cloud_cover == null ? "n/d" : `${Number(p.cloud_cover).toFixed(1)}% nubes`;
          const thumb = p.thumbnail_url
            ? `<img src="${p.thumbnail_url}" alt="Thumbnail Sentinel-2 ${dt}" loading="lazy" />`
            : `<div style="height:110px;background:#e8ebf0;display:flex;align-items:center;justify-content:center;color:#5c6678;font-size:0.8rem">Sin thumbnail</div>`;
          return `<article class="gallery-card">${thumb}<div class="meta"><strong>${dt}</strong>${clouds}<br/>Sentinel-2 L2A</div></article>`;
        })
        .join("");
    } catch (err) {
      status.textContent = "Error al consultar Copernicus STAC.";
    }
  }

  async function searchPlace(query) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || "Búsqueda fallida");
    }
    return res.json();
  }

  async function refreshAll() {
    loadImagery();
    await loadSentinel();
  }

  function wireEvents() {
    qs("search-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const q = qs("search-input").value.trim();
      if (!q) return;
      try {
        const hit = await searchPlace(q);
        setLocation(hit.lat, hit.lon, hit.display_name);
        await refreshAll();
      } catch (err) {
        qs("location-label").textContent = String(err.message || err);
      }
    });

    qs("layer-select").addEventListener("change", (ev) => {
      state.layer = ev.target.value;
      loadImagery();
    });

    qs("date-input").addEventListener("change", (ev) => {
      state.date = ev.target.value;
      loadImagery();
    });

    qs("reload-imagery").addEventListener("click", () => {
      loadImagery();
    });
  }

  async function boot() {
    qs("date-input").value = state.date;
    qs("search-input").value = "Antofagasta";
    initMap();
    wireEvents();
    await loadLayers();
    setLocation(state.lat, state.lon, state.display_name);
    await refreshAll();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
