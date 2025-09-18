document.addEventListener('DOMContentLoaded', () => {
    // Check which page we are on
    if (document.getElementById('timetable-form')) {
        // --- START OF THE CHANGE ---
        // Setup listeners for the buttons
        document.getElementById('timetable-form').addEventListener('submit', handleGeneration);
        document.getElementById('load-sample-data').addEventListener('click', loadSampleData);
        
        // Initialize the form with two empty fields for each category
        initializeEmptyForm();
        // --- END OF THE CHANGE ---

    } else if (document.querySelector('.dashboard-container')) {
        // We are on the dashboard page
        loadDashboardData();
    }
});

// --- NEW FUNCTION TO SETUP A BLANK FORM ---
function initializeEmptyForm() {
    // Clear any existing fields first to ensure a clean slate
    document.getElementById('rooms-list').innerHTML = '';
    document.getElementById('teachers-list').innerHTML = '';
    document.getElementById('batches-list').innerHTML = '';
    document.getElementById('subjects-list').innerHTML = '';

    // Add 2 of each field type by default, but leave them blank
    // The placeholder text will now be visible
    addRoom();
    addRoom();

    addTeacher();
    addTeacher();

    addBatch();
    addBatch();

    addSubject();
    addSubject();
}


// --- INDEX PAGE LOGIC (Unchanged) ---
async function handleGeneration(event) {
    event.preventDefault();
    const generateBtn = document.getElementById('generate-btn');
    const statusMessage = document.getElementById('status-message');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating... Please Wait...';
    statusMessage.textContent = 'Applying Temporal Harmony Algorithm... This may take a moment.';
    statusMessage.style.color = '#007bff';
    const data = {
        config: { DAYS_OF_WEEK: document.getElementById('days').value.split(',').map(s => s.trim()), SLOTS_PER_DAY: parseInt(document.getElementById('slots').value), NUM_GENERATIONS: 100, },
        rooms: Array.from(document.querySelectorAll('#rooms-list .form-group-row')).map(row => ({"id": row.children[0].value, "capacity": parseInt(row.children[1].value)})),
        teachers: Object.fromEntries(Array.from(document.querySelectorAll('#teachers-list .form-group-row')).map(row => [row.children[0].value, { name: row.children[1].value, unavailable: row.children[2].value ? row.children[2].value.split(',').map(s => { const parts = s.trim().split(' '); return [parts[0], parseInt(parts[1])]; }) : [] }])),
        batches: Object.fromEntries(Array.from(document.querySelectorAll('#batches-list .form-group-row')).map(row => [row.children[0].value, { name: row.children[1].value, size: parseInt(row.children[2].value) }])),
        subjects: Array.from(document.querySelectorAll('#subjects-list .form-group-column')).map(col => ({ id: col.children[0].value, name: col.children[1].value, per_week: parseInt(col.children[2].value), teacher: col.children[3].value, batches: col.children[4].value.split(',').map(s => s.trim()), needs_lab: col.children[5].querySelector('input').checked }))
    };
    try {
        const response = await fetch('/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (!response.ok) { const error = await response.json(); throw new Error(error.error || 'Failed to generate timetable.'); }
        statusMessage.textContent = 'Success! Redirecting...';
        statusMessage.style.color = '#28a745';
        window.location.href = '/dashboard';
    } catch (error) {
        statusMessage.textContent = `Error: ${error.message}`;
        statusMessage.style.color = '#dc3545';
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate & Go to Dashboard';
    }
}

// --- DASHBOARD PAGE LOGIC (Unchanged) ---
async function loadDashboardData() {
    console.log("✅ Running the LATEST version of the script file! Version 3 (Day Sort Fix).");
    try {
        const response = await fetch('/api/dashboard-data');
        if (!response.ok) throw new Error('Could not fetch data.');
        const data = await response.json();
        if (!data.timetable || data.timetable.length === 0) {
            document.getElementById('timetables-container').innerHTML = `<div id="output-placeholder"><h2>No Timetable Generated</h2><p>Please go to the main page to generate a timetable.</p></div>`;
            return;
        }
        updateDashboardUI(data);
    } catch (error) {
        console.error('Dashboard Error:', error);
        document.getElementById('timetables-container').innerHTML = `<p style="color: red;">Error loading dashboard data.</p>`;
    }
}

function updateDashboardUI(data) {
    const stats = data.stats;
    document.getElementById('progress-card-container').innerHTML = `<div class="progress-card"><h3>Approval Progress: ${stats.approved_slots} / ${stats.total_slots} Slots Approved</h3><div class="progress-bar-container"><div class="progress-bar" style="width: ${stats.approval_progress}%;">${stats.approval_progress}%</div></div></div>`;
    document.getElementById('analytics-utilization').textContent = stats.utilization;
    document.getElementById('analytics-load').textContent = stats.load_status;
    document.getElementById('analytics-conflicts').textContent = stats.conflicts;
    const leaderboardList = document.getElementById('leaderboard-list');
    leaderboardList.innerHTML = data.users.map(user => `<li>${user.username} - <strong>${user.points} pts</strong></li>`).join('');
    renderTimetables(data.timetable);
}

function renderTimetables(slots) {
    const container = document.getElementById('timetables-container');
    container.innerHTML = '';
    if (!slots || slots.length === 0) {
        container.innerHTML = `<div id="output-placeholder"><h2>No classes were scheduled.</h2><p>The algorithm ran successfully, but the constraints were too strict. Please try again with fewer restrictions.</p></div>`;
        return;
    }
    const batches = [...new Set(slots.map(s => s.batch_name))].sort();
    const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const days = [...new Set(slots.map(s => s.day))];
    days.sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));
    const maxSlots = slots.length > 0 ? Math.max(...slots.map(s => s.slot_index)) + 1 : 0;
    for (const batchName of batches) {
        const tableContainer = document.createElement('div');
        tableContainer.className = 'timetable-table';
        let tableHTML = `<h2>Timetable for ${batchName}</h2><table><thead><tr><th>Day/Time</th>`;
        for (let i = 0; i < maxSlots; i++) { tableHTML += `<th>Slot ${i + 1}</th>`; }
        tableHTML += '</tr></thead><tbody>';
        for (const day of days) {
            tableHTML += `<tr><td>${day}</td>`;
            for (let i = 0; i < maxSlots; i++) {
                const slot = slots.find(s => s.batch_name === batchName && s.day === day && s.slot_index === i);
                if (slot) {
                    tableHTML += `<td id="slot-${slot.id}" class="slot-cell status-${slot.approval_status}"><div class="lecture-subject">${slot.subject_name}</div><div class="lecture-teacher">${slot.teacher_name}</div><div class="lecture-room">@ ${slot.room_id}</div><div class="approval-actions"><button class="btn-approve" onclick="approveSlot(${slot.id})" title="Approve">&#10004;</button><button class="btn-reject" onclick="requestChange(${slot.id})" title="Request Change">&#10006;</button></div></td>`;
                } else { tableHTML += '<td>-</td>'; }
            }
            tableHTML += '</tr>';
        }
        tableHTML += '</tbody></table>';
        tableContainer.innerHTML = tableHTML;
        container.appendChild(tableContainer);
    }
}

