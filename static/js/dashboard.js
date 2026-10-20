async function loadMapLayers() {
  const map = L.map('map', { zoomControl: true }).setView([6.5, -3.5], 8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const layers = {};
  const layerEntries = [];
  const layerNames = ['parcelles','pistes','canaux_irrigation','magasins','vannes','limite_etat','aire_sechage','zio'];
  const customMarkers = {
    magasins: '/static/images/magasin.svg',
    vannes: '/static/images/vanne.svg'
  };

  function displayLabel(name) {
    const map = {
      parcelles: 'Parcelles',
      pistes: 'Pistes',
      canaux_irrigation: 'Canaux d\'irrigation',
      magasins: 'Magasins',
      vannes: 'Vannes',
      limite_etat: 'Limite Etat',
      aire_sechage: 'Aires de séchage',
      zio: 'Zio'
    };
    return map[name] || name;
  }

  // determine geometry category priority: points (1), lines (2), polygons (3)
  function geomPriority(geomType) {
    if (!geomType) return 3;
    const t = geomType.toLowerCase();
    if (t.includes('point')) return 1;
    if (t.includes('line')) return 2;
    return 3;
  }

  await Promise.all(layerNames.map(async (ln) => {
    try {
      const res = await fetch(`/api/${ln}`);
      if (!res.ok) return;
      const geo = await res.json();
      if (!geo || !geo.features) return;
      const gj = L.geoJSON(geo, {
        pointToLayer: function (feature, latlng) {
          if (!customMarkers[ln]) {
            return L.marker(latlng);
          }
          const icon = L.icon({
            iconUrl: customMarkers[ln],
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -11],
            className: 'custom-map-marker'
          });
          return L.marker(latlng, { icon });
        },
        style: function (feature) {
          const styles = {
            parcelles: {color:'#0b3d0b', weight:1, fillOpacity:0.15},
            pistes: {color:'#facc15', weight:3},
            canaux_irrigation: {color:'#0b69ff', weight:2},
            magasins: {color:'#92400e', weight:2},
            vannes: {color:'#ef4444', weight:2},
            limite_etat: {color:'#0f172a', weight:2, dashArray:'6'},
            aire_sechage: {color:'#06b6d4', weight:1, fillOpacity:0.08},
            zio: {color:'#386fa4', weight:3}
          };
          return styles[ln] || {color:'#333', weight:1};
        },
        onEachFeature: function (feature, layer) {
          if (feature.properties) {
            const p = feature.properties;
            let html = '';
            // Custom popups per layer name
            if (ln === 'parcelles') {
              if (p.nom_pcelle) html += `<strong>${p.nom_pcelle}</strong><br/>`;
              if (p.superficie) html += `Superficie: ${p.superficie} ha<br/>`;
              if (p.proprietaire) html += `Propriétaire: ${p.proprietaire}<br/>`;
            } else if (ln === 'pistes') {
              html += `<strong>Piste</strong><br/>`;
              if (p.nom) html += `Nom: ${p.nom}<br/>`;
              if (p.type) html += `Type: ${p.type}<br/>`;
            } else if (ln === 'canaux_irrigation') {
              html += `<strong>Canal d'irrigation</strong><br/>`;
              if (p.nom) html += `Nom: ${p.nom}<br/>`;
              if (p.debit) html += `Débit: ${p.debit || '-'} m3/s<br/>`;
            } else if (ln === 'magasins') {
              html += `<strong>Magasin</strong><br/>`;
              if (p.nom_magasin) html += `Nom: ${p.nom_magasin}<br/>`;
              if (p.adresse) html += `Adresse: ${p.adresse}<br/>`;
            } else if (ln === 'vannes') {
              html += `<strong>Vanne</strong><br/>`;
              if (p.nom_vanne) html += `Nom: ${p.nom_vanne}<br/>`;
              if (p.etat) html += `Etat: ${p.etat}<br/>`;
            } else if (ln === 'zio') {
              html += `<strong>Zio</strong><br/>`;
              if (p.nom) html += `Nom: ${p.nom}<br/>`;
            } else if (ln === 'aire_sechage') {
              // ensure unique labels for each point feature
              html += `<strong>Aire de séchage`;
              if (feature.id) html += ` #${feature.id}`;
              html += `</strong><br/>`;
              if (p.nom_aire) html += `Nom: ${p.nom_aire}<br/>`;
              if (p.capacite) html += `Capacité: ${p.capacite || '-'} kg<br/>`;
            } else {
              // fallback generic info
              for (const k in p) {
                if (!p.hasOwnProperty(k)) continue;
                html += `<strong>${k}:</strong> ${p[k]}<br/>`;
              }
            }
            // for point-like geometries, append a unique identifier if available
            if (feature.geometry && feature.geometry.type && feature.geometry.type.toLowerCase().includes('point')) {
              if (feature.id) html = `<strong>${ln} #${feature.id}</strong><br/>` + html;
            }
            layer.bindPopup(html);
          }
        }
      }).addTo(map);

      // determine representative geometry type for sorting
      let repType = null;
      for (const f of geo.features) {
        if (f && f.geometry && f.geometry.type) { repType = f.geometry.type; break; }
      }

      layers[ln] = gj;
      layerEntries.push({ name: ln, layer: gj, label: displayLabel(ln), priority: geomPriority(repType) });
    } catch (e) {
      console.warn('Error loading layer', ln, e);
    }
  }));

  // sort: by geometry priority (points, lines, polygons) then alphabetically A->Z by label
  layerEntries.sort((a,b) => {
    if (a.priority !== b.priority) return a.priority - b.priority;
    return a.label.localeCompare(b.label, 'fr', {sensitivity: 'base'});
  });

  const sortedControlLayers = {};
  layerEntries.forEach(entry => { sortedControlLayers[entry.label] = entry.layer; });

  L.control.layers(null, sortedControlLayers, {collapsed:true, position:'topright'}).addTo(map);

  const group = L.featureGroup(Object.values(layers));
  if (group.getLayers().length) {
    map.fitBounds(group.getBounds(), {padding:[20,20]});
  }

  const layerCountEl = document.getElementById('layerCount');
  if (layerCountEl) {
    layerCountEl.textContent = layerEntries.length + (layerEntries.length > 1 ? ' couches' : ' couche');
  }
}

