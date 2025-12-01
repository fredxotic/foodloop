/**
 * FoodLoop Map Logic
 * Handles Leaflet initialization and marker rendering
 */

const FoodLoopMap = {
    map: null,
    markers: [],

    init(mapContainerId, data) {
        if (!document.getElementById(mapContainerId)) return;

        // 1. Default Center (Nairobi)
        const defaultLat = -1.2921;
        const defaultLng = 36.8219;
        
        const startLat = data.userLocation ? data.userLocation.lat : defaultLat;
        const startLng = data.userLocation ? data.userLocation.lng : defaultLng;

        // 2. Initialize Map
        this.map = L.map(mapContainerId, {
            zoomControl: false, // We'll add custom controls
            attributionControl: false
        }).setView([startLat, startLng], 13);

        // 3. Add Tile Layer (Standard OSM)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(this.map);

        // 4. Add Custom Zoom Control (Bottom Right)
        L.control.zoom({ position: 'bottomright' }).addTo(this.map);

        // 5. Add Markers
        this.addMarkers(data.donations);
        
        // 6. Add User Location Marker
        if (data.userLocation) {
            this.addUserMarker(data.userLocation);
        }

        // 7. Fix for Gray Tiles (Invalidate Size)
        setTimeout(() => { 
            this.map.invalidateSize(); 
        }, 200);
    },

    createCustomIcon(category) {
        // Define colors based on category if needed, for now using brand green
        return L.divIcon({
            className: 'custom-map-pin',
            html: `<div class="pin-inner"><i class="fas fa-utensils"></i></div>`,
            iconSize: [40, 40],
            iconAnchor: [20, 34],
            popupAnchor: [0, -35]
        });
    },

    addMarkers(donations) {
        donations.forEach(d => {
            if (d.lat && d.lng) {
                const icon = this.createCustomIcon(d.category);
                
                // Build Popup HTML using our new Design System classes
                const popupContent = `
                    <div class="map-popup-card">
                        <div class="popup-header">
                            <span class="badge">${d.category}</span>
                            <span class="score"><i class="fas fa-leaf"></i> ${d.score}</span>
                        </div>
                        <h4 class="popup-title">${d.title}</h4>
                        <a href="${d.url}" class="btn btn-brand btn-sm w-full mt-2">View & Claim</a>
                    </div>
                `;

                L.marker([d.lat, d.lng], { icon: icon })
                 .addTo(this.map)
                 .bindPopup(popupContent, { 
                     minWidth: 220, 
                     maxWidth: 240, 
                     className: 'foodloop-popup'
                 });
            }
        });
    },

    addUserMarker(location) {
        const userIcon = L.divIcon({
            className: 'user-location-pin',
            html: '<div class="pulse-ring"></div><div class="center-dot"></div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        L.marker([location.lat, location.lng], { 
            icon: userIcon, 
            zIndexOffset: 1000 
        }).addTo(this.map)
          .bindPopup('<div class="text-center font-bold text-sm p-1">You are here</div>');
    },

    centerOnUser(location) {
        if (location) {
            this.map.flyTo([location.lat, location.lng], 15);
        } else if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(position => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                this.map.flyTo([lat, lng], 15);
                this.addUserMarker({lat, lng});
            });
        } else {
            alert("Location not available");
        }
    }
};