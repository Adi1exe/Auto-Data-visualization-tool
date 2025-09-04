        document.addEventListener('DOMContentLoaded', function() {
            // Activate Feather Icons
            feather.replace({
                width: '1em',
                height: '1em'
            });

            const fileInput = document.getElementById('file-input');
            const fileNameDisplay = document.getElementById('file-name-display');
            if (fileInput) {
                fileInput.addEventListener('change', function() {
                    if (this.files[0]) {
                        fileNameDisplay.textContent = this.files[0].name;
                    } else {
                        fileNameDisplay.textContent = 'Choose a file (.csv, .xlsx)';
                    }
                });
            }

            const columnsForm = document.getElementById('columns-form');
            if (columnsForm) {
                columnsForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const formData = new FormData(this);
                    const filename = formData.get('filename');
                    const columns = formData.getAll('columns');
                    
                    if (columns.length === 0) {
                        alert('Please select at least one column to visualize.');
                        return;
                    }

                    const visualizationsDiv = document.getElementById('visualizations');
                    const loader = document.getElementById('loader');
                    
                    visualizationsDiv.innerHTML = '';
                    loader.style.display = 'flex';

                    fetch('/visualize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename, columns })
                    })
                    .then(response => response.json())
                    .then(data => {
                        loader.style.display = 'none';
                        if (data.error) {
                            visualizationsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
                        } else {
                            let html = `
                                <div class="card results-header">
                                    <h2><i data-feather="image"></i> 3. Generated Visualizations</h2>
                                </div>
                                <div class="charts-grid">
                            `;
                            for (const key in data.images) {
                                const title = key.replace(/_/g, ' ').replace('plot ', '').replace(/\b\w/g, l => l.toUpperCase());
                                html += `
                                    <div class="chart-card">
                                        <h3>${title}</h3>
                                        <div class="chart-image-wrapper">
                                            <img src="data:image/png;base64,${data.images[key]}" alt="Chart for ${key}">
                                        </div>
                                    </div>
                                `;
                            }
                            html += '</div>';
                            visualizationsDiv.innerHTML = html;
                            feather.replace({ width: '1em', height: '1em' }); // Re-run for new icons
                            document.getElementById('visualizations').scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    })
                    .catch(error => {
                        loader.style.display = 'none';
                        visualizationsDiv.innerHTML = `<p class="error">An unexpected error occurred. Please check the console.</p>`;
                        console.error('Error:', error);
                    });
                });
            }
            
            const selectAllBtn = document.getElementById('select-all');
            if(selectAllBtn) {
                selectAllBtn.addEventListener('click', function() {
                    const checkboxes = document.querySelectorAll('#columns-form input[type="checkbox"]');
                    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = !allChecked;
                    });
                });
            }
        });