loadMapLayers();

// ---- Campaign-driven dashboard JS ----
// Les graphiques ne sont pas dessinés avec une librairie de charts : ce sont
// des listes de barres HTML/CSS (une ligne par coopérative), ce qui garde les
// noms et les valeurs parfaitement lisibles quelle que soit la largeur de
// l'écran. Voir static/styles.css (.bar-row, .grp-row, .donut-*).

const DONUT_PALETTE = ['#1c7a5c', '#386fa4', '#a8662f', '#c9d6cd', '#7c9885', '#b08968', '#5c7a99', '#94a89a'];

function formatNumber(value, decimals = 2) {
  const num = Number(value) || 0;
  return num.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: decimals });
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

// Graphique en barres horizontales : une ligne "nom — valeur" par coopérative.
function renderBarList(containerId, items) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  const sorted = sortDescending(items || []);
  const maxVal = Math.max(0, ...sorted.map(i => Number(i.value || 0)));

  sorted.forEach(item => {
    const value = Number(item.value || 0);
    const pct = maxVal > 0 ? Math.max(0, (value / maxVal) * 100) : 0;
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML =
      `<span class="coop">${escapeHtml(item.coop)}</span>` +
      `<div class="bar-track"><div class="bar-fill" style="width:${pct}%;"></div></div>` +
      `<span class="bar-val">${formatNumber(value)}</span>`;
    container.appendChild(row);
  });
}

// Graphique en barres groupées : effectifs hommes / femmes par coopérative.
function renderGroupedList(containerId, items) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  const withTotal = (items || []).map(i => ({ ...i, total: Number(i.v1 || 0) + Number(i.v2 || 0) }));
  const sorted = withTotal.sort((a, b) => b.total - a.total);
  const maxVal = Math.max(0, ...sorted.flatMap(i => [Number(i.v1 || 0), Number(i.v2 || 0)]));

  sorted.forEach(item => {
    const hommes = Number(item.v1 || 0);
    const femmes = Number(item.v2 || 0);
    const hPct = maxVal > 0 ? (hommes / maxVal) * 100 : 0;
    const fPct = maxVal > 0 ? (femmes / maxVal) * 100 : 0;
    const row = document.createElement('div');
    row.className = 'grp-row';
    row.innerHTML =
      `<div class="grp-header">${escapeHtml(item.coop)} — <span class="total">${formatNumber(item.total, 0)}</span></div>` +
      `<div class="grp-bars"><div class="grp-track"><div class="grp-fill-h" style="width:${hPct}%;"></div></div><span class="grp-val">${formatNumber(hommes, 0)}</span></div>` +
      `<div class="grp-bars"><div class="grp-track"><div class="grp-fill-f" style="width:${fPct}%;"></div></div><span class="grp-val">${formatNumber(femmes, 0)}</span></div>`;
    container.appendChild(row);
  });

  const legend = document.createElement('div');
  legend.className = 'grp-legend';
  legend.innerHTML = '<span><i style="background:#386fa4;"></i>Hommes</span><span><i style="background:#a8662f;"></i>Femmes</span>';
  container.appendChild(legend);
}

