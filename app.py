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

def generate_insights(df):
    """Generate business-friendly hidden pattern insights and related visualizations."""
    insights = []
    images = {}

    # ---- 1. Correlation Insights ----
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr().abs()
        corr_pairs = (
            corr.unstack()
            .sort_values(ascending=False)
            .drop_duplicates()
        )
        top_corrs = corr_pairs[(corr_pairs < 1)].head(3)
        for (col1, col2), val in top_corrs.items():
            insights.append({
                "type": "correlation",
                "text": f"As {col1} increases, {col2} also tends to increase ({val:.0%} relationship)."
            })

        # Plot top correlations
        try:
            plt.figure(figsize=(6, 4))
            top_corrs.plot(kind="bar", color="#00ffff")
            plt.title("Top Correlations")
            plt.ylabel("Strength")
            plt.xticks(rotation=45)
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format="png", transparent=True)
            plt.close()
            img.seek(0)
            images["top_correlations"] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error plotting correlations: {e}")

    # ---- 2. Outlier Detection ----
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = df[(df[col] < lower) | (df[col] > upper)][col]
        if len(outliers) > 0:
            insights.append({
                "type": "outlier",
                "text": f"{len(outliers)} unusual values found in {col} — possible errors or special cases."
            })

            # Boxplot
            try:
                plt.figure(figsize=(5, 4))
                sns.boxplot(x=df[col], color="#ff00ff")
                plt.title(f"Outliers in {col}")
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format="png", transparent=True)
                plt.close()
                img.seek(0)
                images[f"outliers_{col}"] = base64.b64encode(img.getvalue()).decode()
            except Exception as e:
                print(f"Error plotting boxplot for {col}: {e}")

    # ---- 3. Clustering ----
    if len(numeric_cols) >= 2:
        try:
            from sklearn.cluster import KMeans
            sample = df[numeric_cols].dropna().sample(min(500, len(df)), random_state=42)
            kmeans = KMeans(n_clusters=3, random_state=42).fit(sample)
            sample["Cluster"] = kmeans.labels_
            insights.append({
                "type": "cluster",
                "text": "The data naturally groups into 3 segments with similar patterns."
            })

            plt.figure(figsize=(6, 5))
            sns.scatterplot(
                x=sample[numeric_cols[0]],
                y=sample[numeric_cols[1]],
                hue="Cluster",
                palette="viridis",
                s=50
            )
            plt.title("Cluster Pattern")
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format="png", transparent=True)
            plt.close()
            img.seek(0)
            images["clusters"] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error generating clusters: {e}")

    return insights, images

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
    """Generate and return visualizations and hidden insights based on user's column selection."""
    data = request.get_json()
    filename = data.get('filename')
    columns = data.get('columns')

    if not filename or not columns:
        return jsonify({'error': 'Missing filename or columns'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        # Generate normal plots
        images = generate_visualizations(df, columns)

        # Generate hidden pattern insights + extra plots
        insights, insight_images = generate_insights(df)

        # Merge all plots
        images.update(insight_images)

        return jsonify({
            'images': images,
            'insights': insights
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500



if __name__ == '__main__':
    app.run(debug=True)