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

    function updateFileList(files) {
        fileList.innerHTML = ''; // Clear current list
        
        if (files.length > 0) {
            fileListContainer.style.display = 'block';
            submitBtn.disabled = false;
            
            Array.from(files).forEach(file => {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center bg-light';
                li.innerHTML = `
                    <div class="d-flex align-items-center text-truncate">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-file-earmark-pdf text-danger me-2" viewBox="0 0 16 16">
                            <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/>
                            <path d="M4.603 14.087a.81.81 0 0 1-.438-.42c-.195-.388-.13-.776.08-1.102.198-.307.526-.568.897-.787a7.68 7.68 0 0 1 3.798-.861c.297 0 .62.017.918.055.258-.09.508-.182.747-.26.23-.075.46-.145.68-.21a8.655 8.655 0 0 0-.29-.854c-.115-.29-.215-.555-.296-.78l-.055-.166c-.12-.35-.203-.64-.246-.842-.05-.232-.05-.443.013-.603.07-.175.18-.32.324-.413.144-.093.303-.136.467-.13.257.01.48.118.636.31.13.16.204.383.193.636-.013.313-.135.666-.334 1.05-.18.347-.393.68-.624.976-.188.24-.37.456-.528.633.362.338.747.665 1.137.942.378.269.742.508 1.08.694.316.174.59.324.78.413.155.073.303.14.436.195.12.05.208.08.256.096.115.038.165.047.165.047l.033.008c.026.006.05.013.064.016.035.008.082.02.13.033.228.06.465.112.72.138.254.025.5.002.684-.066.19-.07.316-.206.357-.406.026-.128.013-.254-.04-.376a.715.715 0 0 1-.164-.286c-.035-.11-.035-.23.004-.345.045-.133.125-.23.218-.266.112-.043.25-.035.39.027.14.06.24.18.28.324.045.158.003.32-.128.468-.13.15-.316.242-.513.266-.21.026-.437-.01-.646-.104-.21-.093-.38-.25-.49-.446-.104-.188-.13-.4-.085-.615.043-.215.176-.388.356-.475.163-.078.36-.073.543.012.184.086.316.257.38.452.064.194.04.4-.065.578-.105.178-.28.29-.48.318-.2.028-.415-.05-.58-.22-.164-.172-.25-.39-.244-.614a.79.79 0 0 1 .18-.5c.12-.142.29-.215.48-.21.19-.004.38.07.514.21.135.14.212.333.22.535.008.203-.06.393-.19.535-.13.143-.31.215-.503.21-.19-.005-.38-.076-.51-.217-.13-.14-.206-.33-.213-.532-.007-.203.06-.395.192-.537.132-.14.31-.212.502-.208.193.003.382.076.516.217z"/>
                        </svg>
                        <span class="text-dark" title="${file.name}">${file.name}</span>
                    </div>
                    <span class="badge bg-secondary rounded-pill ms-2">${formatFileSize(file.size)}</span>
                `;
                fileList.appendChild(li);
            });
        } else {
            fileListContainer.style.display = 'none';
            submitBtn.disabled = true;
        }
    }
});