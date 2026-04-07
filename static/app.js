// Configuration
const API_BASE_URL = window.location.origin + '/api';
const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws';

let ws = null;
let reconnectInterval = null;
let zonesData = [];

document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    loadInitialData();
    setupEventListeners();
});

function initWebSocket() {
    try {
        ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            clearInterval(reconnectInterval);
        };
        
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                initWebSocket();
            }, 5000);
        };
    } catch (error) {
        console.error('WebSocket initialization error:', error);
        updateConnectionStatus(false);
    }
}

function handleWebSocketMessage(message) {
    console.log('Received:', message.type);
    
    switch (message.type) {
        case 'connected':
            console.log('Connection established');
            break;
        case 'crowd_update':
            zonesData = message.data;
            renderZones(message.data);
            updateLastUpdate();
            break;
        case 'alert':
            showAlert(message.data);
            loadAlerts();
            break;
        case 'new_order':
            loadOrders();
            break;
    }
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connectionIndicator');
    const status = document.getElementById('connectionStatus');
    
    if (connected) {
        indicator.className = 'connection-indicator connected';
        status.textContent = 'Connected';
        status.className = 'text-sm text-green-400';
    } else {
        indicator.className = 'connection-indicator disconnected';
        status.textContent = 'Disconnected';
        status.className = 'text-sm text-red-400';
    }
}

async function loadInitialData() {
    await loadZones();
    await loadOrders();
    await loadAlerts();
}

async function loadZones() {
    try {
        const response = await fetch(`${API_BASE_URL}/zones`);
        const data = await response.json();
        zonesData = data.zones;
        renderZones(data.zones);
        updateLastUpdate();
    } catch (error) {
        console.error('Error loading zones:', error);
    }
}

function renderZones(zones) {
    const categories = {
        'Entry': 'entryZones',
        'Food': 'foodZones',
        'Facilities': 'facilitiesZones',
        'Shop': 'shopZones',
        'Seating': 'seatingZones'
    };
    
    Object.values(categories).forEach(id => {
        document.getElementById(id).innerHTML = '';
    });
    
    let lowCount = 0, mediumCount = 0, highCount = 0, totalCapacity = 0;
    
    zones.forEach(zone => {
        const densityLevel = calculateDensityLevel(zone.current_capacity, zone.max_capacity);
        const percentage = Math.round((zone.current_capacity / zone.max_capacity) * 100);
        
        if (densityLevel === 'low') lowCount++;
        else if (densityLevel === 'medium') mediumCount++;
        else highCount++;
        totalCapacity += zone.current_capacity;
        
        const zoneCard = `
            <div class="zone-card bg-slate-800 p-5 rounded-xl border-l-4 ${getDensityBorderColor(densityLevel)}">
                <div class="flex justify-between items-start mb-3">
                    <h4 class="font-bold text-white text-lg">${zone.name}</h4>
                    <span class="px-3 py-1 rounded-full text-xs font-bold ${getDensityBadgeClass(densityLevel)}">
                        ${densityLevel.toUpperCase()}
                    </span>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Occupancy</span>
                        <span class="text-white font-semibold">${zone.current_capacity} / ${zone.max_capacity}</span>
                    </div>
                    <div class="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
                        <div class="density-${densityLevel} h-full rounded-full transition-all duration-500" 
                             style="width: ${percentage}%"></div>
                    </div>
                    <div class="text-right">
                        <span class="text-gray-300 font-bold">${percentage}%</span>
                    </div>
                </div>
            </div>
        `;
        
        const containerId = categories[zone.section];
        if (containerId) {
            document.getElementById(containerId).innerHTML += zoneCard;
        }
    });
    
    document.getElementById('lowDensityCount').textContent = lowCount;
    document.getElementById('mediumDensityCount').textContent = mediumCount;
    document.getElementById('highDensityCount').textContent = highCount;
    document.getElementById('totalCapacity').textContent = totalCapacity.toLocaleString();
}

function calculateDensityLevel(current, max) {
    const ratio = current / max;
    if (ratio < 0.4) return 'low';
    if (ratio < 0.7) return 'medium';
    return 'high';
}

function getDensityBadgeClass(level) {
    const classes = {
        'low': 'bg-green-500 text-white',
        'medium': 'bg-yellow-500 text-white',
        'high': 'bg-red-500 text-white'
    };
    return classes[level] || '';
}

function getDensityBorderColor(level) {
    const colors = {
        'low': 'border-green-500',
        'medium': 'border-yellow-500',
        'high': 'border-red-500'
    };
    return colors[level] || '';
}

async function loadOrders() {
    try {
        const response = await fetch(`${API_BASE_URL}/orders`);
        const data = await response.json();
        renderOrders(data.orders);
    } catch (error) {
        console.error('Error loading orders:', error);
    }
}

