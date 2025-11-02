import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from flask import Flask, request, render_template, session, make_response,  jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, storage
import firebase_admin.auth as auth

try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
except FileNotFoundError:
    print("Error: 'serviceAccountKey.json' not found. Please download it from your Firebase project settings.")
    # You might want to exit or handle this error more gracefully
except ValueError as e:
    # This can happen if firebase_admin is already initialized (e.g., during hot reload)
    print(f"Firebase already initialized or error: {e}")

# Initialize Flask app
app = Flask(__name__)

app.secret_key = '00326e9df953f171d63fb6f66527d38887f5f81e22546b68eaa50118198f9afc'

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

chart_data_store = {}

# --- MODIFIED Main Route (Protected) ---
@app.route('/')
def index():
    # Check if user is in session. If not, redirect to auth page.
    if 'user' not in session:
        return redirect(url_for('auth_page'))
    
    # If user is logged in, show the main application
    return render_template('index.html')

# --- NEW Authentication Page Route ---
@app.route('/auth')
def auth_page():
    # If user is already logged in, redirect them to the main page
    if 'user' in session:
        return redirect(url_for('index'))
    
    # Otherwise, show the login/signup page
    return render_template('auth.html')

# --- NEW Session Login Route (called by frontend JS) ---
@app.route('/api/session_login', methods=['POST'])
def session_login():
    try:
        # Get the ID token sent from the client
        id_token = request.json.get('idToken')
        
        # Verify the ID token with Firebase Admin
        decoded_token = auth.verify_id_token(id_token)
        
        # Store the user's UID in the Flask session
        session['user'] = decoded_token['uid']
        
        return make_response("Session login successful", 200)
    except auth.InvalidIdTokenError:
        return make_response("Invalid ID token", 401)
    except Exception as e:
        return make_response(f"Error: {str(e)}", 500)

# --- NEW Logout Route ---
@app.route('/logout')
def logout():
    # Clear the user from the session
    session.pop('user', None)
    # Redirect to the authentication page
    return redirect(url_for('auth_page'))

def set_plot_theme(theme='dark'):
    """Sets the matplotlib theme based on 'light' or 'dark' mode."""
    if theme == 'light':
        plt.style.use('default') # Use Matplotlib's default light theme
        plt.rcParams.update({
            'figure.facecolor': 'none',
            'axes.facecolor': '#f0f0f0', # Light background for plot area
            'axes.edgecolor': '#333333',
            'axes.labelcolor': '#000000',
            'xtick.color': '#000000',
            'ytick.color': '#000000',
            'text.color': '#000000', # Black text for light mode
            'grid.color': '#cccccc',
            'font.family': 'sans-serif',
        })
    else: # dark theme (default)
        plt.style.use('dark_background')
        plt.rcParams.update({
            'figure.facecolor': 'none',
            'axes.facecolor': 'none',
            'axes.edgecolor': '#00ffff',
            'axes.labelcolor': '#ffffff',
            'xtick.color': '#ffffff',
            'ytick.color': '#ffffff',
            'text.color': '#ffffff', # White text for dark mode
            'grid.color': '#444444',
            'font.family': 'sans-serif',
        })

def generate_all_visualizations(df, columns, theme='dark'):
    """Generate all possible plots for the selected columns and return them as base64 encoded strings."""
    
    # Set the text/label theme
    set_plot_theme(theme) 
    
    # --- NEW: Define theme-specific colors for plots ---
    if theme == 'light':
        colors = {
            'cmap': 'viridis',    # Colormap for heatmap
            'hist': '#007bff',    # Color for histogram
            'count': 'muted',     # Palette for count plot
            'pair': '#007bff',    # Color for pairplot dots
            'pair_edge': '#444444' # Edge color for pairplot dots
        }
    else: # dark theme
        colors = {
            'cmap': 'cool',
            'hist': '#00ffff',
            'count': 'cool',
            'pair': '#00ffff',
            'pair_edge': '#ff00ff'
        }
    
    images = {}
    
    # Filter dataframe to only selected columns
    df_selected = df[columns]
    
    numeric_cols = df_selected.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df_selected.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # --- Generate Correlation Heatmap for numeric columns ---
    if len(numeric_cols) > 1:
        try:
            plt.figure(figsize=(10, 8))
            corr = df[numeric_cols].corr()
            # Use theme color
            sns.heatmap(corr, annot=True, cmap=colors['cmap'], fmt=".2f")
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
                # Use theme color
                sns.histplot(df[col], kde=True, color=colors['hist'])
                plt.title(f'Distribution of {col}')
                plt.ylabel('Density')

            elif col in categorical_cols:
                # Bar chart for categorical data
                top_20_categories = df[col].value_counts().nlargest(20).index
                df_top_20 = df[df[col].isin(top_20_categories)]
                
                # Use theme palette
                sns.countplot(y=df_top_20[col], order=top_20_categories, palette=colors['count'])
                plt.title(f'Frequency Count of {col} (Top 20)')
                plt.ylabel('Count')


            plt.xlabel(col)
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
            sample_df = df[numeric_cols]
            if len(sample_df) > 500:
                sample_df = sample_df.sample(n=500, random_state=1)
                
            # Use theme colors
            sns.pairplot(sample_df, plot_kws={'color': colors['pair'], 'edgecolor': colors['pair_edge']})
            plt.suptitle('Pairplot of Numeric Columns (Sampled)', y=1.02)
            
            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            plt.close()
            img.seek(0)
            images['pairplot'] = base64.b64encode(img.getvalue()).decode()
        except Exception as e:
            print(f"Error generating pairplot: {e}")

    return images

