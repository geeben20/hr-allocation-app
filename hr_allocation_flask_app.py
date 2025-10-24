"""
Single-file Flask app (hr_allocation_flask_app.py)
Run:
  1. python -m venv venv
  2. venv\Scripts\activate (Windows) or source venv/bin/activate (mac/linux)
  3. pip install Flask SQLAlchemy
  4. python hr_allocation_flask_app.py

Then open http://127.0.0.1:5000/

This file serves a modern redesigned frontend (home page with image left, auth form right)
and a light in-process backend using SQLite for users, projects, resources and simple report endpoints.
All frontend HTML/CSS/JS is embedded in this single file via render_template_string so it's
ready-to-run without extra files.
"""
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Database configuration for production
database_url = os.environ.get('DATABASE_URL', 'sqlite:///hr_alloc.db')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(120), default='Developer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'position': self.position,
            'createdAt': self.created_at.isoformat()
        }

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    manager = db.Column(db.String(120), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='active')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'manager': self.manager,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'updatedAt': self.updated_at.isoformat()
        }

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(120), nullable=False)
    availability = db.Column(db.Integer, default=100)  # percentage
    current_project = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'availability': self.availability,
            'currentProject': self.current_project
        }

# --- Database Initialization ---
def init_db():
    """Initialize the database and seed with sample data."""
    with app.app_context():
        db.create_all()
        # Create a default user and some sample projects/resources if they don't exist
        if not User.query.first():
            u = User(name='Babafemi Oyindamola', email='john@example.com', password_hash=generate_password_hash('password'), position='Project Manager')
            db.session.add(u)
        if not Project.query.first():
            p1 = Project(name='E-commerce Platform', manager='Babafemi Oyindamola', start_date=datetime(2023,3,15).date(), end_date=datetime(2023,9,30).date(), status='active')
            p2 = Project(name='Mobile Banking App', manager='Akinleye Tolu', start_date=datetime(2023,5,1).date(), end_date=datetime(2023,11,15).date(), status='active')
            p3 = Project(name='CRM System', manager='Oluleye Philip', start_date=datetime(2023,1,10).date(), end_date=datetime(2023,7,31).date(), status='completed')
            db.session.add_all([p1,p2,p3])
        if not Resource.query.first():
            r1 = Resource(name='Benjamin Godswill', position='Project Manager', availability=0, current_project='E-commerce Platform')
            r2 = Resource(name='Akinleye Tolu', position='Senior Developer', availability=20, current_project='Mobile Banking App')
            r3 = Resource(name='Oluleye Philip', position='UX Designer', availability=0, current_project='CRM System')
            db.session.add_all([r1,r2,r3])
        db.session.commit()
        print("Database initialized successfully!")

# --- Routes / API ---
@app.route('/')
def home():
    # Single page app HTML (modern home with left image and right signup/login)
    return render_template_string(HOME_HTML)

@app.route('/dashboard')
def dashboard_page():
    return render_template_string(DASH_HTML)

# Auth API (session-based)
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    position = data.get('position') or 'Developer'

    if not (name and email and password):
        return jsonify(success=False, message='Name, email and password are required'), 400

    if User.query.filter_by(email=email).first():
        return jsonify(success=False, message='Email already registered'), 400

    user = User(name=name, email=email, password_hash=generate_password_hash(password), position=position)
    db.session.add(user)
    db.session.commit()
    return jsonify(success=True, data=user.to_dict())

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not (email and password):
        return jsonify(success=False, message='Email and password required'), 400
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(success=False, message='Invalid credentials'), 401
    session['user_id'] = user.id
    return jsonify(success=True, data=user.to_dict())

@app.route('/api/auth/me')
def api_me():
    uid = session.get('user_id')
    if not uid:
        return jsonify(success=False, message='Not authenticated'), 401
    user = User.query.get(uid)
    if not user:
        return jsonify(success=False, message='User not found'), 404
    return jsonify(success=True, data=user.to_dict())

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify(success=True)

# Projects
@app.route('/api/projects')
def api_get_projects():
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    data = [p.to_dict() for p in projects]
    return jsonify(success=True, data=data)

@app.route('/api/resources')
def api_get_resources():
    resources = Resource.query.all()
    data = [r.to_dict() for r in resources]
    return jsonify(success=True, data=data)

@app.route('/api/reports', methods=['GET'])
def api_get_reports():
    # simple mock reports list
    reports = [
        {'id':1,'name':'Q2 Resource Utilization','generatedBy':'System','createdAt':datetime.utcnow().isoformat(),'type':'Resource Utilization'},
        {'id':2,'name':'Project Progress - May 2023','generatedBy':'Benjamin Godswill','createdAt':datetime.utcnow().isoformat(),'type':'Project Progress'}
    ]
    return jsonify(success=True, data=reports)

# Utility endpoints for dashboard stats
@app.route('/api/resources/stats/utilization')
def api_resource_stats():
    total = Resource.query.count()
    allocated = Resource.query.filter(Resource.availability<100).count()
    available = Resource.query.filter(Resource.availability>0).count()
    avg_util = 0
    resources = Resource.query.all()
    if resources:
        avg_util = round(sum((100 - r.availability) for r in resources) / len(resources))
    overallocated = Resource.query.filter(Resource.availability<=0).count()
    return jsonify(success=True, data={'totalResources': total, 'allocatedResources': allocated, 'availableResources': available, 'averageUtilization': avg_util, 'overallocated': overallocated, 'totalProjects': Project.query.count()})

