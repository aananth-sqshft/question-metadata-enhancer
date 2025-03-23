// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Initial state checking - update buttons and status badges based on backend data
    checkProcessingStatus();
    
    // Toggle select all questions
    const selectAllToggle = document.getElementById('toggleSelectAll');
    const questionCheckboxes = document.querySelectorAll('.question-select');
    const processSelectedBtn = document.getElementById('processSelectedBtn');
    
    if (selectAllToggle) {
        selectAllToggle.addEventListener('change', function() {
            const isChecked = this.checked;
            questionCheckboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateSelectedButton();
        });
    }
    
    questionCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedButton);
    });
    
    function updateSelectedButton() {
        const selectedCount = document.querySelectorAll('.question-select:checked').length;
        processSelectedBtn.disabled = selectedCount === 0;
        if (selectedCount > 0) {
            processSelectedBtn.textContent = `Process Selected (${selectedCount})`;
        } else {
            processSelectedBtn.textContent = 'Process Selected';
        }
    }
    
    // Process individual question
    const processButtons = document.querySelectorAll('.process-btn');
    processButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            processQuestion(filename);
        });
    });
    
    // Process all questions
    const processAllBtn = document.getElementById('processAllBtn');
    if (processAllBtn) {
        processAllBtn.addEventListener('click', function() {
            const allFilenames = Array.from(document.querySelectorAll('tr[data-filename]'))
                .map(row => row.getAttribute('data-filename'));
            processBatch(allFilenames);
        });
    }
    
    // Process selected questions
    if (processSelectedBtn) {
        processSelectedBtn.addEventListener('click', function() {
            const selectedFilenames = Array.from(document.querySelectorAll('.question-select:checked'))
                .map(checkbox => checkbox.value);
            processBatch(selectedFilenames);
        });
    }
    
    // Check the processing status of all questions
    function checkProcessingStatus() {
        // Get all questions that have already been processed
        fetch('/images')
            .then(response => response.json())
            .then(images => {
                images.forEach(filename => {
                    fetch(`/ocr/result/${filename}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.ocr_result.success) {
                                updateQuestionStatus(filename, 'processed');
                                enableReviewButton(filename);
                            }
                        })
                        .catch(error => {
                            console.log(`Image ${filename} not yet processed`);
                        });
                });
                
                updateStatistics();
            })
            .catch(error => {
                console.error('Error loading images:', error);
            });
    }
    
    // Process a single question with OCR
    function processQuestion(filename) {
        updateQuestionStatus(filename, 'processing');
        
        fetch('/ocr/result/' + filename)
            .then(response => response.json())
            .then(data => {
                if (data.ocr_result.success) {
                    updateQuestionStatus(filename, 'processed');
                    enableReviewButton(filename);
                    updateStatistics();
                } else {
                    updateQuestionStatus(filename, 'error', data.ocr_result.error);
                }
            })
            .catch(error => {
                console.error('Error processing question:', error);
                updateQuestionStatus(filename, 'error', 'Network error');
            });
    }
    
    // Process a batch of questions
    function processBatch(filenames) {
        if (filenames.length === 0) return;
        
        const progressBar = document.querySelector('#batchProgress .progress-bar');
        const batchProgress = document.getElementById('batchProgress');
        const batchStatus = document.getElementById('batchStatus');
        
        batchProgress.classList.remove('d-none');
        progressBar.style.width = '0%';
        batchStatus.textContent = `Processing 0/${filenames.length} questions...`;
        
        let processed = 0;
        
        fetch('/ocr/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filenames: filenames })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                data.results.forEach(result => {
                    if (result.success) {
                        updateQuestionStatus(result.filename, 'processed');
                        enableReviewButton(result.filename);
                    } else {
                        updateQuestionStatus(result.filename, 'error', result.error);
                    }
                });
                
                batchStatus.textContent = `Processed ${data.processed} questions.`;
                progressBar.style.width = '100%';
                
                setTimeout(() => {
                    batchProgress.classList.add('d-none');
                }, 3000);
                
                updateStatistics();
            } else {
                batchStatus.textContent = 'Error processing batch: ' + data.error;
            }
        })
        .catch(error => {
            console.error('Error processing batch:', error);
            batchStatus.textContent = 'Network error processing batch.';
        });
    }
    
    // Update the display status of a question
    function updateQuestionStatus(filename, status, errorMsg = null) {
        const row = document.querySelector(`tr[data-filename="${filename}"]`);
        if (!row) return;
        
        const statusBadge = row.querySelector('.status-badge');
        
        statusBadge.classList.remove('bg-secondary', 'bg-warning', 'bg-success', 'bg-danger');
        
        switch(status) {
            case 'processing':
                statusBadge.classList.add('bg-warning');
                statusBadge.textContent = 'Processing...';
                break;
            case 'processed':
                statusBadge.classList.add('bg-success');
                statusBadge.textContent = 'Processed';
                break;
            case 'error':
                statusBadge.classList.add('bg-danger');
                statusBadge.textContent = 'Error';
                statusBadge.setAttribute('title', errorMsg || 'Unknown error');
                break;
            default:
                statusBadge.classList.add('bg-secondary');
                statusBadge.textContent = 'Not Processed';
        }
    }
    
    // Enable the review button for a processed question
    function enableReviewButton(filename) {
        const row = document.querySelector(`tr[data-filename="${filename}"]`);
        if (!row) return;
        
        const processBtn = row.querySelector('.process-btn');
        const reviewBtn = row.querySelector('.review-btn');
        
        processBtn.classList.add('btn-outline-secondary');
        processBtn.classList.remove('btn-outline-primary');
        reviewBtn.style.display = 'inline-block';
    }
    
    // Update statistics display
    function updateStatistics() {
        const totalQuestions = document.querySelectorAll('tr[data-filename]').length;
        const processedQuestions = document.querySelectorAll('.status-badge.bg-success').length;
        const pendingQuestions = totalQuestions - processedQuestions;
        
        document.getElementById('totalQuestions').textContent = totalQuestions;
        document.getElementById('processedQuestions').textContent = processedQuestions;
        document.getElementById('pendingQuestions').textContent = pendingQuestions;
    }
    
    // Initialize statistics
    updateStatistics();
});
