// Global variables
let currentEquipment = null;
let timeRange = 7; // Default 7 days
let charts = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    
    // Load dashboard summary
    loadDashboardSummary();
    
    // Set up event listeners
    document.getElementById('refresh-data').addEventListener('click', refreshData);
    document.getElementById('equipment-select').addEventListener('change', function(e) {
        if (e.target.value) {
            loadEquipmentDetail(e.target.value);
        }
    });
    
    // Time range buttons
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            timeRange = parseInt(this.dataset.days);
            if (currentEquipment) {
                updateCharts(currentEquipment);
            }
        });
    });
    
    // Auto-refresh every 5 minutes
    setInterval(refreshData, 300000);
});

function loadDashboardSummary() {
    showLoading();
    
    fetch('/api/dashboard/summary')
        .then(response => response.json())
        .then(data => {
            updateSummaryStats(data.stats);
            renderEquipmentList(data.equipment);
            hideLoading();
        })
        .catch(error => {
            console.error('Error loading dashboard:', error);
            hideLoading();
            showError('Failed to load dashboard data');
        });
}

function updateSummaryStats(stats) {
    document.getElementById('total-equipment').textContent = stats.total_equipment;
    document.getElementById('critical-count').textContent = stats.critical_count;
    document.getElementById('warning-count').textContent = stats.warning_count;
    document.getElementById('healthy-count').textContent = stats.healthy_count;
    document.getElementById('avg-health').textContent = stats.avg_health_score + '%';
    document.getElementById('last-update').textContent = stats.last_update;
}

function renderEquipmentList(equipment) {
    const list = document.getElementById('equipment-list');
    list.innerHTML = '';
    
    equipment.forEach(equip => {
        const item = createEquipmentItem(equip);
        item.addEventListener('click', () => {
            document.querySelectorAll('.equipment-item').forEach(el => el.classList.remove('active'));
            item.classList.add('active');
            loadEquipmentDetail(equip.id);
        });
        list.appendChild(item);
    });
}

function createEquipmentItem(equip) {
    const div = document.createElement('div');
    div.className = 'equipment-item';
    div.dataset.id = equip.id;
    
    div.innerHTML = `
        <div class="equipment-header">
            <span class="equipment-name">${equip.name}</span>
            <span class="risk-badge ${equip.risk_level}">${equip.risk_level}</span>
        </div>
        <div class="equipment-stats">
            <div class="stat">
                <div class="stat-label">Temp</div>
                <div class="stat-value">${equip.temperature}°F</div>
            </div>
            <div class="stat">
                <div class="stat-label">Vib</div>
                <div class="stat-value">${equip.vibration}g</div>
            </div>
            <div class="stat">
                <div class="stat-label">Eff</div>
                <div class="stat-value">${equip.efficiency}%</div>
            </div>
        </div>
        <div class="health-bar">
            <div class="health-fill" style="width: ${equip.health_score}%"></div>
        </div>
        ${equip.needs_attention ? '<div class="attention-indicator">⚠️ Needs Attention</div>' : ''}
    `;
    
    return div;
}

function loadEquipmentDetail(equipmentId) {
    showLoading();
    currentEquipment = equipmentId;
    
    // Update select dropdown
    document.getElementById('equipment-select').value = equipmentId;
    
    fetch(`/api/equipment/${equipmentId}`)
        .then(response => response.json())
        .then(data => {
            renderEquipmentDetail(data);
            prepareChartData(data.historical);
            renderFailureHistory(data.failure_history);
            
            // Show chart and history sections
            document.getElementById('charts-section').style.display = 'block';
            document.getElementById('history-section').style.display = 'block';
            
            hideLoading();
        })
        .catch(error => {
            console.error('Error loading equipment detail:', error);
            hideLoading();
            showError('Failed to load equipment details');
        });
}

