import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from flask import Flask, request, render_template, jsonify, redirect, url_for

# Initialize Flask app
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ... (The generate_visualizations function does not need any changes) ...
def generate_visualizations(df, columns):
    """Generate various plots for the selected columns and return them as base64 encoded strings."""
    images = {}
    numeric_cols = df[columns].select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df[columns].select_dtypes(include=['object', 'category']).columns.tolist()

    # --- Set a custom retro theme for all plots ---
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': 'none',
        'axes.facecolor': 'none',
 'axes.edgecolor': '#00ffff',
        'axes.labelcolor': '#ffffff',
        'xtick.color': '#ffffff',
        'ytick.color': '#ffffff',
        'text.color': '#ffffff',
        'grid.color': '#444444',
        'font.family': 'sans-serif',
    })
    
    # --- Generate Correlation Heatmap for numeric columns ---
    if len(numeric_cols) > 1:
        try:
            plt.figure(figsize=(10, 8))
            corr = df[numeric_cols].corr()
            sns.heatmap(corr, annot=True, cmap='cool', fmt=".2f")
            plt.title('Correlation Heatmap')
            plt.tight_layout()
            
            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            plt.close()
            img.seek(0)
            images['heatmap'] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error generating heatmap: {e}")


    # --- Generate plots for individual columns ---
    for col in columns:
        try:
            plt.figure(figsize=(8, 6))
            if col in numeric_cols:
                # Histogram for numeric data
                sns.histplot(df[col], kde=True, color="#00ffff")
                plt.title(f'Distribution of {col}')

            elif col in categorical_cols:
                # Bar chart for categorical data
                sns.countplot(y=df[col], order=df[col].value_counts().index, palette='cool')
                plt.title(f'Frequency Count of {col}')

            plt.xlabel(col)
            plt.ylabel('Density' if col in numeric_cols else 'Count')
            plt.tight_layout()

            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            plt.close()
            img.seek(0)
            images[f'plot_{col}'] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error generating plot for {col}: {e}")
            
    # --- Generate Pairplot for numeric columns ---
    if len(numeric_cols) > 1:
        try:
            plt.figure()
            sns.pairplot(df[numeric_cols], plot_kws={'color': '#00ffff', 'edgecolor': '#ff00ff'})
            plt.suptitle('Pairplot of Numeric Columns', y=1.02)
            
            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            plt.close()
            img.seek(0)
            images['pairplot'] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error generating pairplot: {e}")

    return images


@app.route('/')
def index():
    """Render the main page with the upload form."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Handle the file upload and show the column selection."""
    if 'file' not in request.files:
        return render_template('index.html', error='No file part')
    
    file = request.files['file']
    
    if file.filename == '':
        return render_template('index.html', error='No selected file')
        
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Read the file into a pandas DataFrame
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Get column names and pass them to the template
            columns = df.columns.tolist()
            return render_template('index.html', columns=columns, filename=filename)
        except Exception as e:
            return render_template('index.html', error=f"Error processing file: {e}")

    return redirect(url_for('index'))


@app.route('/visualize', methods=['POST'])
def visualize():
    """Generate and return visualizations based on user's column selection."""
    data = request.get_json()
    filename = data.get('filename')
    columns = data.get('columns')

    if not filename or not columns:
        return jsonify({'error': 'Missing filename or columns'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        images = generate_visualizations(df, columns)
        
        return jsonify({'images': images})
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500


if __name__ == '__main__':
    app.run(debug=True)