// Graphique en anneau : variétés cultivées, avec légende couleur + effectif réel.
function renderDonut(containerId, labels, values) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  const total = values.reduce((a, b) => a + Number(b || 0), 0);
  const wrap = document.createElement('div');
  wrap.className = 'donut-wrap';

  const donut = document.createElement('div');
  donut.className = 'donut';
  if (total > 0) {
    let acc = 0;
    const stops = values.map((v, i) => {
      const start = (acc / total) * 100;
      acc += Number(v || 0);
      const end = (acc / total) * 100;
      return `${DONUT_PALETTE[i % DONUT_PALETTE.length]} ${start}% ${end}%`;
    }).join(', ');
    donut.style.setProperty('--donut-stops', stops);
  }

  const legend = document.createElement('div');
  legend.className = 'donut-legend';
  labels.forEach((label, i) => {
    const div = document.createElement('div');
    div.innerHTML = `<i style="background:${DONUT_PALETTE[i % DONUT_PALETTE.length]};"></i>${escapeHtml(label)}<b>${formatNumber(values[i], 0)}</b>`;
    legend.appendChild(div);
  });

  wrap.appendChild(donut);
  wrap.appendChild(legend);
  container.appendChild(wrap);
}

async function fetchCampaigns() {
  try {
    const res = await fetch('/api/campaigns');
    if (!res.ok) throw new Error('Erreur chargement campagnes');
    const j = await res.json();
    const container = document.getElementById('campaignChips');
    container.innerHTML = '';

    function addChip(label, id) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip' + (id === null ? ' is-active' : '');
      chip.textContent = label;
      chip.dataset.campaignId = id === null ? '' : id;
      chip.addEventListener('click', () => {
        container.querySelectorAll('.chip').forEach(el => el.classList.remove('is-active'));
        chip.classList.add('is-active');
        loadDashboard(id);
      });
      container.appendChild(chip);
    }

    addChip('Toutes', null);
    (j.campaigns || []).forEach(c => addChip(String(c.annee), c.id));

    // charge la vue initiale (aucune sélection = toutes campagnes confondues)
    loadDashboard(null);
  } catch (e) {
    console.warn('Campaigns load failed', e);
  }
}

function sortDescending(items) {
  return [...items].sort((a, b) => Number(b.value || 0) - Number(a.value || 0));
}

function updateComment(idx, text) { const el = document.getElementById('comment' + idx); if (el) el.textContent = text; }

async function loadDashboard(campagne_id) {
  try {
    const url = '/api/dashboard' + (campagne_id ? `?campagne_id=${campagne_id}` : '');
    const res = await fetch(url);
    if (!res.ok) throw new Error('Erreur chargement dashboard');
    const j = await res.json();
    if (!j.success) throw new Error(j.error || 'no data');
    const d = j.data;

    if (d.superficie_attribuee) {
      renderBarList('chart1', d.superficie_attribuee.items);
      updateComment(1, d.superficie_attribuee.comment || '');
    }
    if (d.superficie_cultivee) {
      renderBarList('chart2', d.superficie_cultivee.items);
      updateComment(2, d.superficie_cultivee.comment || '');
    }
    if (d.superficie_utilisation) {
      renderBarList('chart3', d.superficie_utilisation.items);
      updateComment(3, d.superficie_utilisation.comment || '');
    }
    if (d.production_kg) {
      renderBarList('chart4', d.production_kg.items);
      updateComment(4, d.production_kg.comment || '');
    }
    if (d.effectifs) {
      renderGroupedList('chart5', d.effectifs.items);
      updateComment(5, d.effectifs.comment || '');
    }
    if (d.qte_npk) {
      renderBarList('chart6', d.qte_npk.items);
      updateComment(6, d.qte_npk.comment || '');
    }
    if (d.qte_uree) {
      renderBarList('chart7', d.qte_uree.items);
      updateComment(7, d.qte_uree.comment || '');
    }
    if (d.qte_herbicide) {
      renderBarList('chart8', d.qte_herbicide.items);
      updateComment(8, d.qte_herbicide.comment || '');
    }
    if (d.qte_insecticide) {
      renderBarList('chart9', d.qte_insecticide.items);
      updateComment(9, d.qte_insecticide.comment || '');
    }
    if (d.production_ecoulee) {
      renderBarList('chart10', d.production_ecoulee.items);
      updateComment(10, d.production_ecoulee.comment || '');
    }
    if (d.production_restante) {
      renderBarList('chart11', d.production_restante.items);
      updateComment(11, d.production_restante.comment || '');
    }
    if (d.varietes) {
      const sums = {};
      Object.values(d.varietes.by_coop || {}).forEach(list => {
        (list || []).forEach(item => {
          const key = item.variete || 'Inconnu';
          sums[key] = (sums[key] || 0) + Number(item.count || 0);
        });
      });
      const entries = Object.entries(sums).map(([variete, count]) => ({ variete, count }));
      const sorted = entries.sort((a, b) => Number(b.count) - Number(a.count));
      const labels = sorted.map(item => item.variete);
      const values = sorted.map(item => Number(item.count || 0));
      renderDonut('chart12', labels, values);
      updateComment(12, labels.length ? `Les variétés les plus cultivées sont : ${labels.slice(0, 5).join(', ')}.` : 'Données insuffisantes pour cette campagne.');
    }
  } catch (e) {
    console.warn('Dashboard load failed', e);
  }
}

fetchCampaigns();