def generate_insights(df, theme='dark'):
    """Generate business-friendly hidden pattern insights and related visualizations."""
    
    # Set the text/label theme
    set_plot_theme(theme)

    # --- NEW: Define theme-specific colors for insight plots ---
    if theme == 'light':
        colors = {
            'bar': '#007bff',   # Color for bar plots
            'box': '#dc3545',   # Color for box plots (outliers)
            'cluster': 'muted'  # Palette for cluster plot
        }
    else: # dark theme
        colors = {
            'bar': '#00ffff',
            'box': '#ff00ff',
            'cluster': 'viridis'
        }

    insights = []
    images = {}

    # ---- 1. Correlation Insights ----
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr(numeric_only=True).abs()
        corr_pairs = (
            corr.unstack()
            .sort_values(ascending=False)
            .drop_duplicates()
        )
        top_corrs = corr_pairs[(corr_pairs < 1) & (corr_pairs > 0.7)].head(3)
        for (col1, col2), val in top_corrs.items():
            insights.append({
                "type": "correlation",
                "text": f"Strong relationship detected: {col1} and {col2} move together ({val:.0%} correlation)."
            })

        if not top_corrs.empty:
            try:
                plt.figure(figsize=(6, 4))
                # Use theme color
                top_corrs.plot(kind="bar", color=colors['bar'])
                plt.title("Top Strong Correlations")
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
        if iqr > 0: 
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = df[(df[col] < lower) | (df[col] > upper)][col]
            if len(outliers) > 0 and len(outliers) < (0.05 * len(df)):
                insights.append({
                    "type": "outlier",
                    "text": f"{len(outliers)} unusual values found in {col} — possible errors or special cases."
                })

                try:
                    plt.figure(figsize=(5, 4))
                    # Use theme color
                    sns.boxplot(x=df[col], color=colors['box'])
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
            cluster_cols = numeric_cols[:2]
            sample = df[cluster_cols].dropna().sample(min(500, len(df)), random_state=42)
            if not sample.empty:
                kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(sample)
                sample["Cluster"] = kmeans.labels_
                insights.append({
                    "type": "cluster",
                    "text": f"The data appears to naturally group into 3 segments (based on {', '.join(cluster_cols)})."
                })

                plt.figure(figsize=(6, 5))
                # Use theme palette
                sns.scatterplot(
                    x=sample[cluster_cols[0]],
                    y=sample[cluster_cols[1]],
                    hue="Cluster",
                    palette=colors['cluster'],
                    s=50
                )
                plt.title("Cluster Pattern")
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format="png", transparent=True)
                plt.close()
                img.seek(0)
                images["clusters"] = base64.b64encode(img.getvalue()).decode()
        except ImportError:
            print("Scikit-learn not installed. Skipping cluster analysis.")
        except Exception as e:
            print(f"Error generating clusters: {e}")

    return insights, images

@app.route('/upload', methods=['POST'])
def upload():
    """Handle the file upload and show the column selection."""
    if 'file' not in request.files:
        return render_template('index.html', error='No file part')
    
    file = request.files['file']
    
    if file.filename == '':
        return render_template('index.html', error='No selected file')
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Generate preview
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath, nrows=5)
            else:
                df = pd.read_excel(filepath, nrows=5)
            preview = df.to_html(classes='table table-striped', index=False)
        except Exception as e:
            preview = f'<p class="error">Error generating preview: {e}</p>'

        # Get column names
        try:
            if filename.endswith('.csv'):
                df_full = pd.read_csv(filepath)
            else:
                df_full = pd.read_excel(filepath)
            columns = df_full.columns.tolist()
        except Exception as e:
            return render_template('index.html', error=f'Error reading file: {e}')

        return render_template('index.html', filename=filename, columns=columns, preview=preview)
    return redirect(url_for('index'))


@app.route('/visualize', methods=['POST'])
def visualize():
    """Generate and return visualizations and hidden insights based on user's column and graph selection."""
    data = request.get_json()
    filename = data.get('filename')
    columns = data.get('columns')
    selected_graph_types = data.get('graphs', [])
    theme = data.get('theme', 'dark')

    if not filename or not columns:
        return jsonify({'error': 'Missing filename or columns'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        all_plots = generate_all_visualizations(df, columns, theme)
        insights, insight_images = generate_insights(df, theme)

        user_selected_images = {}
        useful_images = {}

        df_selected = df[columns]
        numeric_cols = df_selected.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df_selected.select_dtypes(include=['object', 'category']).columns.tolist()

        for key, img_data in all_plots.items():
            is_selected = False
            
            if key == 'heatmap' and 'heatmap' in selected_graph_types:
                is_selected = True
            elif key == 'pairplot' and 'pairplot' in selected_graph_types:
                is_selected = True
            elif key.startswith('plot_'):
                col_name = key.replace('plot_', '')
                if col_name in numeric_cols and 'distribution' in selected_graph_types:
                    is_selected = True
                elif col_name in categorical_cols and 'count' in selected_graph_types:
                    is_selected = True
            
            if is_selected:
                user_selected_images[key] = img_data
            else:
                useful_images[key] = img_data
        
        useful_images.update(insight_images)

        return jsonify({
            'user_selected_images': user_selected_images,
            'useful_images': useful_images,
            'insights': insights
        })
    except Exception as e:
        print(f"Error in /visualize: {e}")
        return jsonify({'error': f'An error occurred: {e}'}), 500



if __name__ == '__main__':
    app.run(debug=True)