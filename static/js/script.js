document.addEventListener('DOMContentLoaded', function() {
    // Activate Feather Icons
    feather.replace({
        width: '1em',
        height: '1em'
    });

    // --- Theme Toggle (Updated) ---
    const themeToggle = document.getElementById('theme-checkbox');
    const body = document.body;

    // On page load, check saved preference
    if (localStorage.getItem('theme') === 'light') {
        body.classList.remove('dark-theme');
        if(themeToggle) themeToggle.checked = true;
    } else {
        body.classList.add('dark-theme');
        if(themeToggle) themeToggle.checked = false;
    }

    if(themeToggle) {
        themeToggle.addEventListener('change', function(e) {
            body.classList.toggle('dark-theme');
            
            // Save preference
            let theme = body.classList.contains('dark-theme') ? 'dark' : 'light';
            localStorage.setItem('theme', theme);

            // Re-run feather to update icon colors
            feather.replace();
        });
    }

    // --- File Input Display ---
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const uploadCard = document.getElementById('upload-card');

    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files[0]) {
                fileNameDisplay.textContent = this.files[0].name;
            } else {
                fileNameDisplay.textContent = 'Choose a file (.csv, .xlsx)';
            }
        });

        // Drag and drop functionality
        uploadCard.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadCard.classList.add('drag-over');
        });

        uploadCard.addEventListener('dragleave', () => {
            uploadCard.classList.remove('drag-over');
        });

        uploadCard.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadCard.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileNameDisplay.textContent = files[0].name;
            }
        });
    }

    // --- Handle Column & Graph Selection Form Submit ---
    const selectionForm = document.getElementById('selection-form');
    if (selectionForm) {
        selectionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const filename = formData.get('filename');
            const columns = formData.getAll('columns');
            const graphs = formData.getAll('graphs');
            
            // Get the current theme
            const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';

            if (columns.length === 0) {
                alert('Please select at least one column to visualize.');
                return;
            }

            if (graphs.length === 0) {
                alert('Please select at least one graph type to visualize.');
                return;
            }

            const visualizationsDiv = document.getElementById('visualizations');
            const usefulVisualizationsDiv = document.getElementById('useful-visualizations');
            const loader = document.getElementById('loader');
            const insightsCard = document.getElementById('insights-card');
            const tabsContainer = document.querySelector('.tabs-container');

            // Clear previous results
            visualizationsDiv.innerHTML = '';
            usefulVisualizationsDiv.innerHTML = '';
            loader.style.display = 'flex';
            tabsContainer.style.display = 'none';
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
                body: JSON.stringify({ filename, columns, graphs, theme: currentTheme })
            })
            .then(response => response.json())
            .then(data => {
                loader.style.display = 'none';
                tabsContainer.style.display = 'block';

                if (data.error) {
                    visualizationsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
                } else {
                    
                    // --- 1. User Selected Visualizations Section ---
                    if (data.user_selected_images && Object.keys(data.user_selected_images).length > 0) {
                        let html_selected = `<div class="charts-grid">`;
                        for (const key in data.user_selected_images) {
                            const title = key.replace(/_/g, ' ')
                                            .replace('plot ', '')
                                            .replace(/\b\w/g, l => l.toUpperCase());
                            html_selected += `
                                <div class="chart-card">
                                    <h3>${title}</h3>
                                    <div class="chart-image-wrapper">
                                        <img src="data:image/png;base64,${data.user_selected_images[key]}" alt="Chart for ${key}">
                                    </div>
                                </div>
                            `;
                        }
                        html_selected += '</div>';
                        visualizationsDiv.innerHTML = html_selected;
                    } else {
                         visualizationsDiv.innerHTML = `
                            <p style="text-align:center; color: var(--text-dim);">No visualizations generated for your selection. Try selecting different columns or graph types.</p>
                         `;
                    }

                     // --- 2. "You Might Find These Useful" Section ---
                    if (data.useful_images && Object.keys(data.useful_images).length > 0) {
                        let html_useful = `<div class="charts-grid">`;
                        for (const key in data.useful_images) {
                            const title = key.replace(/_/g, ' ')
                                            .replace('plot ', '')
                                            .replace(/\b\w/g, l => l.toUpperCase());
                            html_useful += `
                                <div class="chart-card">
                                    <h3>${title}</h3>
                                    <div class="chart-image-wrapper">
                                        <img src="data:image/png;base64,${data.useful_images[key]}" alt="Chart for ${key}">
                                    </div>
                                </div>
                            `;
                        }
                        html_useful += '</div>';
                        usefulVisualizationsDiv.innerHTML = html_useful;
                    }

                    // --- 3. Insights Section ---
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
                    document.querySelector('.tabs-container').scrollIntoView({ 
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

    // --- Tab switching --- 
    window.openTab = function(evt, tabName) {
        let i, tabcontent, tablinks;
        tabcontent = document.getElementsByClassName("tab-content");
        for (i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
        }
        tablinks = document.getElementsByClassName("tab-link");
        for (i = 0; i < tablinks.length; i++) {
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }
        document.getElementById(tabName).style.display = "block";
        evt.currentTarget.className += " active";
    }

    // --- Select All / None Button (Columns) ---
    const selectAllColumnsBtn = document.getElementById('select-all-columns');
    if(selectAllColumnsBtn) {
        selectAllColumnsBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('#selection-form input[name="columns"]');
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(checkbox => {
                checkbox.checked = !allChecked;
            });
        });
    }

    // --- Select All / None Button (Graphs) ---
    const selectAllGraphsBtn = document.getElementById('select-all-graphs');
    if(selectAllGraphsBtn) {
        selectAllGraphsBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('#selection-form input[name="graphs"]');
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(checkbox => {
                checkbox.checked = !allChecked;
            });
        });
    }
});