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


// --- INDEX PAGE LOGIC (Updated) ---
async function handleGeneration(event) {
    event.preventDefault();
    const generateBtn = document.getElementById('generate-btn');
    const statusMessage = document.getElementById('status-message');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating Multiple Options...';
    statusMessage.textContent = 'Applying Temporal Harmony Algorithm to generate multiple optimized timetables...';
    statusMessage.style.color = '#007bff';

    const numTimetables = parseInt(document.getElementById('num_timetables').value);
    const maxClassesPerDay = parseInt(document.getElementById('max_classes_per_day').value);
    const department = document.getElementById('department').value;
    const shift = document.getElementById('shift').value;

    const data = {
        config: {
            DAYS_OF_WEEK: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
            SLOTS_PER_DAY: 4,
            MAX_CLASSES_PER_DAY: maxClassesPerDay,
            NUM_TIMETABLES: numTimetables,
            HARMONY_MEMORY_SIZE: 20,
            PITCH_ADJUSTMENT_RATE: 0.3,
            NUM_GENERATIONS: 100,
            DEPARTMENT: department,
            SHIFT: shift
        },
        rooms: Array.from(document.querySelectorAll('#rooms-list .form-group-row')).map(row => ({
            "id": row.children[0].value,
            "name": row.children[1].value,
            "capacity": parseInt(row.children[2].value),
            "room_type": row.children[3].value,
            "department": department
        })),
        teachers: Object.fromEntries(Array.from(document.querySelectorAll('#teachers-list .form-group-row')).map(row => [
            row.children[0].value,
            {
                name: row.children[1].value,
                subjects: row.children[2].value.split(',').map(s => s.trim()),
                leaves_per_month: parseInt(row.children[3].value),
                unavailable: row.children[4].value ? row.children[4].value.split(',').map(s => s.trim()) : [],
                department: department,
                email: row.children[5].value
            }
        ])),
        batches: Object.fromEntries(Array.from(document.querySelectorAll('#batches-list .form-group-row')).map(row => [
            row.children[0].value,
            {
                name: row.children[1].value,
                size: parseInt(row.children[2].value),
                department: department,
                shift: shift
            }
        ])),
        subjects: Array.from(document.querySelectorAll('#subjects-list .form-group-column')).map(col => ({
            id: col.children[0].value,
            name: col.children[1].value,
            per_week: parseInt(col.children[2].value),
            teacher: col.children[3].value,
            batches: col.children[4].value.split(',').map(s => s.trim()),
            needs_lab: col.children[5].querySelector('input').checked,
            fixed_slots: col.children[6].value ? JSON.parse(col.children[6].value) : [],
            department: department,
            credits: parseInt(col.children[7].value)
        }))
    };

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to generate timetables.');
        }

        const result = await response.json();
        statusMessage.textContent = `Success! Generated ${result.timetables.length} optimized timetable options. Redirecting...`;
        statusMessage.style.color = '#28a745';
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 2000);

    } catch (error) {
        statusMessage.textContent = `Error: ${error.message}`;
        statusMessage.style.color = '#dc3545';
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Timetables';
    }
}

// --- DASHBOARD PAGE LOGIC (Updated) ---
async function loadDashboardData() {
    console.log("✅ Running the LATEST version of the script file! Version 4 (Multiple Timetables).");
    try {
        const response = await fetch('/api/dashboard-data');
        if (!response.ok) throw new Error('Could not fetch data.');
        const data = await response.json();
        updateDashboardUI(data);
    } catch (error) {
        console.error('Dashboard Error:', error);
        document.getElementById('timetables-container').innerHTML = `<p style="color: red;">Error loading dashboard data.</p>`;
    }
}

function updateDashboardUI(data) {
    const stats = data.stats;
    const users = data.users || [];

    // Create modern progress card
    const progressCard = document.createElement('div');
    progressCard.className = 'progress-card glass-card';
    progressCard.innerHTML = `
        <h3><i class="fas fa-chart-pie"></i> Approval Progress</h3>
        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
            <div style="font-size: 2rem; font-weight: bold; color: var(--primary-color);">
                ${stats.approved_slots}/${stats.total_slots}
            </div>
            <div style="flex: 1;">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${stats.approval_progress}%;">${stats.approval_progress.toFixed(1)}%</div>
                </div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; font-size: 0.875rem;">
            <div style="text-align: center; padding: 0.5rem; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2);">
                <div style="font-weight: bold; color: var(--success-color); font-size: 1.25rem;">${stats.approved_slots}</div>
                <div style="color: var(--text-secondary);">Approved</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.2);">
                <div style="font-weight: bold; color: var(--warning-color); font-size: 1.25rem;">${stats.total_slots - stats.approved_slots}</div>
                <div style="color: var(--text-secondary);">Pending</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(6, 182, 212, 0.1); border-radius: 8px; border: 1px solid rgba(6, 182, 212, 0.2);">
                <div style="font-weight: bold; color: var(--info-color); font-size: 1.25rem;">${stats.utilization}</div>
                <div style="color: var(--text-secondary);">Utilization</div>
            </div>
        </div>
    `;

    document.getElementById('progress-card-container').innerHTML = '';
    document.getElementById('progress-card-container').appendChild(progressCard);

    // Update analytics
    document.getElementById('analytics-utilization').textContent = stats.utilization;
    document.getElementById('analytics-load').textContent = stats.load_status;
    document.getElementById('analytics-conflicts').textContent = stats.conflicts;

    // Update leaderboard with better formatting
    const leaderboardList = document.getElementById('leaderboard-list');
    if (users.length > 0) {
        leaderboardList.innerHTML = users
            .sort((a, b) => b.points - a.points)
            .slice(0, 5)
            .map((user, index) => {
                const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '🏅';
                return `<li style="display: flex; justify-content: space-between; align-items: center;">
                    <span>${medal} ${user.username}</span>
                    <span style="font-weight: bold; color: var(--primary-color);">${user.points} pts</span>
                </li>`;
            })
            .join('');
    } else {
        leaderboardList.innerHTML = '<li style="text-align: center; color: var(--text-light);"><em>No approvals yet</em></li>';
    }

    // Update quick stats
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
    document.getElementById('active-users').textContent = users.length;
    document.getElementById('weekly-approvals').textContent = stats.approved_slots;

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