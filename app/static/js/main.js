document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const fileListContainer = document.getElementById('fileListContainer');
    const submitBtn = document.getElementById('submitBtn');
    const uploadForm = document.getElementById('uploadForm');
    const loadingSpinner = document.getElementById('loadingSpinner');

    // Drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        updateFileList(files);
    }

    // Click to select
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', function() {
        updateFileList(this.files);
    });

    // Show spinner on submit
    if(uploadForm) {
        uploadForm.addEventListener('submit', function() {
            if (fileInput.files.length > 0) {
                loadingSpinner.style.display = 'flex';
            }
        });
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async function analyzeFile(file, elementId) {
        const statusEl = document.getElementById(`status-${elementId}`);
        statusEl.innerHTML = '<span class="spinner-border spinner-border-sm text-primary"></span> 智能体检中...';
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.error) {
                statusEl.innerHTML = `<span class="text-danger small">分析失败: ${data.error}</span>`;
            } else {
                statusEl.innerHTML = `<span class="badge bg-info text-dark small">${data.type === 'native' ? '📑 原生版' : '📸 扫描件'}</span> 
                                     <span class="text-muted small ms-1">${data.details}</span>`;
                
                // If it's the only file, or we want to auto-apply first file's suggestion to global form
                if (fileInput.files.length === 1) {
                    applySuggestion(data);
                }
            }
        } catch (e) {
            statusEl.innerHTML = `<span class="text-danger small">服务连接失败</span>`;
        }
    }

    function applySuggestion(data) {
        // Mode
        const modeInput = document.querySelector(`input[name="mode"][value="${data.mode}"]`);
        if (modeInput) {
            modeInput.checked = true;
            if (typeof toggleTextInput === 'function') toggleTextInput();
        }
        
        // Threshold
        const thresholdInput = document.getElementById('thresholdRange');
        if (thresholdInput) {
            thresholdInput.value = data.threshold;
            const thresholdVal = document.getElementById('thresholdVal');
            if (thresholdVal) thresholdVal.innerText = data.threshold;
        }
        
        // Switches
        const ocrSwitch = document.getElementById('ocrSwitch');
        if (ocrSwitch) {
            ocrSwitch.checked = data.do_ocr;
            // Trigger engine select visibility
            if (typeof toggleEngineSelect === 'function') toggleEngineSelect();
        }
        
        const headerSwitch = document.getElementById('headerCleanSwitch');
        if (headerSwitch) headerSwitch.checked = data.do_header_clean;

        // OCR Engine Recommendation
        const ocrEngine = document.getElementById('ocrEngine');
        if (ocrEngine) {
            // Recommendation logic: if scanned and threshold low (likely UBS/Nomura blue), use PaddleOCR
            if (data.type === 'scanned' || data.threshold < 190) {
                ocrEngine.value = 'paddleocr';
            } else {
                ocrEngine.value = 'easyocr';
            }
        }
    }

    function updateFileList(files) {
        fileList.innerHTML = ''; 
        
        if (files.length > 0) {
            fileListContainer.style.display = 'block';
            submitBtn.disabled = false;
            
            Array.from(files).forEach((file, index) => {
                const elementId = `file-${index}`;
                const li = document.createElement('li');
                li.className = 'list-group-item bg-light border-0 mb-2 rounded shadow-sm p-3';
                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex align-items-center text-truncate">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-file-earmark-pdf-fill text-danger me-2" viewBox="0 0 16 16">
                                <path d="M5.523 12.424c.14-.082.293-.162.459-.238a7.878 7.678 0 0 1-.45.606c-.28.337-.498.516-.635.501-.136-.014-.2-.15-.141-.38.058-.225.146-.359.267-.49z"/>
                                <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/>
                            </svg>
                            <div>
                                <div class="fw-bold text-dark text-truncate" style="max-width: 400px;">${file.name}</div>
                                <div class="small text-muted">${formatFileSize(file.size)}</div>
                            </div>
                        </div>
                        <div id="status-${elementId}" class="text-end">
                            <span class="text-muted small">待分析...</span>
                        </div>
                    </div>
                `;
                fileList.appendChild(li);
                
                // Trigger Async Analysis
                analyzeFile(file, elementId);
            });
        } else {
            fileListContainer.style.display = 'none';
            submitBtn.disabled = true;
        }
    }
});