async function approveSlot(slotId) {
    const cell = document.getElementById(`slot-${slotId}`);
    cell.className = 'slot-cell status-approved';
    try {
        const response = await fetch(`/api/approve/${slotId}`, { method: 'POST' });
        if (!response.ok) throw new Error('Approval failed on server.');
        const data = await response.json();
        // We don't need to reload the whole page, just update the UI
        loadDashboardData();
    } catch (error) { 
        alert(`Error: ${error.message}`);
        cell.className = 'slot-cell status-pending';
    }
}
async function requestChange(slotId) {
    const reason = prompt("Please provide a reason for the change request:");
    if (!reason) return;
    const cell = document.getElementById(`slot-${slotId}`);
    cell.className = 'slot-cell status-change_requested';
    try {
        const response = await fetch(`/api/request_change/${slotId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }) });
        if (!response.ok) throw new Error('Request failed on server.');
        const data = await response.json();
        // We don't need to reload the whole page, just update the UI
        loadDashboardData();
    } catch (error) { 
        alert(`Error: ${error.message}`);
        cell.className = 'slot-cell status-pending';
    }
}

// --- Form Helper and Sample Data Functions ---
// These addRow, etc., functions are now used by both initializeEmptyForm and loadSampleData
function addRoom(id = '', capacity = '') { const list = document.getElementById('rooms-list'); const item = document.createElement('div'); item.className = 'form-group-row'; item.innerHTML = `<input type="text" placeholder="Room ID (e.g., R1)" value="${id}" required><input type="number" placeholder="Capacity (e.g., 40)" value="${capacity}" min="1" required><button type="button" class="btn-remove" onclick="this.parentElement.remove()">-</button>`; list.appendChild(item); }
function addTeacher(id = '', name = '', unavailable = '') { const list = document.getElementById('teachers-list'); const item = document.createElement('div'); item.className = 'form-group-row'; item.innerHTML = `<input type="text" placeholder="Teacher ID (e.g., T1)" value="${id}" required><input type="text" placeholder="Name (e.g., Dr. Smith)" value="${name}" required><input type="text" placeholder="Unavailable (e.g., Mon 0, Tue 2)" value="${unavailable}"><button type="button" class="btn-remove" onclick="this.parentElement.remove()">-</button>`; list.appendChild(item); }
function addBatch(id = '', name = '', size = '') { const list = document.getElementById('batches-list'); const item = document.createElement('div'); item.className = 'form-group-row'; item.innerHTML = `<input type="text" placeholder="Batch ID (e.g., B1)" value="${id}" required><input type="text" placeholder="Name (e.g., CS 1st Year)" value="${name}" required><input type="number" placeholder="Size (e.g., 50)" value="${size}" min="1" required><button type="button" class="btn-remove" onclick="this.parentElement.remove()">-</button>`; list.appendChild(item); }
function addSubject(id = '', name = '', perWeek = '', teacher = '', batches = '', needsLab = false) { const list = document.getElementById('subjects-list'); const item = document.createElement('div'); item.className = 'form-group-column'; item.innerHTML = `<input type="text" placeholder="Subject ID (e.g., S1)" value="${id}" required><input type="text" placeholder="Name (e.g., Intro to CS)" value="${name}" required><input type="number" placeholder="Classes per Week (e.g., 4)" value="${perWeek}" min="1" required><input type="text" placeholder="Teacher ID (e.g., T1)" value="${teacher}" required><input type="text" placeholder="Batch IDs (e.g., B1,B2)" value="${batches}" required><label class="checkbox-label"><input type="checkbox" ${needsLab ? 'checked' : ''}> Needs Lab?</label><button type="button" class="btn-remove" onclick="this.parentElement.remove()">-</button>`; list.appendChild(item); }

// This function still works for the "Load Sample Data" button
function loadSampleData() {
    document.getElementById('rooms-list').innerHTML = '';
    document.getElementById('teachers-list').innerHTML = '';
    document.getElementById('batches-list').innerHTML = '';
    document.getElementById('subjects-list').innerHTML = '';
    addRoom('R1', 40); addRoom('R2', 30); addRoom('R3', 50); addRoom('LAB1', 30);
    addTeacher('T1', 'Dr. Smith', 'Wed 2'); addTeacher('T2', 'Prof. Jones', ''); addTeacher('T3', 'Dr. Davis', 'Fri 4');
    addBatch('B1', 'CS 1st Year', 35); addBatch('B2', 'IT 2nd Year', 28);
    addSubject('S1', 'Intro to CS', 4, 'T1', 'B1', false);
    addSubject('S2', 'Data Structures', 4, 'T2', 'B2', false);
    addSubject('S3', 'Web Dev Lab', 3, 'T3', 'B2', true);
    addSubject('S4', 'Calculus', 5, 'T1', 'B1', false);
}