document.addEventListener('DOMContentLoaded', function() {
    // Activate Feather Icons
    feather.replace({
        width: '1em',
        height: '1em'
    });

    // --- File Input Display ---
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

    // --- Handle Column Form Submit ---
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
            const insightsCard = document.getElementById('insights-card');

            // Clear previous results
            visualizationsDiv.innerHTML = '';
            loader.style.display = 'flex';
            insightsCard.style.display = 'none';

            // Reset insights sections
            ["correlation", "outlier", "cluster", "trend"].forEach(cat => {
                const ul = document.querySelector(`#${cat}-insights ul`);
                if (ul) ul.innerHTML = "";
                const section = document.getElementById(`${cat}-insights`);
                if (section) section.style.display = "none";
            });

            // Fetch visualizations + insights
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
                    // --- Visualization Section ---
                    let html = `
                        <div class="card results-header">
                            <h2><i data-feather="image"></i> 3. Generated Visualizations</h2>
                        </div>
                        <div class="charts-grid">
                    `;
                    for (const key in data.images) {
                        const title = key.replace(/_/g, ' ')
                                        .replace('plot ', '')
                                        .replace(/\b\w/g, l => l.toUpperCase());
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

                    // --- Insights Section ---
                    if (data.insights && data.insights.length > 0) {
                        data.insights.forEach(insight => {
                            const li = document.createElement('li');
                            li.textContent = insight.text;

                            if (insight.type && document.querySelector(`#${insight.type}-insights ul`)) {
                                document.querySelector(`#${insight.type}-insights ul`).appendChild(li);
                                document.getElementById(`${insight.type}-insights`).style.display = "block";
                            }
                        });

                        insightsCard.style.display = 'block';
                    }

                    // Re-run Feather icons for new content
                    feather.replace({ width: '1em', height: '1em' });

                    // Smooth scroll to results
                    document.getElementById('visualizations').scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                    });
                }
            })
            .catch(error => {
                loader.style.display = 'none';
                visualizationsDiv.innerHTML = `<p class="error">An unexpected error occurred. Please check the console.</p>`;
                console.error('Error:', error);
            });
        });
    }

    // --- Select All / None Button ---
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
