# Here are some Dummy IDs for Signup:

# dummy company_id 1 = 11111111-1111-1111-1111-111111111111
# dummy department_id 1 for company 1= 11111111-1111-1111-0001-111111111111
# dummy department_id 2 for company 1= 11111111-1111-1111-0002-111111111111

# dummy company_id 2 = 22222222-2222-2222-2222-222222222222
# dummy department_id 1 for company 2= 22222222-2222-2222-0001-222222222222
# dummy department_id 2 for company 2= 22222222-2222-2222-0002-222222222222

import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, session, redirect, url_for, render_template_string

app = Flask(__name__)
app.secret_key = "super_secret_development_key"

HTML_LOGIN = """
<h2>Employee Login</h2>
<form action="/process_login" method="POST">
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required><br><br>
    <button type="submit">Login</button>
</form>
<p>Don't have an account? <a href="/signup">Sign up here</a></p>
{% if error_message %}
<p style="color:red;">{{ error_message }}</p>
{% endif %}
"""

HTML_SIGNUP = """
<h2>Employee Signup</h2>
<form action="/save_user" method="POST">
    Name: <input type="text" name="name" required><br><br>
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required><br><br>
    Company ID: <input type="text" name="company_id" required><br><br>
    Department ID: <input type="text" name="department_id" required><br><br>
    <button type="submit">Submit to Database</button>
</form>
"""

HTML_DASHBOARD = """
<h2>Welcome to your Dashboard, {{ user_name }}!</h2>
<h3>Your Information:</h3>
<ul>
    <li><strong>Employee ID:</strong> {{ user_info[0] }}</li>
    <li><strong>Company:</strong> {{ user_info[1] if user_info[1] else 'N/A' }}</li>
    <li><strong>Department:</strong> {{ user_info[2] if user_info[2] else 'N/A' }}</li>
    <li><strong>Name:</strong> {{ user_info[3] }}</li>
    <li><strong>Email:</strong> {{ user_info[4] }}</li>
    <li><strong>Language Preference:</strong> {{ user_info[5] if user_info[5] else 'Not Set' }}</li>
    <li><strong>Status:</strong> {{ user_info[6] }}</li>
    <li><strong>Account Created:</strong> {{ user_info[7] }}</li>
</ul>
<br>
<a href="/feedbacks"><button>View All Feedback</button></a>
<a href="/edit_profile"><button>Edit Profile</button></a>
<a href="/logout"><button>Logout</button></a>
"""

HTML_EDIT_PROFILE = """
<h2>Edit Your Profile</h2>
<form action="/update_profile" method="POST">
    <input type="hidden" name="user_id" value="{{ user_info[0] }}">
    Name: <input type="text" name="name" value="{{ user_info[3] }}" required><br><br>
    Email: <input type="email" name="email" value="{{ user_info[4] }}" required><br><br>
    Language Preference: <input type="text" name="language_preference" value="{{ user_info[5] if user_info[5] else '' }}"><br><br>
    Status: <input type="text" name="status" value="{{ user_info[6] if user_info[6] else '' }}" required><br><br>
    Company ID: <input type="text" name="company_id" value="{{ user_info[8] if user_info[8] else '' }}" required><br><br>
    Department ID: <input type="text" name="department_id" value="{{ user_info[9] if user_info[9] else '' }}" required><br><br>
    <button type="submit">Update Profile</button>
</form>
<br>
<a href="/dashboard"><button>Back to Dashboard</button></a>
{% if error_message %}
<p style="color:red;">{{ error_message }}</p>
{% endif %}
{% if success_message %}
<p style="color:green;">{{ success_message }}</p>
{% endif %}
"""

HTML_FEEDBACKS = """
<h2>Company Feedback Listing</h2>
<table border="1" cellpadding="10" style="border-collapse: collapse;">
    <tr style="background-color: #f2f2f2;">
        <th>Date Submitted</th>
        <th>Employee Name</th>
        <th>Department</th>
        <th>Overall Sentiment</th>
        <th>Topic</th>
    </tr>
    {% for row in feedbacks %}
    <tr>
        <td>{{ row[0] }}</td>
        <td>{{ row[1] }}</td>
        <td>{{ row[2] if row[2] else 'N/A' }}</td>
        <td>{{ row[3] if row[3] else 'Pending AI Analysis' }}</td>
        <td>{{ row[4] if row[4] else 'Pending AI Analysis' }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5">No feedback found.</td></tr>
    {% endfor %}
</table>
<br>
<a href="/dashboard"><button>Back to Dashboard</button></a>
"""

