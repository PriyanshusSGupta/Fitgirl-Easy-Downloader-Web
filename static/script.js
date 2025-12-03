document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('url-input');
    const folderInput = document.getElementById('folder-input');
    const downloadBtn = document.getElementById('download-btn');
    const statusCard = document.getElementById('status-card');
    const statusText = document.getElementById('status-text');
    const percentage = document.getElementById('percentage');
    const progressBar = document.getElementById('progress-bar');
    const currentFile = document.getElementById('current-file');
    const logsContainer = document.getElementById('logs-container');
    const browseBtn = document.getElementById('browse-btn');
    const browseModal = document.getElementById('browse-modal');
    const closeModalBtns = document.querySelectorAll('.close-btn');
    const fileList = document.getElementById('file-list');
    const modalPath = document.getElementById('modal-path');
    const selectFolderBtn = document.getElementById('select-folder-btn');

    let currentBrowsePath = '/';

    // --- Download Logic ---

    downloadBtn.addEventListener('click', async () => {
        const linksText = urlInput.value.trim();
        const folder = folderInput.value.trim();

        if (!linksText) {
            addLog('error', 'Please enter at least one URL');
            return;
        }

        const links = linksText.split('\n').filter(line => line.trim() !== '');

        downloadBtn.disabled = true;
        downloadBtn.textContent = 'Starting...';
        statusCard.classList.remove('hidden');

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ links, folder })
            });

            const data = await response.json();

            if (response.ok) {
                addLog('success', 'Download queue initiated');
                startProgressStream();
            } else {
                addLog('error', data.error || 'Failed to start download');
                downloadBtn.disabled = false;
                downloadBtn.textContent = 'Start Download';
            }
        } catch (err) {
            addLog('error', 'Network error: ' + err.message);
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Start Download';
        }
    });

    function startProgressStream() {
        const eventSource = new EventSource('/api/progress');

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            // Update UI
            statusText.textContent = data.status.toUpperCase();
            percentage.textContent = Math.round(data.progress) + '%';
            progressBar.style.width = data.progress + '%';
            currentFile.textContent = data.filename || data.message;

            // Handle completed links removal
            if (data.completed_link) {
                removeLinkFromTextarea(data.completed_link);
            }

            // Update Logs
            // Clear existing logs to avoid duplicates if we were to re-render all
            // But here we just append new ones if we tracked them. 
            // Since the server sends the full list of recent logs, we can just replace.
            logsContainer.innerHTML = '';
            data.logs.forEach(log => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                if (log.includes('[ERROR]')) div.classList.add('error');
                if (log.includes('[SUCCESS]')) div.classList.add('success');
                div.textContent = log;
                logsContainer.appendChild(div);
            });
            logsContainer.scrollTop = logsContainer.scrollHeight;

            if (data.status === 'success' && data.progress === 100) {
                downloadBtn.disabled = false;
                downloadBtn.textContent = 'Start Download';
            }
        };

        eventSource.onerror = () => {
            eventSource.close();
        };
    }

    function removeLinkFromTextarea(linkToRemove) {
        const currentText = urlInput.value;
        const lines = currentText.split('\n');
        const newLines = lines.filter(line => line.trim() !== linkToRemove.trim());
        urlInput.value = newLines.join('\n');
    }

    function addLog(type, message) {
        const div = document.createElement('div');
        div.className = `log-entry ${type}`;
        div.textContent = `[${type.toUpperCase()}] ${message}`;
        logsContainer.appendChild(div);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    // --- Browse Logic ---

    browseBtn.addEventListener('click', () => {
        browseModal.classList.remove('hidden');
        loadDirectory(currentBrowsePath);
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            browseModal.classList.add('hidden');
        });
    });

    async function loadDirectory(path) {
        try {
            const response = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (response.ok) {
                currentBrowsePath = data.current_path;
                modalPath.textContent = currentBrowsePath;
                renderFileList(data.items);
            } else {
                alert('Error loading directory: ' + data.error);
            }
        } catch (err) {
            alert('Network error: ' + err.message);
        }
    }

    function renderFileList(items) {
        fileList.innerHTML = '';
        items.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="icon">📁</span> ${item.name}`;
            li.addEventListener('click', () => {
                loadDirectory(item.path);
            });
            fileList.appendChild(li);
        });
    }

    selectFolderBtn.addEventListener('click', () => {
        folderInput.value = currentBrowsePath;
        browseModal.classList.add('hidden');
    });

    const newFolderBtn = document.getElementById('new-folder-btn');
    newFolderBtn.addEventListener('click', async () => {
        const folderName = prompt("Enter new folder name:");
        if (folderName) {
            try {
                const response = await fetch('/api/mkdir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: currentBrowsePath, name: folderName })
                });
                const data = await response.json();

                if (response.ok) {
                    loadDirectory(currentBrowsePath); // Refresh
                } else {
                    alert('Error creating folder: ' + data.error);
                }
            } catch (err) {
                alert('Network error: ' + err.message);
            }
        }
    });
});
