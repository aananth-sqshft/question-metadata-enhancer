// static/js/ocr-review.js

document.addEventListener('DOMContentLoaded', function() {
    // Get filename from URL path
    const pathParts = window.location.pathname.split('/');
    const filename = pathParts[pathParts.length - 1];
    
    let currentOcrText = '';
    let existingMetadata = null;
    let enhancedMetadata = null;
    
    // Load OCR results and metadata
    loadOcrResult();
    
    // Form submissions
    document.getElementById('ocrForm').addEventListener('submit', function(e) {
        e.preventDefault();
        submitForAnalysis();
    });
    
    document.getElementById('reprocessBtn').addEventListener('click', function() {
        loadOcrResult(true);
    });
    
    document.getElementById('editMetadataBtn').addEventListener('click', function() {
        showMetadataEditor();
    });
    
    document.getElementById('cancelEditBtn').addEventListener('click', function() {
        hideMetadataEditor();
    });
    
    document.getElementById('metadataForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveUpdatedMetadata();
    });
    
    document.getElementById('saveMetadataBtn').addEventListener('click', function() {
        saveMetadata();
    });
    
    // Load OCR result and existing metadata
    function loadOcrResult(forceReprocess = false) {
        const apiUrl = forceReprocess ? 
            `/ocr/process` : 
            `/ocr/result/${filename}`;
        
        const method = forceReprocess ? 'POST' : 'GET';
        const body = forceReprocess ? 
            JSON.stringify({ filenames: [filename] }) : 
            null;
        
        fetch(apiUrl, {
            method: method,
            headers: forceReprocess ? { 'Content-Type': 'application/json' } : {},
            body: body
        })
        .then(response => response.json())
        .then(data => {
            let result;
            if (forceReprocess) {
                // Extract the result for this specific file from the batch results
                result = data.results.find(r => r.filename === filename);
                if (!result) {
                    throw new Error('Result not found in response');
                }
            } else {
                result = data.ocr_result;
                existingMetadata = data.metadata;
            }
            
            // Display OCR text
            currentOcrText = result.text;
            displayOcrText(result.text, result.success, result.error);
            
            // Display existing metadata
            displayExistingMetadata(existingMetadata);
        })
        .catch(error => {
            console.error('Error loading OCR result:', error);
            displayOcrText('', false, 'Error loading OCR result: ' + error.message);
        });
    }
    
    // Display OCR text
    function displayOcrText(text, success, error = null) {
        const container = document.getElementById('ocrTextContainer');
        const editContainer = document.getElementById('ocrEditContainer');
        const textArea = document.getElementById('ocrText');
        
        if (success) {
            // Show the edit form
            container.innerHTML = '';
            editContainer.style.display = 'block';
            textArea.value = text;
        } else {
            // Show error message
            container.innerHTML = `
                <div class="alert alert-danger">
                    <h5>OCR Processing Failed</h5>
                    <p>${error || 'Unknown error occurred during OCR processing.'}</p>
                    <button id="retryOcrBtn" class="btn btn-danger mt-2">Retry OCR</button>
                </div>
            `;
            editContainer.style.display = 'none';
            
            document.getElementById('retryOcrBtn').addEventListener('click', function() {
                loadOcrResult(true);
            });
        }
    }
    
    // Display existing metadata
    function displayExistingMetadata(metadata) {
        const container = document.getElementById('existingMetadata');
        
        if (!metadata) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <p>No existing metadata found for this question.</p>
                </div>
            `;
            return;
        }
        
        let html = '<dl class="row">';
        
        // Filter out technical fields
        const ignoreFields = ['filename', 'coordinates', 'original_image'];
        
        Object.entries(metadata).forEach(([key, value]) => {
            if (!ignoreFields.includes(key) && value) {
                html += `
                    <dt class="col-sm-4">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</dt>
                    <dd class="col-sm-8">${formatMetadataValue(value)}</dd>
                `;
            }
        });
        
        html += '</dl>';
        container.innerHTML = html;
    }
    
    // Format metadata values for display
    function formatMetadataValue(value) {
        if (Array.isArray(value)) {
            return value.join(', ');
        } else if (typeof value === 'object' && value !== null) {
            return JSON.stringify(value);
        }
        return value;
    }
    
    // Submit OCR text for LLM analysis
    function submitForAnalysis() {
        const ocrText = document.getElementById('ocrText').value.trim();
        
        if (!ocrText) {
            alert('Please provide OCR text for analysis.');
            return;
        }
        
        // Show LLM analysis card and loading state
        document.getElementById('llmAnalysisCard').style.display = 'block';
        document.getElementById('llmAnalysisContainer').style.display = 'block';
        document.getElementById('metadataPreviewContainer').style.display = 'none';
        document.getElementById('metadataEditContainer').style.display = 'none';
        
        // Call the LLM analysis API
        fetch('/llm/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                ocr_text: ocrText
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                enhancedMetadata = data.metadata;
                displayMetadataPreview(enhancedMetadata);
            } else {
                let errorMessage = data.error || 'Unknown error during LLM analysis';
                console.error('LLM Analysis Error:', errorMessage);
                if (data.metadata && data.metadata.detailed_error) {
                    console.error('Detailed error:', data.metadata.detailed_error);
                }
                throw new Error(errorMessage);
            }
        })
        .catch(error => {
            console.error('Error during LLM analysis:', error);
            document.getElementById('llmAnalysisContainer').innerHTML = `
                <div class="alert alert-danger">
                    <h5>LLM Analysis Failed</h5>
                    <p>${error.message || 'An error occurred during LLM analysis.'}</p>
                    <button id="retryLlmBtn" class="btn btn-danger mt-2">Retry Analysis</button>
                </div>
            `;
            
            document.getElementById('retryLlmBtn').addEventListener('click', function() {
                submitForAnalysis();
            });
        });
    }
    
    // Display metadata preview
    function displayMetadataPreview(metadata) {
        document.getElementById('llmAnalysisContainer').style.display = 'none';
        document.getElementById('metadataPreviewContainer').style.display = 'block';
        
        const container = document.getElementById('metadataPreview');
        let html = '';
        
        Object.entries(metadata).forEach(([key, value]) => {
            if (key !== 'error' && key !== 'raw_response') {
                html += `
                    <div class="metadata-item">
                        <span class="key">${formatKey(key)}:</span> 
                        <span class="value">${formatMetadataValueHtml(value)}</span>
                    </div>
                `;
            }
        });
        
        container.innerHTML = html;
    }
    
    // Format metadata key for display
    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // Format metadata value as HTML
    function formatMetadataValueHtml(value) {
        if (Array.isArray(value)) {
            return value.map(item => `<span class="badge bg-light text-dark me-1">${item}</span>`).join('');
        } else if (typeof value === 'object' && value !== null) {
            return `<pre class="mb-0 text-muted">${JSON.stringify(value, null, 2)}</pre>`;
        }
        return value;
    }
    
    // Show metadata editor
    function showMetadataEditor() {
        document.getElementById('metadataPreviewContainer').style.display = 'none';
        document.getElementById('metadataEditContainer').style.display = 'block';
        
        const container = document.getElementById('metadataEditFields');
        container.innerHTML = '';
        
        Object.entries(enhancedMetadata).forEach(([key, value]) => {
            if (key !== 'error' && key !== 'raw_response') {
                let input = '';
                
                if (Array.isArray(value)) {
                    input = createArrayInput(key, value);
                } else if (typeof value === 'object' && value !== null) {
                    input = createObjectInput(key, value);
                } else {
                    input = `
                        <div class="form-group">
                            <label for="${key}">${formatKey(key)}</label>
                            <input type="text" class="form-control" id="${key}" name="${key}" value="${value || ''}">
                        </div>
                    `;
                }
                
                container.innerHTML += input;
            }
        });
        
        // Add event listeners for array inputs
        document.querySelectorAll('.add-tag-input').forEach(input => {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const field = this.getAttribute('data-field');
                    const value = this.value.trim();
                    
                    if (value) {
                        addArrayItem(field, value);
                        this.value = '';
                    }
                }
            });
        });
        
        document.querySelectorAll('.add-tag-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const field = this.getAttribute('data-field');
                const input = document.querySelector(`.add-tag-input[data-field="${field}"]`);
                const value = input.value.trim();
                
                if (value) {
                    addArrayItem(field, value);
                    input.value = '';
                }
            });
        });
        
        // Add remove tag listeners
        document.querySelectorAll('.remove-tag').forEach(btn => {
            btn.addEventListener('click', function() {
                this.parentElement.remove();
            });
        });
    }
    
    // Create input for array values
    function createArrayInput(key, values) {
        let html = `
            <div class="form-group">
                <label>${formatKey(key)}</label>
                <div id="${key}-tags" class="array-input">
        `;
        
        values.forEach(value => {
            html += createArrayTag(key, value);
        });
        
        html += `
                </div>
                <div class="input-group">
                    <input type="text" class="form-control add-tag-input" data-field="${key}" placeholder="Add new item">
                    <button type="button" class="btn btn-outline-secondary add-tag-btn" data-field="${key}">Add</button>
                </div>
            </div>
        `;
        
        return html;
    }
    
    // Create tag element for array items
    function createArrayTag(field, value) {
        return `
            <span class="array-tag" data-field="${field}" data-value="${value}">
                ${value}
                <span class="remove-tag">&times;</span>
            </span>
        `;
    }
    
    // Add item to array input
    function addArrayItem(field, value) {
        const tagsContainer = document.getElementById(`${field}-tags`);
        const tag = document.createElement('span');
        tag.className = 'array-tag';
        tag.setAttribute('data-field', field);
        tag.setAttribute('data-value', value);
        tag.innerHTML = `${value} <span class="remove-tag">&times;</span>`;
        
        tagsContainer.appendChild(tag);
        
        tag.querySelector('.remove-tag').addEventListener('click', function() {
            tag.remove();
        });
    }
    
    // Create input for object values
    function createObjectInput(key, obj) {
        return `
            <div class="form-group">
                <label for="${key}">${formatKey(key)}</label>
                <textarea class="form-control" id="${key}" name="${key}" rows="4">${JSON.stringify(obj, null, 2)}</textarea>
            </div>
        `;
    }
    
    // Hide metadata editor
    function hideMetadataEditor() {
        document.getElementById('metadataPreviewContainer').style.display = 'block';
        document.getElementById('metadataEditContainer').style.display = 'none';
    }
    
    // Save metadata with edits
    function saveUpdatedMetadata() {
        const form = document.getElementById('metadataForm');
        const updatedMetadata = {};
        
        // Process standard inputs
        form.querySelectorAll('input[type="text"], textarea').forEach(input => {
            const key = input.id;
            let value = input.value;
            
            if (input.tagName === 'TEXTAREA' && input.id in enhancedMetadata && typeof enhancedMetadata[input.id] === 'object') {
                try {
                    value = JSON.parse(input.value);
                } catch (e) {
                    console.error(`Error parsing JSON for ${input.id}:`, e);
                    value = enhancedMetadata[input.id];
                }
            }
            
            updatedMetadata[key] = value;
        });
        
        // Process array inputs
        Object.keys(enhancedMetadata).forEach(key => {
            if (Array.isArray(enhancedMetadata[key])) {
                const tags = document.querySelectorAll(`.array-tag[data-field="${key}"]`);
                updatedMetadata[key] = Array.from(tags).map(tag => tag.getAttribute('data-value'));
            }
        });
        
        // Save the updated metadata
        enhancedMetadata = updatedMetadata;
        displayMetadataPreview(updatedMetadata);
        hideMetadataEditor();
        
        // Automatically save
        saveMetadata();
    }
    
    // Save metadata to server
    function saveMetadata() {
        fetch('/metadata/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                metadata: enhancedMetadata
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                document.getElementById('llmAnalysisCard').style.display = 'none';
                document.getElementById('successMessage').style.display = 'block';
            } else {
                throw new Error(data.error || 'Failed to save metadata');
            }
        })
        .catch(error => {
            console.error('Error saving metadata:', error);
            alert('Error saving metadata: ' + error.message);
        });
    }
});