def get_db_connection():
    return psycopg2.connect(
        dbname="employee_feedback",
        user="postgres",
        password="postgres",
        host="localhost"
    )

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(HTML_LOGIN, error_message=None)

@app.route('/signup')
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(HTML_SIGNUP)

@app.route('/save_user', methods=['POST'])
def save_user():
    user_name = request.form['name']
    user_email = request.form['email']
    raw_password = request.form['password']
    comp_id = request.form['company_id']
    dept_id = request.form['department_id']

    encoded_password = generate_password_hash(raw_password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO employees (company_id, department_id, name, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (comp_id, dept_id, user_name, user_email, encoded_password)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Database Error: {e}"
    finally:
        cursor.close()
        conn.close()

    return f"Success! Account is created. <a href='/login'>Go to Login page</a>"

@app.route('/process_login', methods=['POST'])
def process_login():
    email_input = request.form['email']
    password_input = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, password_hash FROM employees WHERE email = %s", (email_input,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user[2], password_input):
        session['user_id'] = str(user[0])
        session['user_name'] = user[1]
        return redirect(url_for('dashboard'))
    else:
        return render_template_string(HTML_LOGIN, error_message='Invalid email or password.')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT e.id, c.name AS company_name, d.name AS department_name,
               e.name AS employee_name, e.email, e.language_preference,
               e.status, e.created_at, e.company_id, e.department_id
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = %s
    """
    cursor.execute(query, (session['user_id'],))
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user_info:
        return redirect(url_for('logout'))

    return render_template_string(HTML_DASHBOARD, user_name=session['user_name'], user_info=user_info)

@app.route('/edit_profile')
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT e.id, c.name AS company_name, d.name AS department_name,
               e.name AS employee_name, e.email, e.language_preference,
               e.status, e.created_at, e.company_id, e.department_id
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = %s
    """
    cursor.execute(query, (session['user_id'],))
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user_info:
        return redirect(url_for('logout'))

    return render_template_string(HTML_EDIT_PROFILE, user_info=user_info,
                                  error_message=None, success_message=None)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    name = request.form['name']
    email = request.form['email']
    language_preference = request.form.get('language_preference')
    status = request.form['status']
    company_id = request.form['company_id']
    department_id = request.form['department_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE employees
            SET name = %s, email = %s, language_preference = %s, status = %s,
                company_id = %s, department_id = %s
            WHERE id = %s
            """,
            (name, email, language_preference, status, company_id, department_id, user_id)
        )
        conn.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        conn.rollback()
        error_message = f"Database Error: {e}"
        query = """
            SELECT e.id, c.name AS company_name, d.name AS department_name,
                   e.name AS employee_name, e.email, e.language_preference,
                   e.status, e.created_at, e.company_id, e.department_id
            FROM employees e
            LEFT JOIN companies c ON e.company_id = c.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.id = %s
        """
        cursor.execute(query, (user_id,))
        user_info = cursor.fetchone()
        
        return render_template_string(HTML_EDIT_PROFILE, user_info=user_info,
                                      error_message=error_message, success_message=None)
    finally:
        cursor.close()
        conn.close()

@app.route('/feedbacks')
def feedbacks():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            fs.date_submitted, 
            CASE WHEN fs.is_anonymous THEN 'Anonymous' ELSE e.name END as employee_name,
            d.name as department_name,
            s.overall_sentiment,
            STRING_AGG(DISTINCT t.topic_label, ', ') as topics
        FROM feedback_submissions fs
        LEFT JOIN employees e ON fs.employee_id = e.id
        LEFT JOIN departments d ON fs.department_id = d.id
        LEFT JOIN feedback_sentiment s ON fs.id = s.submission_id
        LEFT JOIN feedback_topics t ON fs.id = t.submission_id
        GROUP BY
            fs.id,
            fs,date_submitted,
            fs.is_anonymous,
            e.name,
            d.name,
            s.overall_sentiment
        ORDER BY fs.date_submitted DESC;
    """
    
    cursor.execute(query)
    feedback_data = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template_string(HTML_FEEDBACKS, feedbacks=feedback_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(port=5000, debug=True)