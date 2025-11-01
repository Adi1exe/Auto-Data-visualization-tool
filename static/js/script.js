document.addEventListener('DOMContentLoaded', function() {
    // Activate Feather Icons
    feather.replace({
        width: '1em',
        height: '1em'
    });

    // --- Theme Toggle & Ripple Effect ---
    const themeToggle = document.getElementById('theme-checkbox');
    const body = document.body;
    const ripple = document.getElementById('ripple-effect');

    // On page load, check saved preference
    if (localStorage.getItem('theme') === 'light') {
        body.classList.add('light-mode');
        if(themeToggle) themeToggle.checked = true;
        feather.replace(); // Re-run feather for icons
    }

    if(themeToggle) {
        themeToggle.addEventListener('change', function(e) {
            body.classList.toggle('light-mode');
            
            // Save preference
            let theme = body.classList.contains('light-mode') ? 'light' : 'dark';
            localStorage.setItem('theme', theme);

            // --- Ripple Effect ---
            const rect = themeToggle.getBoundingClientRect();
            // Get center of the toggle switch
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;

            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            
            // Set ripple color based on new theme
            let rippleColor = theme === 'light' ? '#ffffff' : '#1a2233'; // Light ripple on dark, dark ripple on light
            ripple.style.background = rippleColor;

            ripple.style.animation = 'none';
            ripple.offsetHeight; // Trigger reflow
            ripple.style.animation = 'ripple 0.6s linear';

            // Re-run feather to update icon colors if they are set by 'color'
            feather.replace();
        });
    }


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

    // --- Handle Column & Graph Selection Form Submit ---
    const selectionForm = document.getElementById('selection-form');
    if (selectionForm) {
        selectionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const filename = formData.get('filename');
            const columns = formData.getAll('columns');
            const graphs = formData.getAll('graphs'); // Get selected graph types
            
            // **** NEW: Get the current theme ****
            const currentTheme = document.body.classList.contains('light-mode') ? 'light' : 'dark';

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

            // Clear previous results
            visualizationsDiv.innerHTML = '';
            usefulVisualizationsDiv.innerHTML = '';
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
                // **** NEW: Send the theme to the backend ****
                body: JSON.stringify({ filename, columns, graphs, theme: currentTheme })
            })
            .then(response => response.json())
            .then(data => {
                loader.style.display = 'none';
                if (data.error) {
                    visualizationsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
                } else {
                    
                    // --- 1. User Selected Visualizations Section ---
                    if (data.user_selected_images && Object.keys(data.user_selected_images).length > 0) {
                        let html_selected = `
                            <div class="card results-header">
                                <h2><i data-feather="image"></i> 4. Your Selected Visualizations</h2>
                            </div>
                            <div class="charts-grid">
                        `;
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
                            <div class="card results-header">
                                <h2><i data-feather="image"></i> 4. Your Selected Visualizations</h2>
                            </div>
                            <p style="text-align:center; color: var(--text-muted-color);">No visualizations generated for your selection. Try selecting different columns or graph types.</p>
                         `;
                    }

                     // --- 2. "You Might Find These Useful" Section ---
                    if (data.useful_images && Object.keys(data.useful_images).length > 0) {
                        let html_useful = `
                            <div class="card results-header">
                                <h2><i data-feather="gift"></i> You might find these useful</h2>
                            </div>
                            <div class.charts-grid">
                        `;
                        for (const key in data.useful_images) {
                            const title = key.replace(/_/g, ' ')
                                            .replace('plot ', '')
                                            .replace(/\b\w/g, l => l.toUpperCase());
                            html_useful += `
                                <div class="chart-card">
                                    <h3>${title}</h3>
                                    <div class.chart-image-wrapper">
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