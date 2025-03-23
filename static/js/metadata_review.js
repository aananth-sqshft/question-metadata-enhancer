// static/js/metadata-review.js

document.addEventListener('DOMContentLoaded', function() {
    const filename = document.getElementById('questionImage').getAttribute('alt');
    let currentMetadata = null;
    
    // Load metadata and OCR text
    loadData();
    
    // Event listeners
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
    
    // Load metadata and OCR text
    function loadData() {
        // Get OCR results which include metadata
        fetch(`/ocr/result/${filename}`)
            .then(response => response.json())
            .then(data => {
                currentMetadata = data.metadata || {};
                displayMetadata(currentMetadata);
                displayOcrText(data.ocr_result.text);
            })
            .catch(error => {
                console.error('Error loading data:', error);
                document.getElementById('metadataContainer').innerHTML = `
                    <div class="alert alert-danger">
                        <p>Error loading metadata: ${error.message}</p>
                    </div>
                `;
            });
    }
    
    // Display metadata
    function displayMetadata(metadata) {
        const container = document.getElementById('metadataContainer');
        
        if (!metadata || Object.keys(metadata).length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <p>No metadata found for this question.</p>
                    <p>Process this question from the dashboard to generate metadata.</p>
                    <a href="/" class="btn btn-primary">Go to Dashboard</a>
                </div>
            `;
            return;
        }
        
        let html = '';
        
        // Technical metadata first (filename, coordinates, etc.)
        const technicalFields = ['filename', 'original_image', 'coordinates'];
        html += '<div class="metadata-card">';
        html += '<div class="metadata-card-header">Technical Information</div>';
        html += '<div class="metadata-card-body">';
        
        technicalFields.forEach(field => {
            if (metadata[field]) {
                html += `
                    <div class="row mb-2">
                        <div class="col-sm-4 text-muted">${formatKey(field)}:</div>
                        <div class="col-sm-8">${formatMetadataValueHtml(metadata[field])}</div>
                    </div>
                `;
            }
        });
        
        html += '</div></div>';
        
        // Basic metadata
        const basicFields = ['year', 'marks', 'subject', 'chapter', 'topic', 'question_type', 'difficulty_level'];
        html += '<div class="metadata-card">';
        html += '<div class="metadata-card-header">Basic Information</div>';
        html += '<div class="metadata-card-body">';
        
        basicFields.forEach(field => {
            if (field in metadata) {
                html += `
                    <div class="row mb-2">
                        <div class="col-sm-4 text-muted">${formatKey(field)}:</div>
                        <div class="col-sm-8">${formatMetadataValueHtml(metadata[field])}</div>
                    </div>
                `;
            }
        });
        
        html += '</div></div>';
        
        // Enhanced metadata
        const enhancedFields = ['keywords', 'cognitive_skills', 'topic_classification'];
        html += '<div class="metadata-card">';
        html += '<div class="metadata-card-header">Enhanced Information</div>';
        html += '<div class="metadata-card-body">';
        
        enhancedFields.forEach(field => {
            if (field in metadata) {
                html += `
                    <div class="row mb-2">
                        <div class="col-sm-4 text-muted">${formatKey(field)}:</div>
                        <div class="col-sm-8">${formatMetadataValueHtml(metadata[field])}</div>
                    </div>
                `;
            }
        });
        
        html += '</div></div>';
        
        // Cleaned text if available
        if (metadata.cleaned_text) {
            html += '<div class="metadata-card">';
            html += '<div class="metadata-card-header">Cleaned Question Text</div>';
            html += '<div class="metadata-card-body">';
            html += `<p>${metadata.cleaned_text}</p>`;
            html += '</div></div>';
        }
        
        // Other fields
        const handledFields = [...technicalFields, ...basicFields, ...enhancedFields, 'cleaned_text'];
        const otherFields = Object.keys(metadata).filter(key => !handledFields.includes(key));
        
        if (otherFields.length > 0) {
            html += '<div class="metadata-card">';
            html += '<div class="metadata-card-header">Other Information</div>';
            html += '<div class="metadata-card-body">';
            
            otherFields.forEach(field => {
                html += `
                    <div class="row mb-2">
                        <div class="col-sm-4 text-muted">${formatKey(field)}:</div>
                        <div class="col-sm-8">${formatMetadataValueHtml(metadata[field])}</div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        }
        
        container.innerHTML = html;
    }
    
    // Format metadata key for display
    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // Format metadata value as HTML
    function formatMetadataValueHtml(value) {
        if (Array.isArray(value)) {
            return `<div class="badge-row">${value.map(item => `<span class="badge bg-light text-dark">${item}</span>`).join('')}</div>`;
        } else if (typeof value === 'object' && value !== null) {
            if (value.main_topic && value.subtopics) {
                // Special handling for topic classification
                return `
                    <div>
                        <strong>${value.main_topic}</strong>
                        <div class="badge-row">
                            ${value.subtopics.map(item => `<span class="badge bg-light text-dark">${item}</span>`).join('')}
                        </div>
                    </div>
                `;
            }
            return `<pre class="mb-0 text-muted small">${JSON.stringify(value, null, 2)}</pre>`;
        }
        return value;
    }
    
    // Display OCR text
    function displayOcrText(text) {
        const container = document.getElementById('ocrTextContainer');
        
        if (!text) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <p>No OCR text available for this question.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <p class="mb-0">${text}</p>
        `;
    }
    
    // Show metadata editor
    function showMetadataEditor() {
        document.getElementById('metadataContainer').style.display = 'none';
        document.getElementById('metadataEditContainer').style.display = 'block';
        
        const container = document.getElementById('metadataEditFields');
        container.innerHTML = '';
        
        // Skip technical fields
        const skipFields = ['filename', 'original_image', 'coordinates'];
        
        Object.entries(currentMetadata).forEach(([key, value]) => {
            if (!skipFields.includes(key)) {
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
        document.getElementById('metadataContainer').style.display = 'block';
        document.getElementById('metadataEditContainer').style.display = 'none';
    }
    
    // Save metadata with edits
    function saveUpdatedMetadata() {
        const form = document.getElementById('metadataForm');
        const updatedMetadata = {...currentMetadata};
        
        // Process standard inputs
        form.querySelectorAll('input[type="text"], textarea').forEach(input => {
            const key = input.id;
            let value = input.value;
            
            if (input.tagName === 'TEXTAREA' && input.id in currentMetadata && typeof currentMetadata[input.id] === 'object') {
                try {
                    value = JSON.parse(input.value);
                } catch (e) {
                    console.error(`Error parsing JSON for ${input.id}:`, e);
                    value = currentMetadata[input.id];
                }
            }
            
            updatedMetadata[key] = value;
        });
        
        // Process array inputs
        Object.keys(currentMetadata).forEach(key => {
            if (Array.isArray(currentMetadata[key])) {
                const tags = document.querySelectorAll(`.array-tag[data-field="${key}"]`);
                updatedMetadata[key] = Array.from(tags).map(tag => tag.getAttribute('data-value'));
            }
        });
        
        // Save the updated metadata
        fetch('/metadata/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                metadata: updatedMetadata
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update local metadata
                currentMetadata = updatedMetadata;
                
                // Show updated metadata
                displayMetadata(currentMetadata);
                hideMetadataEditor();
                
                // Show success message
                document.getElementById('successMessage').style.display = 'block';
                
                // Hide success message after 5 seconds
                setTimeout(() => {
                    document.getElementById('successMessage').style.display = 'none';
                }, 5000);
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

