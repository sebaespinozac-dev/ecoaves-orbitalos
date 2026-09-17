(() => {
  const DEFAULT = {
    lat: -23.6509,
    lon: -70.3975,
    display_name: "Antofagasta, Región de Antofagasta, Chile",
  };

  const DARKSKY_LAYER = "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance";
  const PRECIP_LAYER = "IMERG_Precipitation_Rate";

  const state = {
    lat: DEFAULT.lat,
    lon: DEFAULT.lon,
    display_name: DEFAULT.display_name,
    layer: "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    date: isoDaysAgo(1),
    modules: { darksky: false, fire: false, tailings: false, ravine: false },
    sentinelProducts: [],
    fires: [],
  };

  let map;
  let marker;
  let bboxRect;
  let darkskyOverlay = null;
  let precipOverlay = null;
  let fireLayer = null;

  function isoDaysAgo(n) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - n);
    return d.toISOString().slice(0, 10);
  }

  function qs(id) {
    return document.getElementById(id);
  }

  function boundsAround(lat, lon, half = 1) {
    return [
      [lat - half, lon - half],
      [lat + half, lon + half],
    ];
  }

  function imageryUrl(layer, date) {
    const params = new URLSearchParams({
      lat: String(state.lat),
      lon: String(state.lon),
      date: date || state.date,
      layer,
      width: "1024",
      height: "1024",
    });
    return `/api/imagery?${params.toString()}&_=${Date.now()}`;
  }

  function precipUrl() {
    const params = new URLSearchParams({
      lat: String(state.lat),
      lon: String(state.lon),
      date: state.date,
      width: "1024",
      height: "1024",
    });
    return `/api/precipitation?${params.toString()}&_=${Date.now()}`;
  }

  function initMap() {
    map = L.map("map", { zoomControl: true }).setView([state.lat, state.lon], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 18,
    }).addTo(map);
    marker = L.marker([state.lat, state.lon]).addTo(map);
    bboxRect = L.rectangle(boundsAround(state.lat, state.lon), {
      color: "#1f4e79",
      weight: 1,
      fillOpacity: 0.04,
    }).addTo(map);
    fireLayer = L.layerGroup().addTo(map);
  }

  function setLocation(lat, lon, displayName) {
    state.lat = lat;
    state.lon = lon;
    state.display_name = displayName;
    qs("location-label").textContent = displayName;
    marker.setLatLng([lat, lon]);
    if (bboxRect) map.removeLayer(bboxRect);
    bboxRect = L.rectangle(boundsAround(lat, lon), {
      color: "#1f4e79",
      weight: 1,
      fillOpacity: 0.04,
    }).addTo(map);
    map.setView([lat, lon], 8);
    refreshOverlays();
  }

  async function loadLayers() {
    const select = qs("layer-select");
    try {
      const res = await fetch("/api/layers");
      const layers = await res.json();
      select.innerHTML = layers
        .map((l) => `<option value="${l.id}">${l.name} (${l.type})</option>`)
        .join("");
      select.value = state.layer;
    } catch (_err) {
      select.innerHTML =
        '<option value="VIIRS_SNPP_CorrectedReflectance_TrueColor">Color verdadero (VIIRS)</option>';
    }
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
      meta.textContent = "No se pudo cargar la imagen. Prueba otra fecha o capa.";
    };
    img.src = imageryUrl(state.layer, state.date);
  }

  function clearOverlay(refName) {
    if (refName === "darksky" && darkskyOverlay) {
      map.removeLayer(darkskyOverlay);
      darkskyOverlay = null;
    }
    if (refName === "ravine" && precipOverlay) {
      map.removeLayer(precipOverlay);
      precipOverlay = null;
    }
  }

  function setImageOverlay(kind, url) {
    clearOverlay(kind);
    const bounds = boundsAround(state.lat, state.lon);
    const overlay = L.imageOverlay(url, bounds, {
      opacity: 0.55,
      interactive: false,
    });
    overlay.addTo(map);
    if (kind === "darksky") darkskyOverlay = overlay;
    if (kind === "ravine") precipOverlay = overlay;
  }

  async function refreshOverlays() {
    if (state.modules.darksky) {
      setImageOverlay("darksky", imageryUrl(DARKSKY_LAYER, state.date));
    } else {
      clearOverlay("darksky");
    }
    if (state.modules.ravine) {
      setImageOverlay("ravine", precipUrl());
    } else {
      clearOverlay("ravine");
    }
    if (state.modules.fire) {
      await loadFires();
    } else {
      fireLayer.clearLayers();
      state.fires = [];
    }
    renderModulePanels();
  }

  async function loadFires() {
    fireLayer.clearLayers();
    try {
      const params = new URLSearchParams({
        lat: String(state.lat),
        lon: String(state.lon),
        days: "1",
      });
      const res = await fetch(`/api/fires?${params}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      state.fires = data.fires || [];
      state.firesNote = data.note || "";
      state.firesSource = data.source || "";
      state.fires.forEach((f) => {
        const color = (f.frp || 0) >= 10 ? "#c43c1a" : "#e8673a";
        const m = L.circleMarker([f.lat, f.lon], {
          radius: 6,
          color,
          fillColor: color,
          fillOpacity: 0.85,
          weight: 1,
        });
        m.bindPopup(
          `<strong>Foco FIRMS</strong><br/>FRP: ${f.frp ?? "n/d"} MW<br/>Confianza: ${f.confidence ?? "n/d"}<br/>${f.date || ""}`
        );
        fireLayer.addLayer(m);
      });
    } catch (_err) {
      state.fires = [];
      state.firesNote = "Error al consultar FIRMS.";
    }
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
      state.sentinelProducts = data.products || [];
      if (!state.sentinelProducts.length) {
        status.textContent = "Sin productos en los últimos 7 días para esta zona.";
        renderModulePanels();
        return;
      }
      status.textContent = `${state.sentinelProducts.length} producto(s) encontrados`;
      grid.innerHTML = state.sentinelProducts
        .map((p, idx) => {
          const dt = (p.datetime || "").slice(0, 10) || "—";
          const clouds =
            p.cloud_cover == null
              ? "n/d"
              : `${Number(p.cloud_cover).toFixed(1)}% nubes`;
          const thumb = p.thumbnail_url
            ? `<img src="${p.thumbnail_url}" alt="Thumbnail Sentinel-2 ${dt}" loading="lazy" data-idx="${idx}" />`
            : `<div class="thumb-missing" data-idx="${idx}">Sin thumbnail</div>`;
          return `<article class="gallery-card" data-idx="${idx}">${thumb}<div class="meta"><strong>${dt}</strong>${clouds}<br/>Sentinel-2 L2A</div></article>`;
        })
        .join("");
      grid.querySelectorAll(".gallery-card").forEach((card) => {
        card.addEventListener("click", () => {
          const idx = Number(card.getAttribute("data-idx"));
          openLightbox(state.sentinelProducts[idx]);
        });
      });
      renderModulePanels();
    } catch (_err) {
      status.textContent = "Error al consultar Copernicus STAC.";
      state.sentinelProducts = [];
      renderModulePanels();
    }
  }

  function openLightbox(product) {
    if (!product || !product.thumbnail_url) return;
    const box = qs("lightbox");
    qs("lightbox-img").src = product.thumbnail_url;
    qs("lightbox-caption").textContent = `${(product.datetime || "").slice(0, 19)} · nubes ${
      product.cloud_cover == null ? "n/d" : Number(product.cloud_cover).toFixed(1) + "%"
    } · ${product.id || ""}`;
    box.hidden = false;
  }

  function closeLightbox() {
    qs("lightbox").hidden = true;
  }

  function sortedSentinelByDate() {
    return [...state.sentinelProducts].sort((a, b) =>
      String(a.datetime || "").localeCompare(String(b.datetime || ""))
    );
  }

  function renderModulePanels() {
    const detail = qs("module-detail");
    const title = qs("active-module-title");
    const body = qs("active-module-body");
    const active = Object.keys(state.modules).filter((k) => state.modules[k]);

    if (!active.length) {
      detail.innerHTML = `<p class="muted">Activa un módulo para ver el detalle.</p>`;
      title.textContent = "Panel del módulo";
      body.innerHTML = `<p class="muted">Sin módulo activo.</p>`;
      return;
    }

    const focus = active[active.length - 1];
    let leftHtml = "";
    let rightHtml = "";

    if (state.modules.darksky) {
      leftHtml += `<p><strong>DARKSKY</strong><br/><span class="level-badge">nivel: n/d</span></p>
        <p class="muted">Overlay DNB semitransparente en el mapa. Nivel cuantitativo requiere fotometría Black Marble / lote DARKSKY.</p>`;
    }
    if (state.modules.fire) {
      leftHtml += `<p><strong>FIRE</strong><br/>${state.fires.length} foco(s)</p>
        <p class="muted">${state.firesNote || state.firesSource || "NASA FIRMS VIIRS"}</p>`;
    }
    if (state.modules.tailings) {
      leftHtml += `<p><strong>TAILINGS</strong><br/>${state.sentinelProducts.length} escena(s) S2</p>
        <p class="muted">Clic en un thumbnail para ampliar. Comparación abajo.</p>`;
    }
    if (state.modules.ravine) {
      leftHtml += `<p><strong>RAVINE</strong><br/>Overlay IMERG</p>
        <p class="muted">Precipitación Worldview · ${state.date}</p>`;
    }
    detail.innerHTML = leftHtml || `<p class="muted">—</p>`;

    if (focus === "darksky") {
      title.textContent = "DARKSKY — contaminación lumínica";
      rightHtml = `
        <p>Capa: <code>${DARKSKY_LAYER}</code></p>
        <p>Fecha: ${state.date}</p>
        <p><span class="level-badge">normal → observar → fiscalizar → crítico</span></p>
        <p class="muted">Indicador cuantitativo no inventado: pendiente de fotometría DNB / reporte DARKSKY.</p>`;
    } else if (focus === "fire") {
      title.textContent = "FIRE — focos activos";
      if (!state.fires.length) {
        rightHtml = `<p>Sin focos activos en la zona</p><p class="muted">${state.firesNote || ""}</p>`;
      } else {
        const rows = state.fires
          .slice(0, 25)
          .map(
            (f) =>
              `<tr><td>${f.lat.toFixed(3)}, ${f.lon.toFixed(3)}</td><td>${f.frp ?? "—"}</td><td>${f.confidence ?? "—"}</td><td>${f.date || "—"}</td></tr>`
          )
          .join("");
        rightHtml = `<table class="fire-table"><thead><tr><th>Lat, Lon</th><th>FRP</th><th>Conf.</th><th>Fecha</th></tr></thead><tbody>${rows}</tbody></table>`;
      }
    } else if (focus === "tailings") {
      title.textContent = "TAILINGS — comparar antes/después";
      const sorted = sortedSentinelByDate();
      if (sorted.length < 2) {
        rightHtml = `<p class="muted">Se necesitan al menos 2 escenas Sentinel-2 en 7 días para comparar.</p>
          <p class="muted">Para análisis espectral (NDWI/NDVI) se requiere descarga completa con credenciales CDSE.</p>`;
      } else {
        const oldest = sorted[0];
        const newest = sorted[sorted.length - 1];
        rightHtml = `
          <div class="compare">
            <figure>
              <img src="${oldest.thumbnail_url || ""}" alt="Antes" data-role="old" />
              <figcaption>Antes · ${(oldest.datetime || "").slice(0, 10)} · nubes ${
                oldest.cloud_cover == null ? "n/d" : Number(oldest.cloud_cover).toFixed(1) + "%"
              }</figcaption>
            </figure>
            <figure>
              <img src="${newest.thumbnail_url || ""}" alt="Después" data-role="new" />
              <figcaption>Después · ${(newest.datetime || "").slice(0, 10)} · nubes ${
                newest.cloud_cover == null ? "n/d" : Number(newest.cloud_cover).toFixed(1) + "%"
              }</figcaption>
            </figure>
          </div>
          <p class="muted" style="margin-top:0.5rem">Para análisis espectral (NDWI/NDVI) se requiere descarga completa con credenciales CDSE.</p>`;
      }
    } else if (focus === "ravine") {
      title.textContent = "RAVINE — precipitación IMERG";
      rightHtml = `
        <p>Capa: <code>${PRECIP_LAYER}</code></p>
        <p>Fecha: ${state.date}</p>
        <p class="muted">Overlay semitransparente en el mapa (Worldview Snapshot). Sin inventar mm acumulados sin parsear el raster.</p>
        <img src="${precipUrl()}" alt="Precipitación IMERG" style="width:100%;max-height:160px;object-fit:contain;background:#e6e9ef;border:1px solid var(--border);border-radius:4px;" />`;
    }

    body.innerHTML = rightHtml;
    body.querySelectorAll(".compare img").forEach((img) => {
      img.addEventListener("click", () => {
        const role = img.getAttribute("data-role");
        const sorted = sortedSentinelByDate();
        const product = role === "old" ? sorted[0] : sorted[sorted.length - 1];
        openLightbox(product);
      });
    });
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
    await refreshOverlays();
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

    qs("date-input").addEventListener("change", async (ev) => {
      state.date = ev.target.value;
      loadImagery();
      await refreshOverlays();
    });

    qs("reload-imagery").addEventListener("click", () => loadImagery());

    ["darksky", "fire", "tailings", "ravine"].forEach((name) => {
      qs(`mod-${name}`).addEventListener("change", async (ev) => {
        state.modules[name] = ev.target.checked;
        if (name === "darksky" && ev.target.checked) {
          // Also switch main preview to night lights for context
          state.layer = DARKSKY_LAYER;
          qs("layer-select").value = DARKSKY_LAYER;
          loadImagery();
        }
        if (name === "ravine" && ev.target.checked) {
          state.layer = PRECIP_LAYER;
          qs("layer-select").value = PRECIP_LAYER;
          loadImagery();
        }
        await refreshOverlays();
      });
    });

    qs("toggle-modules").addEventListener("click", () => {
      document.querySelector(".workspace").classList.toggle("collapsed-modules");
    });

    qs("lightbox-close").addEventListener("click", closeLightbox);
    qs("lightbox").addEventListener("click", (ev) => {
      if (ev.target.id === "lightbox") closeLightbox();
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