function renderEquipmentDetail(data) {
    const detailDiv = document.getElementById('equipment-detail');
    
    detailDiv.innerHTML = `
        <div class="equipment-info">
            <h3>${data.equipment_name}</h3>
            <p class="equipment-type">Type: ${data.equipment_type}</p>
        </div>
        
        <div class="current-readings">
            <div class="reading-card">
                <div class="reading-label">Temperature</div>
                <div class="reading-value">${data.current_temp}<span class="reading-unit">°F</span></div>
                <div class="reading-trend ${getTrendClass(data.temp_trend)}">
                    ${getTrendIcon(data.temp_trend)} ${data.temp_trend}
                </div>
            </div>
            <div class="reading-card">
                <div class="reading-label">Vibration</div>
                <div class="reading-value">${data.current_vibration}<span class="reading-unit">g</span></div>
                <div class="reading-trend ${getTrendClass(data.vib_trend)}">
                    ${getTrendIcon(data.vib_trend)} ${data.vib_trend}
                </div>
            </div>
            <div class="reading-card">
                <div class="reading-label">Efficiency</div>
                <div class="reading-value">${data.current_efficiency}<span class="reading-unit">%</span></div>
                <div class="reading-trend ${getTrendClass(data.eff_trend)}">
                    ${getTrendIcon(data.eff_trend)} ${data.eff_trend}
                </div>
            </div>
        </div>
        
        <div class="prediction-card">
            <div class="prediction-header">
                <h3>Maintenance Prediction</h3>
                <span class="priority-badge">${data.prediction.priority}</span>
            </div>
            <div class="risk-meter">
                <div class="risk-bar">
                    <div class="risk-fill" style="width: ${data.prediction.risk_score}%"></div>
                </div>
                <div class="risk-labels">
                    <span>Low Risk</span>
                    <span>Risk Score: ${data.prediction.risk_score}%</span>
                    <span>High Risk</span>
                </div>
            </div>
            <div class="recommendation">
                <strong>Recommendation:</strong> ${data.prediction.recommendation}
            </div>
            ${data.prediction.reasons && data.prediction.reasons.length > 0 ? `
                <div class="reasons">
                    <strong>Reasons:</strong>
                    <ul>
                        ${data.prediction.reasons.map(reason => `<li>${reason}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
        
        <div class="additional-info">
            <div class="info-row">
                <span class="info-label">Health Score:</span>
                <span class="info-value ${getHealthScoreClass(data.health_score)}">${data.health_score}%</span>
            </div>
            <div class="info-row">
                <span class="info-label">Usage Hours:</span>
                <span class="info-value">${data.current_hours.toLocaleString()} hrs</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last Maintenance:</span>
                <span class="info-value">${data.last_maintenance}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Days Until Maintenance:</span>
                <span class="info-value">${data.days_until_maintenance} days</span>
            </div>
        </div>
    `;
}

function prepareChartData(historical) {
    // Filter data based on time range
    const pointsToShow = timeRange * 24; // hourly data
    const startIdx = Math.max(0, historical.timestamps.length - pointsToShow);
    
    const timestamps = historical.timestamps.slice(startIdx);
    const temperature = historical.temperature.slice(startIdx);
    const vibration = historical.vibration.slice(startIdx);
    const efficiency = historical.efficiency.slice(startIdx);
    const health = historical.health_score.slice(startIdx);
    
    // Create/update charts
    createChart('temp-chart', 'Temperature (°F)', timestamps, temperature, '#e74c3c');
    createChart('vibration-chart', 'Vibration (g)', timestamps, vibration, '#f39c12');
    createChart('efficiency-chart', 'Efficiency (%)', timestamps, efficiency, '#27ae60');
    createChart('health-chart', 'Health Score (%)', timestamps, health, '#3498db');
}

function createChart(elementId, title, timestamps, values, color) {
    const trace = {
        x: timestamps,
        y: values,
        type: 'scatter',
        mode: 'lines',
        name: title,
        line: {
            color: color,
            width: 2
        }
    };
    
    const layout = {
        title: title,
        xaxis: {
            title: 'Time',
            showgrid: true
        },
        yaxis: {
            title: title,
            showgrid: true
        },
        margin: {
            l: 50,
            r: 20,
            t: 40,
            b: 40
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };
    
    Plotly.newPlot(elementId, [trace], layout, {responsive: true});
}

function updateCharts(equipmentId) {
    // Reload equipment data with new time range
    fetch(`/api/equipment/${equipmentId}`)
        .then(response => response.json())
        .then(data => {
            prepareChartData(data.historical);
        });
}

function renderFailureHistory(failures) {
    const historyDiv = document.getElementById('failure-history');
    
    if (failures.length === 0) {
        historyDiv.innerHTML = '<p class="no-data">No failures recorded in this period</p>';
        return;
    }
    
    historyDiv.innerHTML = failures.map(failure => `
        <div class="failure-item">
            <span class="failure-time">${failure.timestamp}</span>
            <span class="failure-type">${failure.type}</span>
            <span class="failure-severity">Severity: ${Math.round(failure.severity)}%</span>
        </div>
    `).join('');
}

function refreshData() {
    showLoading();
    
    fetch('/api/refresh-data')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload everything
                loadDashboardSummary();
                if (currentEquipment) {
                    loadEquipmentDetail(currentEquipment);
                }
            }
            hideLoading();
        })
        .catch(error => {
            console.error('Error refreshing data:', error);
            hideLoading();
            showError('Failed to refresh data');
        });
}

// Utility functions
function getTrendClass(trend) {
    if (trend === 'increasing') return 'trend-up';
    if (trend === 'decreasing') return 'trend-down';
    return 'trend-stable';
}

function getTrendIcon(trend) {
    if (trend === 'increasing') return '↑';
    if (trend === 'decreasing') return '↓';
    return '→';
}

function getHealthScoreClass(score) {
    if (score >= 80) return 'health-good';
    if (score >= 60) return 'health-warning';
    if (score >= 40) return 'health-critical';
    return 'health-extreme';
}

function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    // Simple alert for now - could be enhanced with a toast notification
    alert('Error: ' + message);
}