# --- HTML Templates (embedded) ---
HOME_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DevResource — HR Allocation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#f4f6fb;--card:#ffffff;--muted:#7b8a97;--accent:#6c63ff;--accent-2:#4dd0e1;--glass: rgba(255,255,255,0.6)}
    *{box-sizing:border-box;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial}
    body{margin:0;background:linear-gradient(180deg,#f8fbff 0%,var(--bg)100%);color:#102a43}
    .wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px}
    .card{width:100%;max-width:1100px;background:transparent;display:flex;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(16,42,67,0.08)}
    .left{flex:1;min-height:480px;background-image:linear-gradient(135deg, rgba(108,99,255,0.85), rgba(77,208,225,0.85)), url('https://images.unsplash.com/photo-1528247228-1e8d3a780f9f?q=80&w=1400&auto=format&fit=crop&ixlib=rb-4.0.3&s=1');background-size:cover;background-position:center;padding:40px;color:white;display:flex;flex-direction:column;justify-content:center}
    .brand{display:flex;align-items:center;gap:12px;font-weight:700}
    .brand .logo{width:48px;height:48px;border-radius:10px;background:rgba(255,255,255,0.18);display:grid;place-items:center;font-size:20px}
    .left h1{font-size:34px;line-height:1.05;margin-top:18px;margin-bottom:8px}
    .left p{opacity:0.95;color:rgba(255,255,255,0.9);max-width:420px}
    .left ul{margin-top:18px;list-style:none;padding:0}
    .left li{display:flex;align-items:center;gap:10px;margin-top:10px;font-weight:600}
    .badge{background:rgba(255,255,255,0.12);padding:6px 10px;border-radius:999px;font-size:13px}

    .right{width:420px;background:var(--card);padding:32px;border-top-right-radius:14px;border-bottom-right-radius:14px}
    .auth-title{font-size:20px;font-weight:700;margin-bottom:6px}
    .auth-sub{font-size:13px;color:var(--muted);margin-bottom:18px}
    .form-group{margin-bottom:14px}
    .input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #e6eef6;background:#fbfdff}
    .btn{display:inline-block;width:100%;padding:12px 14px;border-radius:10px;border:none;background:linear-gradient(90deg,var(--accent),#5b45f6);color:white;font-weight:700;cursor:pointer}
    .ghost{width:100%;text-align:center;padding:10px;border-radius:10px;border:1px solid #eef3ff;margin-top:12px;cursor:pointer;background:transparent}
    .switch{display:flex;gap:8px;align-items:center;justify-content:center;margin-top:12px}
    .small{font-size:13px;color:var(--muted)}

    .or{display:flex;align-items:center;gap:12px;margin:18px 0}
    .or span{flex:1;height:1px;background:#eef4fb}
    .or b{font-size:13px;color:var(--muted)}

    footer{margin-top:16px;font-size:13px;color:var(--muted);text-align:center}

    @media (max-width:900px){.card{flex-direction:column}.left{display:none}.right{border-radius:14px;width:100%;max-width:520px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card" role="main">
      <div class="left" aria-hidden="true">
        <div class="brand"><div class="logo">DR</div><div>DevResource</div></div>
        <h1> Human Resources Allocation for Software Developers </h1>
        <p>Assign the right people to the right projects, track utilization and spot bottlenecks before they affect delivery.</p>
        <ul>
          <li><span class="badge">Projects</span> Manage and Track project progress</li>
          <li><span class="badge">Resources</span> View Availability & Allocation</li>
          <li><span class="badge">Reports</span> Export Utilization & Performance Reports</li>
        </ul>
      </div>

      <div class="right" aria-live="polite">
        <div id="auth-root">
          <div id="login-view">
            <div class="auth-title">Welcome back</div>
            <div class="auth-sub">Sign in to your DevResource account</div>
            <div id="login-message"></div>
            <form id="loginForm">
              <div class="form-group">
                <input class="input" id="email" type="email" placeholder="Email address" required>
              </div>
              <div class="form-group">
                <input class="input" id="password" type="password" placeholder="Password" required>
              </div>
              <button id="login-btn" class="btn" type="submit">Sign in</button>
            </form>

            <div class="or"><span></span><b>or</b><span></span></div>
            <button id="showRegister" class="ghost">Create an account</button>
            <footer>By continuing, you agree to our <a href="#">Terms</a> and <a href="#">Privacy</a>.</footer>
          </div>

          <div id="register-view" style="display:none">
            <div class="auth-title">Create account</div>
            <div class="auth-sub">Start using DevResource for free</div>
            <div id="register-message"></div>
            <form id="registerForm">
              <div class="form-group"><input class="input" id="fullName" placeholder="Full name" required></div>
              <div class="form-group"><input class="input" id="regEmail" type="email" placeholder="Email address" required></div>
              <div class="form-group"><input class="input" id="regPassword" type="password" placeholder="Create password" required></div>
              <div class="form-group"><input class="input" id="confirmPassword" type="password" placeholder="Confirm password" required></div>
              <div class="form-group"><input class="input" id="position" placeholder="Position (e.g. Developer)"></div>
              <button id="register-btn" class="btn" type="submit">Create account</button>
            </form>
            <div class="or"><span></span><b>or</b><span></span></div>
            <button id="showLogin" class="ghost">Have an account? Sign in</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const apiBase = '';

    function showMessage(id, msg, type='error'){
      const el = document.getElementById(id);
      el.innerHTML = `<div style="padding:10px;border-radius:8px;margin-bottom:12px;background:${type==='error'?'#fff0f0':'#f0fff4'};color:${type==='error'?'#c33':'#166534'}">${msg}</div>`;
    }

    function clearMessage(id){document.getElementById(id).innerHTML=''}

    document.getElementById('showRegister').addEventListener('click', ()=>{document.getElementById('login-view').style.display='none';document.getElementById('register-view').style.display='block';clearMessage('login-message');});
    document.getElementById('showLogin').addEventListener('click', ()=>{document.getElementById('register-view').style.display='none';document.getElementById('login-view').style.display='block';clearMessage('register-message');});

    document.getElementById('loginForm').addEventListener('submit', async (e)=>{
      e.preventDefault();
      clearMessage('login-message');
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      try{
        const res = await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
        const data = await res.json();
        if(!res.ok) throw new Error(data.message||'Login failed');
        // redirect to dashboard
        window.location.href = '/dashboard';
      }catch(err){showMessage('login-message',err.message||'Error logging in')}
    });

    document.getElementById('registerForm').addEventListener('submit', async (e)=>{
      e.preventDefault();
      clearMessage('register-message');
      const name = document.getElementById('fullName').value;
      const email = document.getElementById('regEmail').value;
      const password = document.getElementById('regPassword').value;
      const confirm = document.getElementById('confirmPassword').value;
      const position = document.getElementById('position').value || 'Developer';
      if(password !== confirm){showMessage('register-message','Passwords do not match', 'error');return}
      try{
        const res = await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,password,position})});
        const data = await res.json();
        if(!res.ok) throw new Error(data.message||'Registration failed');
        showMessage('register-message','Account created — redirecting to sign in...', 'success');
        setTimeout(()=>{document.getElementById('register-view').style.display='none';document.getElementById('login-view').style.display='block';},1000);
      }catch(err){showMessage('register-message',err.message||'Error registering')}
    });
  </script>
</body>
</html>
"""

# Dashboard HTML: Modern dashboard with full navigation and separate pages
DASH_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard — DevResource</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --primary: #6c63ff;
      --primary-dark: #5b45f6;
      --secondary: #4dd0e1;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --dark: #102a43;
      --muted: #7b8a97;
      --light: #f8fbff;
      --border: #e6eef6;
      --card-bg: #ffffff;
      --sidebar-bg: #1e293b;
      --sidebar-text: #f1f5f9;
      --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: #f5f7fb;
      color: var(--dark);
      line-height: 1.6;
    }
    
    /* Layout */
    .dashboard-container {
      display: flex;
      min-height: 100vh;
    }
    
    /* Sidebar */
    .sidebar {
      width: 260px;
      background: var(--sidebar-bg);
      color: var(--sidebar-text);
      padding: 24px 0;
      transition: all 0.3s ease;
    }
    
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 24px 24px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      margin-bottom: 24px;
    }
    
    .logo {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: var(--primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 18px;
    }
    
    .brand-text {
      font-weight: 700;
      font-size: 20px;
    }
    
    .nav-links {
      list-style: none;
      padding: 0;
    }
    
    .nav-item {
      margin-bottom: 8px;
    }
    
    .nav-link {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 24px;
      color: var(--sidebar-text);
      text-decoration: none;
      transition: all 0.2s;
      border-left: 3px solid transparent;
    }
    
    .nav-link:hover, .nav-link.active {
      background: rgba(255,255,255,0.1);
      border-left-color: var(--primary);
    }
    
    .nav-link i {
      width: 20px;
      text-align: center;
    }
    
    /* Main Content */
    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    
    /* Top Bar */
    .top-bar {
      background: var(--card-bg);
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 10px rgba(16,42,67,0.08);
      z-index: 10;
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--primary);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 600;
    }
    
    .user-details {
      display: flex;
      flex-direction: column;
    }
    
    .user-name {
      font-weight: 600;
    }
    
    .user-role {
      font-size: 13px;
      color: var(--muted);
    }
    
    .logout-btn {
      background: transparent;
      border: 1px solid var(--border);
      padding: 8px 16px;
      border-radius: 8px;
      color: var(--dark);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    
    .logout-btn:hover {
      background: #f8fafc;
    }
    
    /* Content Area */
    .content {
      padding: 32px;
      flex: 1;
    }
    
    .page-title {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    
    .page-subtitle {
      color: var(--muted);
      margin-bottom: 24px;
    }
    
    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
    }
    
    .stat-card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 12px rgba(16,42,67,0.05);
      transition: transform 0.2s, box-shadow 0.2s;
      position: relative;
      overflow: hidden;
    }
    
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
      transition: left 0.5s;
    }
    
    .stat-card:hover::before {
      left: 100%;
    }
    
    .stat-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }
    
    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 16px;
      font-size: 20px;
    }
    
    .projects-icon { background: rgba(108, 99, 255, 0.1); color: var(--primary); }
    .team-icon { background: rgba(77, 208, 225, 0.1); color: var(--secondary); }
    .utilization-icon { background: rgba(16, 185, 129, 0.1); color: var(--success); }
    .issues-icon { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
    
    .stat-value {
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 4px;
    }
    
    .stat-label {
      color: var(--muted);
      font-size: 14px;
    }
    
    /* Content Cards */
    .content-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    
    @media (max-width: 1024px) {
      .content-grid {
        grid-template-columns: 1fr;
      }
    }
    
    .content-card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 12px rgba(16,42,67,0.05);
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    
    .card-title {
      font-size: 18px;
      font-weight: 600;
    }
    
    .view-all {
      color: var(--primary);
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
    }
    
    /* Tables */
    .data-table {
      width: 100%;
      border-collapse: collapse;
    }
    
    .data-table th {
      text-align: left;
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
      font-weight: 500;
      font-size: 14px;
    }
    
    .data-table td {
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
    }
    
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
    }
    
    .status-active {
      background: rgba(16, 185, 129, 0.1);
      color: var(--success);
    }
    
    .status-completed {
      background: rgba(107, 114, 128, 0.1);
      color: #6b7280;
    }
    
    .status-planning {
      background: rgba(59, 130, 246, 0.1);
      color: #3b82f6;
    }
    
    .availability-high {
      color: var(--success);
      font-weight: 600;
    }
    
    .availability-medium {
      color: var(--warning);
      font-weight: 600;
    }
    
    .availability-low {
      color: var(--danger);
      font-weight: 600;
    }
    
    /* Action Buttons */
    .action-buttons {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
    }
    
    .btn {
      padding: 10px 20px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    
    .btn-primary {
      background: var(--primary);
      color: white;
    }
    
    .btn-secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--dark);
    }
    
    .btn-success {
      background: var(--success);
      color: white;
    }
    
    /* Charts */
    .chart-container {
      height: 300px;
      position: relative;
      margin: 20px 0;
    }
    
    /* Progress Bars */
    .progress-bar {
      width: 100%;
      height: 8px;
      background: var(--border);
      border-radius: 4px;
      overflow: hidden;
    }
    
    .progress-fill {
      height: 100%;
      background: var(--primary);
      border-radius: 4px;
      transition: width 0.3s ease;
    }
    
    /* Resource Cards */
    .resource-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 20px;
    }
    
    .resource-card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 12px rgba(16,42,67,0.05);
      transition: transform 0.2s;
    }
    
    .resource-card:hover {
      transform: translateY(-2px);
    }
    
    .resource-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }
    
    .resource-avatar {
      width: 50px;
      height: 50px;
      border-radius: 50%;
      background: var(--primary);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 600;
      font-size: 18px;
    }
    
    .resource-info h4 {
      margin-bottom: 4px;
    }
    
    .resource-position {
      color: var(--muted);
      font-size: 14px;
    }
    
    /* Report Cards */
    .report-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }
    
    .report-card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 12px rgba(16,42,67,0.05);
      border-left: 4px solid var(--primary);
    }
    
    .report-card.success {
      border-left-color: var(--success);
    }
    
    .report-card.warning {
      border-left-color: var(--warning);
    }
    
    /* Search and Filter */
    .search-filter-bar {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      align-items: center;
    }
    
    .search-box {
      flex: 1;
      position: relative;
    }
    
    .search-box input {
      width: 100%;
      padding: 12px 16px 12px 40px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card-bg);
    }
    
    .search-box i {
      position: absolute;
      left: 16px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
    }
    
    /* Mobile Responsive */
    @media (max-width: 768px) {
      .dashboard-container {
        flex-direction: column;
      }
      
      .sidebar {
        width: 100%;
        padding: 16px;
      }
      
      .nav-links {
        display: flex;
        overflow-x: auto;
      }
      
      .nav-item {
        margin-bottom: 0;
        margin-right: 16px;
      }
      
      .nav-link {
        border-left: none;
        border-bottom: 3px solid transparent;
        white-space: nowrap;
      }
      
      .nav-link:hover, .nav-link.active {
        border-left-color: transparent;
        border-bottom-color: var(--primary);
      }
      
      .content {
        padding: 20px;
      }
      
      .stats-grid {
        grid-template-columns: 1fr;
      }
      
      .search-filter-bar {
        flex-direction: column;
      }
    }

    /* Page Transitions */
    .page-content {
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.3s ease;
    }
    
    .page-content.active {
      opacity: 1;
      transform: translateY(0);
    }

    /* Modal Styles */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }

    .modal-content {
      background: white;
      border-radius: 12px;
      width: 100%;
      max-width: 500px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 24px 0;
      margin-bottom: 20px;
    }

    .modal-header h3 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .modal-close {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: var(--muted);
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-body {
      padding: 0 24px;
    }

    .modal-footer {
      padding: 20px 24px 24px;
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      border-top: 1px solid var(--border);
      margin-top: 20px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: var(--dark);
    }

    .form-group .input {
      width: 100%;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
    }

    .form-group .input:focus {
      outline: none;
      border-color: var(--primary);
    }
  </style>
</head>
<body>
  <div class="dashboard-container">
    <!-- Sidebar Navigation -->
    <nav class="sidebar">
      <div class="brand">
        <div class="logo">DR</div>
        <div class="brand-text">DevResource</div>
      </div>
      <ul class="nav-links">
        <li class="nav-item">
          <a href="#dashboard" class="nav-link active" data-page="dashboard">
            <i class="fas fa-chart-pie"></i>
            <span>Dashboard</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#projects" class="nav-link" data-page="projects">
            <i class="fas fa-project-diagram"></i>
            <span>Projects</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#resources" class="nav-link" data-page="resources">
            <i class="fas fa-users"></i>
            <span>Resources</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#reports" class="nav-link" data-page="reports">
            <i class="fas fa-chart-bar"></i>
            <span>Reports</span>
          </a>
        </li>
      </ul>
    </nav>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Top Bar -->
      <header class="top-bar">
        <div id="breadcrumb">
          <span class="breadcrumb-item">Dashboard</span>
        </div>
        <div class="user-info">
          <div class="user-details">
            <div class="user-name" id="user-name">Loading...</div>
            <div class="user-role" id="user-role">Loading...</div>
          </div>
          <div class="avatar" id="user-avatar">JD</div>
          <button class="logout-btn" id="logoutBtn">
            <i class="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <div class="content">
        <!-- Dashboard Page -->
        <div id="dashboard-page" class="page-content active">
          <h1 class="page-title">Dashboard</h1>
          <p class="page-subtitle">Welcome back! Here's what's happening with your team today.</p>

          <div class="stats-grid" id="stats-grid">
            <!-- Stats will be populated by JavaScript -->
          </div>

          <div class="content-grid">
            <div class="content-card">
              <div class="card-header">
                <h3 class="card-title">Recent Projects</h3>
                <a href="#projects" class="view-all">View All</a>
              </div>
              <div id="projects-area">
                <!-- Projects will be populated by JavaScript -->
              </div>
            </div>

            <div class="content-card">
              <div class="card-header">
                <h3 class="card-title">Team Resources</h3>
                <a href="#resources" class="view-all">View All</a>
              </div>
              <div id="resources-area">
                <!-- Resources will be populated by JavaScript -->
              </div>
            </div>
          </div>
        </div>

        <!-- Projects Page -->
        <div id="projects-page" class="page-content">
          <div class="card-header">
            <div>
              <h1 class="page-title">Projects</h1>
              <p class="page-subtitle">Manage and track all your projects in one place</p>
            </div>
            <button class="btn btn-primary" id="new-project-btn">
              <i class="fas fa-plus"></i>
              New Project
            </button>
          </div>

          <div class="search-filter-bar">
            <div class="search-box">
              <i class="fas fa-search"></i>
              <input type="text" placeholder="Search projects...">
            </div>
            <select class="btn btn-secondary">
              <option>All Status</option>
              <option>Active</option>
              <option>Completed</option>
              <option>Planning</option>
            </select>
          </div>

          <div class="content-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Manager</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="projects-table">
                <!-- Projects table will be populated by JavaScript -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- Resources Page -->
        <div id="resources-page" class="page-content">
          <div class="card-header">
            <div>
              <h1 class="page-title">Team Resources</h1>
              <p class="page-subtitle">Manage your team members and their allocations</p>
            </div>
            <button class="btn btn-primary" id="new-resource-btn">
              <i class="fas fa-user-plus"></i>
              Add Resource
            </button>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon team-icon">
                <i class="fas fa-users"></i>
              </div>
              <div class="stat-value" id="total-resources">0</div>
              <div class="stat-label">Total Resources</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon utilization-icon">
                <i class="fas fa-chart-line"></i>
              </div>
              <div class="stat-value" id="avg-utilization">0%</div>
              <div class="stat-label">Avg Utilization</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon projects-icon">
                <i class="fas fa-check-circle"></i>
              </div>
              <div class="stat-value" id="available-resources">0</div>
              <div class="stat-label">Available</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon issues-icon">
                <i class="fas fa-exclamation-triangle"></i>
              </div>
              <div class="stat-value" id="overallocated-resources">0</div>
              <div class="stat-label">Overallocated</div>
            </div>
          </div>

          <div class="resource-grid" id="resources-grid">
            <!-- Resource cards will be populated by JavaScript -->
          </div>
        </div>

        <!-- Reports Page -->
        <div id="reports-page" class="page-content">
          <div class="card-header">
            <div>
              <h1 class="page-title">Reports & Analytics</h1>
              <p class="page-subtitle">Generate and view detailed reports</p>
            </div>
            <button class="btn btn-success" id="export-report-btn">
              <i class="fas fa-download"></i>
              Export Report
            </button>
          </div>

          <div class="content-grid">
            <div class="content-card">
              <h3 class="card-title">Resource Utilization</h3>
              <div class="chart-container">
                <canvas id="utilizationChart"></canvas>
              </div>
            </div>

            <div class="content-card">
              <h3 class="card-title">Project Status Distribution</h3>
              <div class="chart-container">
                <canvas id="projectChart"></canvas>
              </div>
            </div>
          </div>

          <div class="content-card">
            <div class="card-header">
              <h3 class="card-title">Recent Reports</h3>
            </div>
            <div class="report-grid" id="reports-grid">
              <!-- Reports will be populated by JavaScript -->
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // DOM Elements
    const pages = {
      dashboard: document.getElementById('dashboard-page'),
      projects: document.getElementById('projects-page'),
      resources: document.getElementById('resources-page'),
      reports: document.getElementById('reports-page')
    };

    const breadcrumb = document.getElementById('breadcrumb');
    let currentPage = 'dashboard';

    // API Functions
    async function fetchJson(path, options = {}) {
      const response = await fetch(path, options);
      return response.json();
    }

    // Modal Management
    function createModal(title, content, onSubmit = null) {
      // Remove existing modal
      const existingModal = document.getElementById('dynamic-modal');
      if (existingModal) {
        existingModal.remove();
      }

      const modal = document.createElement('div');
      modal.id = 'dynamic-modal';
      modal.innerHTML = `
        <div class="modal-overlay">
          <div class="modal-content">
            <div class="modal-header">
              <h3>${title}</h3>
              <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
              ${content}
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary modal-cancel">Cancel</button>
              <button class="btn btn-primary modal-submit">Submit</button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Event listeners
      modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
      modal.querySelector('.modal-cancel').addEventListener('click', () => modal.remove());
      modal.querySelector('.modal-overlay').addEventListener('click', (e) => {
        if (e.target === modal.querySelector('.modal-overlay')) {
          modal.remove();
        }
      });

      if (onSubmit) {
        modal.querySelector('.modal-submit').addEventListener('click', () => {
          onSubmit(modal);
        });
      }

      return modal;
    }

    // Navigation
    function navigateTo(page) {
      // Hide all pages
      Object.values(pages).forEach(p => {
        p.classList.remove('active');
        setTimeout(() => p.style.display = 'none', 300);
      });
      
      // Show target page
      setTimeout(() => {
        pages[page].style.display = 'block';
        setTimeout(() => pages[page].classList.add('active'), 50);
      }, 300);
      
      // Update navigation
      document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
      });
      document.querySelector(`[data-page="${page}"]`).classList.add('active');
      
      // Update breadcrumb
      const pageTitles = {
        dashboard: 'Dashboard',
        projects: 'Projects',
        resources: 'Resources',
        reports: 'Reports'
      };
      breadcrumb.innerHTML = `<span class="breadcrumb-item">${pageTitles[page]}</span>`;
      
      // Update document title
      document.title = `${pageTitles[page]} — DevResource`;
      
      currentPage = page;
      
      // Load page-specific data
      loadPageData(page);
    }

    // Load page-specific data
    async function loadPageData(page) {
      switch(page) {
        case 'dashboard':
          await loadDashboardData();
          break;
        case 'projects':
          await loadProjectsData();
          break;
        case 'resources':
          await loadResourcesData();
          break;
        case 'reports':
          await loadReportsData();
          break;
      }
    }

    // Dashboard Data
    async function loadDashboardData() {
      try {
        const stats = await fetchJson('/api/resources/stats/utilization');
        if (stats.success) {
          const data = stats.data;
          document.getElementById('stats-grid').innerHTML = `
            <div class="stat-card">
              <div class="stat-icon projects-icon">
                <i class="fas fa-project-diagram"></i>
              </div>
              <div class="stat-value">${data.totalProjects}</div>
              <div class="stat-label">Active Projects</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon team-icon">
                <i class="fas fa-users"></i>
              </div>
              <div class="stat-value">${data.totalResources}</div>
              <div class="stat-label">Team Members</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon utilization-icon">
                <i class="fas fa-chart-line"></i>
              </div>
              <div class="stat-value">${data.averageUtilization}%</div>
              <div class="stat-label">Avg Utilization</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon issues-icon">
                <i class="fas fa-exclamation-triangle"></i>
              </div>
              <div class="stat-value">${data.overallocated}</div>
              <div class="stat-label">Critical Issues</div>
            </div>
          `;
        }

        const projects = await fetchJson('/api/projects');
        if (projects.success) {
          const projectsHtml = `
            <table class="data-table">
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Manager</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${projects.data.slice(0, 5).map(project => `
                  <tr>
                    <td>${project.name}</td>
                    <td>${project.manager || 'N/A'}</td>
                    <td>
                      <span class="status-badge ${project.status === 'active' ? 'status-active' : 'status-completed'}">
                        ${project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                      </span>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
          document.getElementById('projects-area').innerHTML = projectsHtml;
        }

        const resources = await fetchJson('/api/resources');
        if (resources.success) {
          const resourcesHtml = `
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Position</th>
                  <th>Availability</th>
                </tr>
              </thead>
              <tbody>
                ${resources.data.slice(0, 5).map(resource => {
                  let availabilityClass = 'availability-high';
                  if (resource.availability <= 20) availabilityClass = 'availability-low';
                  else if (resource.availability <= 50) availabilityClass = 'availability-medium';
                  
                  return `
                    <tr>
                      <td>${resource.name}</td>
                      <td>${resource.position}</td>
                      <td class="${availabilityClass}">${resource.availability}%</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          `;
          document.getElementById('resources-area').innerHTML = resourcesHtml;
        }
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      }
    }

    // Projects Data
    async function loadProjectsData() {
      try {
        const projects = await fetchJson('/api/projects');
        if (projects.success) {
          const projectsHtml = projects.data.map(project => `
            <tr>
              <td><strong>${project.name}</strong></td>
              <td>${project.manager || 'N/A'}</td>
              <td>${project.startDate ? new Date(project.startDate).toLocaleDateString() : 'N/A'}</td>
              <td>${project.endDate ? new Date(project.endDate).toLocaleDateString() : 'N/A'}</td>
              <td>
                <span class="status-badge ${project.status === 'active' ? 'status-active' : 
                                       project.status === 'completed' ? 'status-completed' : 'status-planning'}">
                  ${project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                </span>
              </td>
              <td>
                <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">
                  <i class="fas fa-edit"></i>
                </button>
              </td>
            </tr>
          `).join('');
          document.getElementById('projects-table').innerHTML = projectsHtml;
        }
      } catch (error) {
        console.error('Error loading projects data:', error);
      }
    }

    // Add New Project Functionality
    function setupNewProjectButton() {
      const newProjectBtn = document.getElementById('new-project-btn');
      if (newProjectBtn) {
        newProjectBtn.addEventListener('click', showNewProjectModal);
      }
    }

    function showNewProjectModal() {
      const modalContent = `
        <form id="new-project-form">
          <div class="form-group">
            <label for="project-name">Project Name</label>
            <input type="text" id="project-name" class="input" required>
          </div>
          <div class="form-group">
            <label for="project-manager">Project Manager</label>
            <input type="text" id="project-manager" class="input" required>
          </div>
          <div class="form-group">
            <label for="project-start-date">Start Date</label>
            <input type="date" id="project-start-date" class="input" required>
          </div>
          <div class="form-group">
            <label for="project-end-date">End Date</label>
            <input type="date" id="project-end-date" class="input" required>
          </div>
          <div class="form-group">
            <label for="project-status">Status</label>
            <select id="project-status" class="input" required>
              <option value="planning">Planning</option>
              <option value="active" selected>Active</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </form>
      `;

      createModal('Create New Project', modalContent, async (modal) => {
        const form = modal.querySelector('#new-project-form');
        const formData = {
          name: modal.querySelector('#project-name').value,
          manager: modal.querySelector('#project-manager').value,
          start_date: modal.querySelector('#project-start-date').value,
          end_date: modal.querySelector('#project-end-date').value,
          status: modal.querySelector('#project-status').value
        };

        if (!formData.name || !formData.manager || !formData.start_date || !formData.end_date) {
          alert('Please fill in all required fields');
          return;
        }

        try {
          // In a real application, you would send this to your backend API
          // For now, we'll simulate success and refresh the data
          console.log('Creating new project:', formData);
          
          // Show success message
          alert('Project created successfully!');
          modal.remove();
          
          // Reload projects data
          await loadProjectsData();
        } catch (error) {
          console.error('Error creating project:', error);
          alert('Error creating project. Please try again.');
        }
      });
    }

    // Resources Data
    async function loadResourcesData() {
      try {
        const [resources, stats] = await Promise.all([
          fetchJson('/api/resources'),
          fetchJson('/api/resources/stats/utilization')
        ]);

        if (stats.success) {
          document.getElementById('total-resources').textContent = stats.data.totalResources;
          document.getElementById('avg-utilization').textContent = stats.data.averageUtilization + '%';
          document.getElementById('available-resources').textContent = stats.data.availableResources;
          document.getElementById('overallocated-resources').textContent = stats.data.overallocated;
        }

        if (resources.success) {
          const resourcesHtml = resources.data.map(resource => {
            const utilization = 100 - resource.availability;
            let statusClass = 'availability-high';
            let statusText = 'Available';
            
            if (resource.availability <= 20) {
              statusClass = 'availability-low';
              statusText = 'Fully Allocated';
            } else if (resource.availability <= 50) {
              statusClass = 'availability-medium';
              statusText = 'Partially Available';
            }

            return `
              <div class="resource-card">
                <div class="resource-header">
                  <div class="resource-avatar">
                    ${resource.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                  </div>
                  <div class="resource-info">
                    <h4>${resource.name}</h4>
                    <div class="resource-position">${resource.position}</div>
                  </div>
                </div>
                <div style="margin-bottom: 12px;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>Utilization</span>
                    <span class="${statusClass}">${utilization}%</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress-fill" style="width: ${utilization}%"></div>
                  </div>
                </div>
                <div style="font-size: 14px; color: var(--muted);">
                  <i class="fas fa-project-diagram"></i>
                  ${resource.currentProject || 'No project assigned'}
                </div>
                <div style="margin-top: 16px; display: flex; gap: 8px;">
                  <button class="btn btn-secondary" style="flex: 1; padding: 8px; font-size: 12px;">
                    <i class="fas fa-edit"></i> Edit
                  </button>
                  <button class="btn btn-primary" style="flex: 1; padding: 8px; font-size: 12px;">
                    <i class="fas fa-chart-bar"></i> Details
                  </button>
                </div>
              </div>
            `;
          }).join('');
          document.getElementById('resources-grid').innerHTML = resourcesHtml;
        }
      } catch (error) {
        console.error('Error loading resources data:', error);
      }
    }

    // Add New Resource Functionality
    function setupNewResourceButton() {
      const newResourceBtn = document.getElementById('new-resource-btn');
      if (newResourceBtn) {
        newResourceBtn.addEventListener('click', showNewResourceModal);
      }
    }

    function showNewResourceModal() {
      const modalContent = `
        <form id="new-resource-form">
          <div class="form-group">
            <label for="resource-name">Full Name</label>
            <input type="text" id="resource-name" class="input" required>
          </div>
          <div class="form-group">
            <label for="resource-position">Position</label>
            <select id="resource-position" class="input" required>
              <option value="">Select Position</option>
              <option value="Project Manager">Project Manager</option>
              <option value="Senior Developer">Senior Developer</option>
              <option value="Developer">Developer</option>
              <option value="UX Designer">UX Designer</option>
              <option value="QA Engineer">QA Engineer</option>
              <option value="DevOps Engineer">DevOps Engineer</option>
            </select>
          </div>
          <div class="form-group">
            <label for="resource-availability">Availability (%)</label>
            <input type="number" id="resource-availability" class="input" min="0" max="100" value="100" required>
          </div>
          <div class="form-group">
            <label for="resource-project">Current Project</label>
            <select id="resource-project" class="input">
              <option value="">No Project</option>
              <option value="E-commerce Platform">E-commerce Platform</option>
              <option value="Mobile Banking App">Mobile Banking App</option>
              <option value="CRM System">CRM System</option>
            </select>
          </div>
        </form>
      `;

      createModal('Add New Resource', modalContent, async (modal) => {
        const form = modal.querySelector('#new-resource-form');
        const formData = {
          name: modal.querySelector('#resource-name').value,
          position: modal.querySelector('#resource-position').value,
          availability: parseInt(modal.querySelector('#resource-availability').value),
          current_project: modal.querySelector('#resource-project').value || null
        };

        if (!formData.name || !formData.position) {
          alert('Please fill in all required fields');
          return;
        }

        try {
          // In a real application, you would send this to your backend API
          console.log('Creating new resource:', formData);
          
          // Show success message
          alert('Resource added successfully!');
          modal.remove();
          
          // Reload resources data
          await loadResourcesData();
        } catch (error) {
          console.error('Error adding resource:', error);
          alert('Error adding resource. Please try again.');
        }
      });
    }

    // Reports Data
    async function loadReportsData() {
      try {
        const reports = await fetchJson('/api/reports');
        if (reports.success) {
          const reportsHtml = reports.data.map(report => `
            <div class="report-card ${report.type.includes('Utilization') ? 'success' : 'warning'}">
              <div style="display: flex; justify-content: between; align-items: start; margin-bottom: 16px;">
                <h4 style="flex: 1; margin: 0;">${report.name}</h4>
                <span class="status-badge ${report.type.includes('Utilization') ? 'status-active' : 'status-planning'}">
                  ${report.type}
                </span>
              </div>
              <p style="color: var(--muted); margin-bottom: 16px; font-size: 14px;">
                Generated by ${report.generatedBy}
              </p>
              <div style="display: flex; justify-content: between; align-items: center;">
                <span style="font-size: 12px; color: var(--muted);">
                  ${new Date(report.createdAt).toLocaleDateString()}
                </span>
                <button class="btn btn-primary download-report" data-report-id="${report.id}" style="padding: 6px 12px; font-size: 12px;">
                  <i class="fas fa-download"></i> Download
                </button>
              </div>
            </div>
          `).join('');
          document.getElementById('reports-grid').innerHTML = reportsHtml;

          // Add download event listeners
          document.querySelectorAll('.download-report').forEach(btn => {
            btn.addEventListener('click', (e) => {
              const reportId = e.target.closest('.download-report').getAttribute('data-report-id');
              downloadReport(reportId);
            });
          });
        }

        // Initialize charts
        initializeCharts();
      } catch (error) {
        console.error('Error loading reports data:', error);
      }
    }

    // Export Report Functionality
    function setupExportReportButton() {
      const exportBtn = document.getElementById('export-report-btn');
      if (exportBtn) {
        exportBtn.addEventListener('click', showExportModal);
      }
    }

    function showExportModal() {
      const modalContent = `
        <form id="export-report-form">
          <div class="form-group">
            <label for="export-report-type">Report Type</label>
            <select id="export-report-type" class="input" required>
              <option value="resource_utilization">Resource Utilization</option>
              <option value="project_progress">Project Progress</option>
              <option value="team_performance">Team Performance</option>
              <option value="capacity_planning">Capacity Planning</option>
            </select>
          </div>
          <div class="form-group">
            <label for="export-date-range">Date Range</label>
            <select id="export-date-range" class="input" required>
              <option value="last_7_days">Last 7 Days</option>
              <option value="last_30_days">Last 30 Days</option>
              <option value="last_quarter">Last Quarter</option>
              <option value="last_year">Last Year</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>
          <div class="form-group" id="custom-date-range" style="display: none;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div>
                <label for="export-start-date">Start Date</label>
                <input type="date" id="export-start-date" class="input">
              </div>
              <div>
                <label for="export-end-date">End Date</label>
                <input type="date" id="export-end-date" class="input">
              </div>
            </div>
          </div>
          <div class="form-group">
            <label for="export-format">Export Format</label>
            <select id="export-format" class="input" required>
              <option value="pdf">PDF</option>
              <option value="excel">Excel</option>
              <option value="csv">CSV</option>
            </select>
          </div>
        </form>
      `;

      const modal = createModal('Export Report', modalContent, async (modal) => {
        const formData = {
          type: modal.querySelector('#export-report-type').value,
          dateRange: modal.querySelector('#export-date-range').value,
          format: modal.querySelector('#export-format').value,
          startDate: modal.querySelector('#export-start-date')?.value,
          endDate: modal.querySelector('#export-end-date')?.value
        };

        try {
          // Simulate export process
          await exportReport(formData);
          modal.remove();
        } catch (error) {
          console.error('Error exporting report:', error);
          alert('Error exporting report. Please try again.');
        }
      });

      // Show/hide custom date range
      modal.querySelector('#export-date-range').addEventListener('change', (e) => {
        const customRange = modal.querySelector('#custom-date-range');
        customRange.style.display = e.target.value === 'custom' ? 'block' : 'none';
      });
    }

    async function exportReport(options) {
      // Simulate export process
      const exportText = `Exporting ${options.type} report for ${options.dateRange} as ${options.format.toUpperCase()}...`;
      console.log(exportText);
      
      // Show loading state
      const originalText = document.querySelector('#reports-page .btn-success').innerHTML;
      document.querySelector('#reports-page .btn-success').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Reset button text
      document.querySelector('#reports-page .btn-success').innerHTML = originalText;
      
      // Create and download a mock file
      const content = `DevResource Report\nType: ${options.type}\nDate Range: ${options.dateRange}\nGenerated: ${new Date().toLocaleString()}`;
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `devresource-report-${options.type}-${new Date().getTime()}.${options.format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      alert('Report exported successfully!');
    }

    function downloadReport(reportId) {
      // Simulate download process
      console.log(`Downloading report ${reportId}...`);
      
      // Create and download a mock report file
      const content = `DevResource Report\nReport ID: ${reportId}\nDownloaded: ${new Date().toLocaleString()}\n\nThis is a sample report content.`;
      const blob = new Blob([content], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      alert('Report downloaded successfully!');
    }

    // Initialize Charts
    function initializeCharts() {
      // Utilization Chart
      const utilCtx = document.getElementById('utilizationChart').getContext('2d');
      new Chart(utilCtx, {
        type: 'line',
        data: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Resource Utilization',
            data: [65, 75, 70, 80, 75, 85],
            borderColor: '#6c63ff',
            backgroundColor: 'rgba(108, 99, 255, 0.1)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            }
          }
        }
      });

      // Project Chart
      const projectCtx = document.getElementById('projectChart').getContext('2d');
      new Chart(projectCtx, {
        type: 'doughnut',
        data: {
          labels: ['Active', 'Completed', 'Planning'],
          datasets: [{
            data: [60, 25, 15],
            backgroundColor: [
              '#10b981',
              '#6b7280',
              '#3b82f6'
            ]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom'
            }
          }
        }
      });
    }

    // Load user data
    async function loadUserData() {
      try {
        const response = await fetchJson('/api/auth/me');
        if (response.success) {
          const user = response.data;
          document.getElementById('user-name').textContent = user.name;
          document.getElementById('user-role').textContent = user.position;
          document.getElementById('user-avatar').textContent = 
            user.name.split(' ').map(n => n[0]).join('').toUpperCase();
        } else {
          window.location.href = '/';
        }
      } catch (error) {
        console.error('Error loading user data:', error);
        window.location.href = '/';
      }
    }

    // Setup page-specific event listeners
    function setupPageListeners() {
      setupNewProjectButton();
      setupNewResourceButton();
      setupExportReportButton();
    }

    // Event Listeners
    document.getElementById('logoutBtn').addEventListener('click', async () => {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/';
    });

    // Navigation event listeners
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const page = this.getAttribute('data-page');
        navigateTo(page);
      });
    });

    // Handle URL hash changes
    window.addEventListener('hashchange', () => {
      const page = window.location.hash.substring(1) || 'dashboard';
      if (pages[page]) {
        navigateTo(page);
      }
    });

    // Initialize the dashboard
    async function initDashboard() {
      await loadUserData();
      
      // Check URL hash for initial page
      const initialPage = window.location.hash.substring(1) || 'dashboard';
      if (pages[initialPage]) {
        navigateTo(initialPage);
      } else {
        navigateTo('dashboard');
      }

      // Setup page listeners
      setupPageListeners();
    }

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', initDashboard);
  </script>
</body>
</html>
"""

# Initialize database and run app
if __name__ == '__main__':
    # Initialize database
    with app.app_context():
        db.create_all()
        # Create default data if it doesn't exist
        if not User.query.first():
            u = User(name='Babafemi Oyindamola', email='john@example.com', 
                    password_hash=generate_password_hash('password'), 
                    position='Project Manager')
            db.session.add(u)
        if not Project.query.first():
            p1 = Project(name='E-commerce Platform', manager='Babafemi Oyindamola', 
                        start_date=datetime(2023,3,15).date(), 
                        end_date=datetime(2023,9,30).date(), status='active')
            p2 = Project(name='Mobile Banking App', manager='Akinleye Tolu', 
                        start_date=datetime(2023,5,1).date(), 
                        end_date=datetime(2023,11,15).date(), status='active')
            p3 = Project(name='CRM System', manager='Oluleye Philip', 
                        start_date=datetime(2023,1,10).date(), 
                        end_date=datetime(2023,7,31).date(), status='completed')
            db.session.add_all([p1,p2,p3])
        if not Resource.query.first():
            r1 = Resource(name='Benjamin Godswill', position='Project Manager', 
                         availability=0, current_project='E-commerce Platform')
            r2 = Resource(name='Akinleye Tolu', position='Senior Developer', 
                         availability=20, current_project='Mobile Banking App')
            r3 = Resource(name='Oluleye Philip', position='UX Designer', 
                         availability=0, current_project='CRM System')
            db.session.add_all([r1,r2,r3])
        db.session.commit()
        print("Database initialized successfully!")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)