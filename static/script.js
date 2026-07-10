document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const messageText = document.getElementById('messageText');
    const fileInput = document.getElementById('fileInput');
    const dropzone = document.getElementById('dropzone');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removePreviewBtn = document.getElementById('removePreviewBtn');
    
    const addGroupForm = document.getElementById('addGroupForm');
    const groupNameInput = document.getElementById('groupNameInput');
    const groupsList = document.getElementById('groupsList');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const selectNoneBtn = document.getElementById('selectNoneBtn');
    
    const startBtn = document.getElementById('startBtn');
    const consoleLogs = document.getElementById('consoleLogs');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    let groupsData = [];
    let selectedImageFile = null;
    let eventSource = null;

    // Load initial groups
    loadGroups();
    checkRunningStatus();

    // --- Logger Helpers ---
    function log(message, type = 'system') {
        const line = document.createElement('div');
        line.className = `log-line ${type}-line`;
        
        // Formatted timestamp
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        
        line.innerText = `[${timeStr}] ${message}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // --- Load Groups ---
    async function loadGroups() {
        try {
            const response = await fetch('/api/groups');
            groupsData = await response.json();
            renderGroups();
        } catch (err) {
            log('Error loading groups: ' + err, 'error');
        }
    }

    // --- Render Groups ---
    function renderGroups() {
        groupsList.innerHTML = '';
        if (groupsData.length === 0) {
            groupsList.innerHTML = '<li class="loading-placeholder">No groups added yet.</li>';
            return;
        }
        
        groupsData.forEach((group, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="group-info">
                    <input type="checkbox" id="group_${index}" ${group.selected ? 'checked' : ''}>
                    <label for="group_${index}">${group.name}</label>
                </div>
                <button class="delete-group-btn" data-index="${index}"><i class="fa-regular fa-trash-can"></i></button>
            `;
            
            // Checkbox change listener
            const checkbox = li.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => {
                groupsData[index].selected = e.target.checked;
                saveGroupsToServer();
            });
            
            // Delete listener
            const deleteBtn = li.querySelector('.delete-group-btn');
            deleteBtn.addEventListener('click', () => {
                groupsData.splice(index, 1);
                renderGroups();
                saveGroupsToServer();
            });
            
            groupsList.appendChild(li);
        });
    }

    // --- Save Groups to Server ---
    async function saveGroupsToServer() {
        try {
            await fetch('/api/groups', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(groupsData)
            });
        } catch (err) {
            log('Error saving groups: ' + err, 'error');
        }
    }

    // --- Add Group ---
    addGroupForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = groupNameInput.value.trim();
        if (!name) return;
        
        // Prevent duplicates
        if (groupsData.some(g => g.name.toLowerCase() === name.toLowerCase())) {
            alert('Group already exists in the list.');
            return;
        }
        
        groupsData.push({ name: name, selected: true });
        groupNameInput.value = '';
        renderGroups();
        saveGroupsToServer();
    });

    // --- Select All / Clear All ---
    selectAllBtn.addEventListener('click', () => {
        groupsData.forEach(g => g.selected = true);
        renderGroups();
        saveGroupsToServer();
    });

    selectNoneBtn.addEventListener('click', () => {
        groupsData.forEach(g => g.selected = false);
        renderGroups();
        saveGroupsToServer();
    });

    // --- Drag and Drop File Upload ---
    dropzone.addEventListener('click', () => {
        if (!selectedImageFile) fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
            alert('Only image files are supported.');
            return;
        }
        selectedImageFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            previewContainer.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    }

    removePreviewBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // prevent opening file dialog
        selectedImageFile = null;
        fileInput.value = '';
        previewContainer.style.display = 'none';
        imagePreview.src = '';
    });

    // --- Check if App is running ---
    async function checkRunningStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.is_running) {
                setUIStateRunning();
                startListeningToLogs();
            }
        } catch (err) {
            console.error('Error checking status:', err);
        }
    }

    function setUIStateRunning() {
        statusDot.className = 'status-dot running';
        statusText.innerText = 'Running';
        startBtn.disabled = true;
        startBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Broadcasting...';
        
        // Disable editing inputs
        messageText.disabled = true;
        fileInput.disabled = true;
        removePreviewBtn.disabled = true;
        document.querySelectorAll('.groups-list input[type="checkbox"]').forEach(c => c.disabled = true);
        document.querySelectorAll('.delete-group-btn').forEach(b => b.disabled = true);
        document.querySelector('.add-group-form button').disabled = true;
    }

    function setUIStateIdle() {
        statusDot.className = 'status-dot idle';
        statusText.innerText = 'Idle';
        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Broadcast';
        
        // Re-enable editing inputs
        messageText.disabled = false;
        fileInput.disabled = false;
        removePreviewBtn.disabled = false;
        document.querySelectorAll('.groups-list input[type="checkbox"]').forEach(c => c.disabled = false);
        document.querySelectorAll('.delete-group-btn').forEach(b => b.disabled = false);
        document.querySelector('.add-group-form button').disabled = false;
    }

    // --- Connect to log streaming ---
    function startListeningToLogs() {
        if (eventSource) eventSource.close();
        
        eventSource = new EventSource('/stream');
        eventSource.onmessage = (event) => {
            if (event.data.trim() === '') return; // ping keep-alive
            
            const msg = event.data;
            if (msg.includes('❌') || msg.includes('💥')) {
                log(msg, 'error');
            } else if (msg.includes('✅') || msg.includes('🎉')) {
                log(msg, 'success');
            } else {
                log(msg, 'system');
            }
            
            if (msg.includes('Broadcast complete!') || msg.includes('Critical Error') || msg.includes('Browser closed.')) {
                setTimeout(() => {
                    setUIStateIdle();
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                }, 1000);
            }
        };
        eventSource.onerror = () => {
            log('Disconnected from stream log channel.', 'error');
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        };
    }

    // --- Start Broadcast Event handler ---
    startBtn.addEventListener('click', async () => {
        const text = messageText.value.trim();
        if (!text) {
            alert('Please enter a broadcast message.');
            return;
        }
        if (!selectedImageFile) {
            alert('Please select or drop an image file.');
            return;
        }
        
        const activeGroups = groupsData.filter(g => g.selected);
        if (activeGroups.length === 0) {
            alert('Please select at least one contact/group from the list.');
            return;
        }

        // Build FormData
        const formData = new FormData();
        formData.append('message', text);
        formData.append('image', selectedImageFile);

        setUIStateRunning();
        log('Starting broadcast process...', 'system');
        
        try {
            const response = await fetch('/api/broadcast', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                startListeningToLogs();
            } else {
                log('Failed to start broadcast: ' + data.message, 'error');
                setUIStateIdle();
            }
        } catch (err) {
            log('Error sending start request: ' + err, 'error');
            setUIStateIdle();
        }
    });
});
