import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# --- NEW IMPORTS ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

# Initialize Flask app
app = Flask(__name__)

# --- NEW CONFIGURATIONS ---
# A secret key is required for sessions and CSRF protection
# IMPORTANT: Change this to a long, random string in production
app.config['SECRET_KEY'] = 'e0f4edbb83a9846c00495c503897ccd083dfcfc5aa4836cce2439064a9cd9ad4' 
# Define the database path
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

# --- EXISTING CONFIGS ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# --- INITIALIZE EXTENSIONS ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # 'login' is the function name of our login route
login_manager.login_message = 'You must be logged in to access this page.'
login_manager.login_message_category = 'error' # for styling flash messages


# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
# --- NEW: User Model ---
# This class defines the 'User' table in your database
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Required function for Flask-Login to load a user from the session
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- NEW: Forms (using Flask-WTF) ---
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Register')

    # Custom validator to check if email already exists
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already taken. Please choose a different one.')


# --- Your Existing Helper Functions (No Changes) ---
def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
                # Get top 20 most frequent categories
                top_20_categories = df[col].value_counts().nlargest(20).index
                df_top_20 = df[df[col].isin(top_20_categories)]
                
                sns.countplot(y=df_top_20[col], order=top_20_categories, palette='cool')
                plt.title(f'Frequency Count of {col} (Top 20)')
                plt.ylabel('Count')


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
            # Use a sample to avoid crashing on large datasets
            sample_df = df[numeric_cols]
            if len(sample_df) > 500:
                sample_df = sample_df.sample(n=500, random_state=1)
                
            sns.pairplot(sample_df, plot_kws={'color': '#00ffff', 'edgecolor': '#ff00ff'})
            plt.suptitle('Pairplot of Numeric Columns (Sampled)', y=1.02)
            
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
        corr = df[numeric_cols].corr(numeric_only=True).abs()
        corr_pairs = (
            corr.unstack()
            .sort_values(ascending=False)
            .drop_duplicates()
        )
        # Look for strong correlations
        top_corrs = corr_pairs[(corr_pairs < 1) & (corr_pairs > 0.7)].head(3) 
        for (col1, col2), val in top_corrs.items():
            insights.append({
                "type": "correlation",
                "text": f"Strong relationship detected: {col1} and {col2} move together ({val:.0%} correlation)."
            })

        # Plot top correlations (only if any were found)
        if not top_corrs.empty:
            try:
                plt.figure(figsize=(6, 4))
                top_corrs.plot(kind="bar", color="#00ffff")
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
         # Avoid division by zero or constant columns
        if iqr > 0:
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = df[(df[col] < lower) | (df[col] > upper)][col]
            # Only flag if it's a small portion (e.g., < 5%)
            if len(outliers) > 0 and len(outliers) < (0.05 * len(df)): 
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
            # Use only first 2-3 numeric cols for a simple demo
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
                sns.scatterplot(
                    x=sample[cluster_cols[0]],
                    y=sample[cluster_cols[1]],
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
        except ImportError:
            print("Scikit-learn not installed. Skipping cluster analysis.")
        except Exception as e:
            print(f"Error generating clusters: {e}")

    return insights, images

# --- NEW: Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, send them to the index page
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Find the user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        # Check if user exists and password is correct
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
        
        # Log the user in
        login_user(user)
        
        # Redirect to the page they were trying to access (if any)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    
    # Show the login form
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        
        # Add to database
        db.session.add(user)
        db.session.commit()
        
        flash('Congratulations, you are now a registered user! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required # Ensures only logged-in users can log out
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# --- MODIFIED: Your Existing Routes (Now Protected) ---

@app.route('/')
@login_required  # <-- PROTECTED: User must be logged in to see this
def index():
    """Render the main page (now protected)."""
    # Pass session data (if it exists) to the template
    return render_template('index.html', 
                           columns=session.get('columns'), 
                           filename=session.get('filename'))

@app.route('/upload', methods=['POST'])
@login_required  # <-- PROTECTED
def upload():
    """Handle the file upload and show the column selection."""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
        
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            columns = df.columns.tolist()
            # Store file info in the user's session
            session['filename'] = filename
            session['columns'] = columns
            
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error processing file: {e}", 'error')
            return redirect(url_for('index'))

    flash('File type not allowed', 'error')
    return redirect(url_for('index'))


@app.route('/visualize', methods=['POST'])
@login_required  # <-- PROTECTED
def visualize():
    """Generate and return visualizations (now protected)."""
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
    # This block ensures db.create_all() is called
    # only when you run 'python app.py' directly
    with app.app_context():
        db.create_all() # Creates the db.sqlite3 file and tables
    app.run(debug=True)