function renderOrders(orders) {
    const container = document.getElementById('recentOrders');
    
    if (orders.length === 0) {
        container.innerHTML = '<p class="text-gray-400">No orders yet</p>';
        return;
    }
    
    container.innerHTML = orders.slice(0, 10).map(order => `
        <div class="bg-slate-700 p-4 rounded-lg">
            <div class="flex justify-between items-start mb-2">
                <div class="font-semibold text-white">${order.customer_name}</div>
                <span class="px-2 py-1 rounded text-xs font-bold ${getStatusBadge(order.status)}">
                    ${order.status.toUpperCase()}
                </span>
            </div>
            <div class="text-sm text-gray-300">
                <div>${order.quantity}x ${order.item_name}</div>
                <div class="text-gray-400 mt-1">📍 ${order.pickup_zone}</div>
                <div class="text-yellow-400 mt-1">⏱️ ${order.estimated_wait} min wait</div>
            </div>
        </div>
    `).join('');
}

function getStatusBadge(status) {
    const badges = {
        'pending': 'bg-yellow-500 text-white',
        'ready': 'bg-green-500 text-white',
        'completed': 'bg-blue-500 text-white'
    };
    return badges[status] || 'bg-gray-500 text-white';
}

async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/alerts`);
        const data = await response.json();
        renderAlerts(data.alerts);
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById('alertHistory');
    
    if (alerts.length === 0) {
        container.innerHTML = '<p class="text-gray-400">No alerts yet</p>';
        return;
    }
    
    container.innerHTML = alerts.map(alert => `
        <div class="bg-slate-700 p-4 rounded-lg border-l-4 ${getAlertBorderColor(alert.alert_type)}">
            <div class="flex justify-between items-start mb-2">
                <span class="font-bold ${getAlertTextColor(alert.alert_type)}">
                    ${getAlertIcon(alert.alert_type)} ${alert.alert_type.toUpperCase()}
                </span>
                <span class="text-xs text-gray-400">${formatTime(alert.created_at)}</span>
            </div>
            <div class="text-white">${alert.message}</div>
        </div>
    `).join('');
}

function showAlert(alert) {
    const banner = document.getElementById('alertBanner');
    banner.className = `alert-banner fixed top-0 left-0 right-0 z-50 p-4 text-white text-center font-semibold shadow-lg ${getAlertBannerColor(alert.alert_type)}`;
    banner.textContent = `${getAlertIcon(alert.alert_type)} ${alert.message}`;
    banner.classList.remove('hidden');
    
    setTimeout(() => banner.classList.add('hidden'), 5000);
}

function getAlertBorderColor(type) {
    const colors = {
        'info': 'border-blue-500',
        'warning': 'border-yellow-500',
        'emergency': 'border-red-500',
        'success': 'border-green-500'
    };
    return colors[type] || 'border-gray-500';
}

function getAlertTextColor(type) {
    const colors = {
        'info': 'text-blue-400',
        'warning': 'text-yellow-400',
        'emergency': 'text-red-400',
        'success': 'text-green-400'
    };
    return colors[type] || 'text-gray-400';
}

function getAlertBannerColor(type) {
    const colors = {
        'info': 'bg-blue-600',
        'warning': 'bg-yellow-600',
        'emergency': 'bg-red-600',
        'success': 'bg-green-600'
    };
    return colors[type] || 'bg-gray-600';
}

function getAlertIcon(type) {
    const icons = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'emergency': '🚨',
        'success': '✅'
    };
    return icons[type] || '📢';
}

function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
}

function updateLastUpdate() {
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}

function setupEventListeners() {
    document.getElementById('orderForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const orderData = {
            customer_name: document.getElementById('customerName').value,
            item_type: document.getElementById('itemType').value,
            item_name: document.getElementById('itemName').value,
            quantity: parseInt(document.getElementById('quantity').value),
            pickup_zone: document.getElementById('pickupZone').value
        };
        
        try {
            const response = await fetch(`${API_BASE_URL}/orders`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(orderData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                const successDiv = document.getElementById('orderSuccess');
                const messageDiv = document.getElementById('orderSuccessMessage');
                messageDiv.innerHTML = `
                    <div>Order #${result.order_id}</div>
                    <div class="text-lg font-bold mt-1">Estimated wait: ${result.estimated_wait} minutes</div>
                `;
                successDiv.classList.remove('hidden');
                document.getElementById('orderForm').reset();
                setTimeout(() => successDiv.classList.add('hidden'), 5000);
            }
        } catch (error) {
            console.error('Error placing order:', error);
            alert('Failed to place order. Please try again.');
        }
    });
    
    document.getElementById('alertForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const alertData = {
            message: document.getElementById('alertMessage').value,
            alert_type: document.getElementById('alertType').value,
            priority: document.getElementById('alertPriority').value
        };
        
        try {
            const response = await fetch(`${API_BASE_URL}/alerts`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(alertData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Alert sent successfully!');
                document.getElementById('alertForm').reset();
            }
        } catch (error) {
            console.error('Error sending alert:', error);
            alert('Failed to send alert. Please try again.');
        }
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.add('bg-slate-700');
    });
    
    document.getElementById(`${tabName}Tab`).classList.remove('hidden');
    event.target.classList.add('active');
    event.target.classList.remove('bg-slate-700');
}
