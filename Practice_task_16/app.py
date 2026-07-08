import json
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, session, redirect, url_for, render_template_string

app = Flask(__name__)
app.secret_key = "super_secret_development_key"

# Navbar

def render_nav():
    """
    Builds the nav bar HTML. Admin-only links (User Management, Feedback
    Management, Department Management, Company Management, Questions
    Management) only appear when the logged-in user's role is admin.
    """
    links = ['<a href="/dashboard">Dashboard</a>']

    if is_admin():
        links += [
            '<a href="/admin/users">User Management</a>',
            '<a href="/feedbacks">Feedback Management</a>',
            '<a href="/companies">Company Management</a>',
            '<a href="/companies">Department Management</a>',
            '<a href="/questions">Questions Management</a>',
            '<a href="/analytics">Analytics</a>',
        ]
    else:
        links += [
            '<a href="/companies">Companies</a>',
            '<a href="/questions">Questions</a>',
            '<a href="/feedbacks">Feedbacks</a>',
            '<a href="/analytics">Analytics</a>',
        ]

    links.append('<a href="/logout">Logout</a>')

    return "<p>\n  " + "\n  | ".join(links) + "\n</p>\n<hr>\n"

# Login

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

# Signup

HTML_SIGNUP = """
<h2>Employee Signup</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}
{% if no_admin_yet %}
<p style="color:blue;">No admin account exists yet. Check "Register as Admin" below to become the first admin.</p>
{% endif %}
<form action="/save_user" method="POST">
    Name: <input type="text" name="name" required><br><br>
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required minlength="6"><br><br>
    Re-enter Password: <input type="password" name="confirm_password" required minlength="6"><br><br>

    Company:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        <option value="">-- Select Company --</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>

    Department:
    <select name="department_id" id="departmentSelect" required disabled>
        <option value="">-- Select Company First --</option>
    </select><br><br>

    {% if no_admin_yet %}
    <label>
        <input type="checkbox" name="register_as_admin" value="yes">
        Register as Admin (only available because no admin account exists yet)
    </label><br><br>
    {% endif %}

    <button type="submit">Submit to Database</button>
</form>
<p>Already registered? <a href="/login">Go to Login</a></p>

<script>
// All departments for every company, grouped by company_id.
// Rendered server-side so no extra request is needed when the
// user picks a company from the dropdown.
const departmentsByCompany = {{ departments_by_company_json | safe }};

function loadDepartments() {
    const companyId = document.getElementById('companySelect').value;
    const deptSelect = document.getElementById('departmentSelect');
    deptSelect.innerHTML = '';

    if (!companyId) {
        deptSelect.disabled = true;
        deptSelect.innerHTML = '<option value="">-- Select Company First --</option>';
        return;
    }

    const depts = departmentsByCompany[companyId] || [];
    deptSelect.disabled = false;

    if (depts.length === 0) {
        deptSelect.innerHTML = '<option value="">-- No Departments --</option>';
        return;
    }

    deptSelect.innerHTML = '<option value="">-- Select Department --</option>';
    depts.forEach(function(dept) {
        const opt = document.createElement('option');
        opt.value = dept.id;
        opt.textContent = dept.name;
        deptSelect.appendChild(opt);
    });
}
</script>
"""

# Dashboard

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

{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}
{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}

<a href="/submit_feedback"><button>Submit Feedback</button></a>
<a href="/feedbacks"><button>View All Feedback</button></a>
<a href="/edit_profile"><button>Edit Profile</button></a>

<hr>
<h3>Your Past Submissions</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>Date Submitted</th>
        <th>Question</th>
        <th>Your Answer</th>
        <th>Actions</th>
    </tr>
    {% for row in my_submissions %}
    <tr>
        <td>{{ row[0] }}</td>
        <td>{{ row[2] }}</td>
        <td>{{ row[3] }}</td>
        <td><a href="/my_feedback/{{ row[1] }}/edit"><button>Edit</button></a></td>
    </tr>
    {% else %}
    <tr><td colspan="4">You haven't submitted any feedback yet.</td></tr>
    {% endfor %}
</table>
"""

# Edit Profile

HTML_EDIT_PROFILE = """
<h2>Edit Your Profile</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}
{% if success_message %}<p style="color:green;">{{ success_message }}</p>{% endif %}
<form action="/update_profile" method="POST">
    <input type="hidden" name="user_id" value="{{ user_info[0] }}">
    Name: <input type="text" name="name" value="{{ user_info[3] }}" required><br><br>
    Email: <input type="email" name="email" value="{{ user_info[4] }}" required><br><br>
    Language Preference:
    <select name="language_preference">
      <option value="en" {{ 'selected' if user_info[5]=='en' }}>English</option>
      <option value="tr" {{ 'selected' if user_info[5]=='tr' }}>Turkish</option>
    </select><br><br>
    Status:
    <select name="status">
      <option value="active"   {{ 'selected' if user_info[6]=='active' }}>Active</option>
      <option value="inactive" {{ 'selected' if user_info[6]=='inactive' }}>Inactive</option>
    </select><br><br>
    Company ID: <input type="text" name="company_id" value="{{ user_info[8] if user_info[8] else '' }}" required><br><br>
    Department ID: <input type="text" name="department_id" value="{{ user_info[9] if user_info[9] else '' }}"><br><br>
    <button type="submit">Update Profile</button>
</form>
<br>
<a href="/dashboard"><button>Back to Dashboard</button></a>
"""

# Feedback

HTML_FEEDBACKS = """
<h2>Company Feedback Listing</h2>
<table border="1" cellpadding="10" style="border-collapse: collapse;">
    <tr>
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

# Companies list

HTML_COMPANIES = """
<h2>Companies</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>Create New Company</h3>
<form action="/companies/create" method="POST">
    Name: <input type="text" name="name" required><br><br>
    Industry: <input type="text" name="industry"><br><br>
    Status:
    <select name="status">
      <option value="active">Active</option>
      <option value="inactive">Inactive</option>
    </select><br><br>
    <button type="submit">Create Company</button>
</form>

<hr>
<h3>Search Companies</h3>
<input type="text" id="searchInput" placeholder="Type to search by name..." oninput="filterTable()"><br><br>

<h3>All Companies</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>Name</th>
        <th>Industry</th>
        <th>Status</th>
        <th>Created</th>
        <th>Actions</th>
    </tr>
    {% for c in companies %}
    <tr class="company-row">
        <td class="company-name">{{ c[1] }}</td>
        <td>{{ c[2] if c[2] else '—' }}</td>
        <td>{{ c[3] }}</td>
        <td>{{ c[4].strftime('%d %b %Y') if c[4] else '—' }}</td>
        <td>
            <a href="/companies/{{ c[0] }}"><button>View</button></a>

            <form action="/companies/{{ c[0] }}/update" method="POST" style="display:inline;">
                <input type="text" name="name" value="{{ c[1] }}" required>
                <input type="text" name="industry" value="{{ c[2] if c[2] else '' }}">
                <select name="status">
                  <option value="active"   {{ 'selected' if c[3]=='active' }}>Active</option>
                  <option value="inactive" {{ 'selected' if c[3]=='inactive' }}>Inactive</option>
                </select>
                <button type="submit">Update</button>
            </form>

            <form action="/companies/{{ c[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete {{ c[1] }}?')">
                <button type="submit">Delete</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5">No companies found.</td></tr>
    {% endfor %}
</table>

<script>
function filterTable() {
    var q = document.getElementById('searchInput').value.toLowerCase();
    var rows = document.querySelectorAll('.company-row');
    rows.forEach(function(row) {
        var name = row.querySelector('.company-name').textContent.toLowerCase();
        row.style.display = name.includes(q) ? '' : 'none';
    });
}
</script>
"""

# Company Detail
HTML_COMPANY_DETAIL = """
<a href="/companies"><button>&larr; Back to Companies</button></a>
<br><br>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h2>Company Details</h2>
<ul>
    <li><strong>ID:</strong> {{ company[0] }}</li>
    <li><strong>Name:</strong> {{ company[1] }}</li>
    <li><strong>Industry:</strong> {{ company[2] if company[2] else 'Not specified' }}</li>
    <li><strong>Status:</strong> {{ company[3] }}</li>
    <li><strong>Created:</strong> {{ company[4].strftime('%d %b %Y') if company[4] else '—' }}</li>
    <li><strong>Updated:</strong> {{ company[5].strftime('%d %b %Y') if company[5] else '—' }}</li>
</ul>

<h3>Edit Company</h3>
<form action="/companies/{{ company[0] }}/update" method="POST">
    Name: <input type="text" name="name" value="{{ company[1] }}" required><br><br>
    Industry: <input type="text" name="industry" value="{{ company[2] if company[2] else '' }}"><br><br>
    Status:
    <select name="status">
      <option value="active"   {{ 'selected' if company[3]=='active' }}>Active</option>
      <option value="inactive" {{ 'selected' if company[3]=='inactive' }}>Inactive</option>
    </select><br><br>
    <button type="submit">Save Changes</button>
</form>

<hr>
<h2>Departments ({{ departments|length }})</h2>

<h3>Add Department</h3>
<form action="/companies/{{ company[0] }}/departments/create" method="POST">
    Name: <input type="text" name="name" required><br><br>
    Min Display Count: <input type="number" name="min_display_count" min="1"><br><br>
    <button type="submit">Add Department</button>
</form>

<br>
<table border="2" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>Name</th>
        <th>Department ID</th>
        <th>Min Display Count</th>
        <th>Created</th>
        <th>Actions</th>
    </tr>
    {% for d in departments %}
    <tr>
        <td>{{ d[2] }}</td>
        <td>{{ d[9] }}</td>
        <td>{{ d[3] if d[3] is not none else '—' }}</td>
        <td>{{ d[4].strftime('%d %b %Y') if d[4] else '—' }}</td>
        <td>
            <form action="/departments/{{ d[0] }}/update" method="POST" style="display:inline;">
                <input type="hidden" name="company_id" value="{{ company[0] }}">
                <input type="text" name="name" value="{{ d[2] }}" required>
                <input type="number" name="min_display_count" value="{{ d[3] if d[3] is not none else '' }}" min="1">
                <button type="submit">Update</button>
            </form>

            {% if d[2] != 'No Department' %}
            <form action="/departments/{{ d[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete department {{ d[2] }}?')">
                <input type="hidden" name="company_id" value="{{ company[0] }}">
                <button type="submit">Delete</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5">No departments yet.</td></tr>
    {% endfor %}
</table>
"""

# Questions

HTML_QUESTIONS = """
<h2>Questions</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>Create New Question</h3>
<form action="/questions/create" method="POST">
    Company:
    <select name="company_id" required>
        <option value="">-- Select Company --</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>

    Question Text (English): <input type="text" name="question_text_en" required style="width:300px;"><br><br>
    Question Text (Turkish): <input type="text" name="question_text_tr" style="width:300px;"><br><br>
    Order Index: <input type="number" name="order_index" min="1" max="3" value="1"><br><br>

    <p>Note: a company can have a maximum of 3 questions. If the index you pick is already used by another question, that question will automatically move to the remaining free index. Departments can be assigned after creation using the Edit page.</p>
    <button type="submit">Create Question</button>
</form>

<hr>
<h3>All Questions</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>Company</th>
        <th>Question (EN)</th>
        <th>Question (TR)</th>
        <th>Order</th>
        <th>Departments</th>
        <th>Active</th>
        <th>Actions</th>
    </tr>
    {% for q in questions %}
    <tr>
        <td>{{ q[8] }}</td>
        <td>{{ q[2] }}</td>
        <td>{{ q[3] if q[3] else '—' }}</td>
        <td>{{ q[4] }}</td>
        <td>{{ q[9] if q[9] else 'No departments assigned' }}</td>
        <td>{{ 'Yes' if q[5] else 'No' }}</td>
        <td>
            <a href="/questions/{{ q[0] }}/edit"><button>Edit</button></a>
            <form action="/questions/{{ q[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete this question?')">
                <button type="submit">Delete</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="7">No questions found.</td></tr>
    {% endfor %}
</table>
"""

# Edit Question page

HTML_QUESTION_EDIT = """
<a href="/questions"><button>&larr; Back to Questions</button></a>
<br><br>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}

<h2>Edit Question</h2>
<form action="/questions/{{ question[0] }}/update" method="POST">
    <p><strong>Company:</strong> {{ company_name }}</p>

    Question Text (English):
    <input type="text" name="question_text_en" value="{{ question[2] }}" required style="width:300px;"><br><br>

    Question Text (Turkish):
    <input type="text" name="question_text_tr" value="{{ question[3] if question[3] else '' }}" style="width:300px;"><br><br>

    Order Index: <input type="number" name="order_index" min="1" max="3" value="{{ question[4] }}" oninput="if(parseInt(this.value) > 3) this.value = 3; if(parseInt(this.value) < 1) this.value = 1;">><br><br>

    Active:
    <select name="is_active">
        <option value="true"  {{ 'selected' if question[5] }}>Yes</option>
        <option value="false" {{ 'selected' if not question[5] }}>No</option>
    </select><br><br>

    <p><strong>Departments</strong> (this question applies to):</p>
    {% if departments %}
   
    <label style="font-weight: normal; cursor: pointer;">
        <input type="checkbox" id="select-all-toggle"> All Departments
    </label><br><hr style="width: 200px; margin: 5px 0; border: 0; border-top: 1px solid #ccc;">
    {% endif %}

    {% for d in departments %}
    <label style="cursor: pointer;">
        <!-- Added class="dept-box" to target these instantly -->
        <input type="checkbox" name="department_ids" value="{{ d[0] }}" class="dept-box"
               {{ 'checked' if d[0] in assigned_department_ids }}>
        {{ d[1] }}
    </label><br>
    {% else %}
    <p>This company has no departments yet.</p>
    {% endfor %}
    <br>

    <button type="submit">Save Changes</button>
</form>

<script>
// This block runs inside the browser to handle the instant checkbox filling
document.getElementById('select-all-toggle')?.addEventListener('change', function() {
    const allDeptBoxes = document.querySelectorAll('.dept-box');
    allDeptBoxes.forEach(box => {
        box.checked = this.checked; // Instantly matches all boxes to the "All" checkbox state
    });
});

document.querySelectorAll('.dept-box').forEach(box => {
    box.addEventListener('change', function() {
        const masterToggle = document.getElementById('select-all-toggle');
        if (!this.checked && masterToggle) {
            masterToggle.checked = false; 
        }
    });
});
</script>
"""

# Submit Feedback page

HTML_SUBMIT_FEEDBACK = """
<a href="/dashboard"><button>&larr; Back to Dashboard</button></a>
<br><br>

<h2>Submit Today's Feedback</h2>
<p><strong>Company:</strong> {{ company_name }} &nbsp;|&nbsp; <strong>Department:</strong> {{ department_name }}</p>

{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

{% if already_submitted %}
<p style="color:green;">You have already submitted feedback today. Come back tomorrow!</p>
<a href="/dashboard"><button>Back to Dashboard</button></a>

{% elif not questions %}
<p>There are no questions assigned to your department yet. Please check back later.</p>
<a href="/dashboard"><button>Back to Dashboard</button></a>

{% else %}
<form action="/submit_feedback" method="POST">
    {% for q in questions %}
    <div style="margin-bottom:20px;">
        <label><strong>{{ loop.index }}. {{ q[1] }}</strong></label><br>
        <input type="hidden" name="question_id_{{ loop.index }}" value="{{ q[0] }}">
        <textarea name="answer_{{ loop.index }}" rows="3" cols="60" required></textarea>
    </div>
    {% endfor %}
    <input type="hidden" name="question_count" value="{{ questions|length }}">
    <button type="submit">Submit Feedback</button>
</form>
{% endif %}
"""

# Analytics Dashboard

HTML_ANALYTICS = """
<h2>Analytics Dashboard</h2>
<p>Visual overview of feedback, employees, and department activity.</p>

<div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:24px;">
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>Total Feedback Submissions</strong><br>
        <span style="font-size:28px;">{{ stats.total_submissions }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>Total Employees</strong><br>
        <span style="font-size:28px;">{{ stats.total_employees }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>Total Departments</strong><br>
        <span style="font-size:28px;">{{ stats.total_departments }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>Total Companies</strong><br>
        <span style="font-size:28px;">{{ stats.total_companies }}</span>
    </div>
</div>

<table border="0" cellspacing="0" cellpadding="0" style="width:100%;">
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Feedback Sentiment Breakdown</h3>
    <canvas id="sentimentPieChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Feedback Volume by Department</h3>
    <canvas id="deptBarChart" height="260"></canvas>
  </td>
</tr>
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Employees per Company</h3>
    <canvas id="employeesPieChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Departments per Company</h3>
    <canvas id="deptCountBarChart" height="260"></canvas>
  </td>
</tr>
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Feedback Submissions Over Time</h3>
    <canvas id="submissionsLineChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>Distribution of Answer Lengths (Histogram)</h3>
    <canvas id="answerLengthHistogram" height="260"></canvas>
  </td>
</tr>
</table>

<br>
<a href="/dashboard"><button>Back to Dashboard</button></a>

<!-- Chart.js via CDN -- no server-side chart library / image rendering needed -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>
// All chart data is rendered server-side into JSON below by Flask/Jinja,
// then handed straight to Chart.js on the client.
const sentimentData        = {{ sentiment_json | safe }};
const deptVolumeData       = {{ dept_volume_json | safe }};
const employeesByCompany   = {{ employees_by_company_json | safe }};
const deptCountByCompany   = {{ dept_count_by_company_json | safe }};
const submissionsOverTime  = {{ submissions_over_time_json | safe }};
const answerLengthBuckets  = {{ answer_length_histogram_json | safe }};

// 1. PIE CHART — Sentiment breakdown (positive / neutral / negative)
new Chart(document.getElementById('sentimentPieChart'), {
    type: 'pie',
    data: {
        labels: sentimentData.labels,
        datasets: [{
            data: sentimentData.values,
            backgroundColor: ['#4caf50', '#ffc107', '#f44336', '#9e9e9e']
        }]
    },
    options: { responsive: true }
});

// 2. BAR CHART — Feedback volume by department
new Chart(document.getElementById('deptBarChart'), {
    type: 'bar',
    data: {
        labels: deptVolumeData.labels,
        datasets: [{
            label: 'Submissions',
            data: deptVolumeData.values,
            backgroundColor: 'teal'
        }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
});

// 3. PIE CHART — Employees per company
new Chart(document.getElementById('employeesPieChart'), {
    type: 'pie',
    data: {
        labels: employeesByCompany.labels,
        datasets: [{
            data: employeesByCompany.values,
            backgroundColor: ['#3f51b5', '#009688', '#ff5722', '#795548', '#607d8b', '#e91e63']
        }]
    },
    options: { responsive: true }
});

// 4. BAR CHART — Departments per company
new Chart(document.getElementById('deptCountBarChart'), {
    type: 'bar',
    data: {
        labels: deptCountByCompany.labels,
        datasets: [{
            label: 'Departments',
            data: deptCountByCompany.values,
            backgroundColor: 'orange'
        }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
});

// 5. LINE CHART — Feedback submissions over time (by date)
new Chart(document.getElementById('submissionsLineChart'), {
    type: 'line',
    data: {
        labels: submissionsOverTime.labels,
        datasets: [{
            label: 'Submissions',
            data: submissionsOverTime.values,
            borderColor: 'purple',
            backgroundColor: 'rgba(103,58,183,0.15)',
            fill: true,
            tension: 0.25
        }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
});

// 6. HISTOGRAM (bar chart w/ bucketed ranges) — Answer text length distribution
new Chart(document.getElementById('answerLengthHistogram'), {
    type: 'bar',
    data: {
        labels: answerLengthBuckets.labels,
        datasets: [{
            label: 'Number of Answers',
            data: answerLengthBuckets.values,
            backgroundColor: '#527512'
        }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
});
</script>
"""

# Edit My Feedback (own submissions only)

HTML_EDIT_MY_FEEDBACK = """
<a href="/dashboard"><button>&larr; Back to Dashboard</button></a>
<br><br>

<h2>Edit Your Feedback</h2>
<p><strong>Date Submitted:</strong> {{ submission[1] }}</p>

{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

<form action="/my_feedback/{{ submission[0] }}/update" method="POST">
    {% for a in answers %}
    <div style="margin-bottom:20px;">
        <label><strong>{{ loop.index }}. {{ a[1] }}</strong></label><br>
        <input type="hidden" name="answer_id_{{ loop.index }}" value="{{ a[0] }}">
        <textarea name="answer_text_{{ loop.index }}" rows="3" cols="60" required>{{ a[2] }}</textarea>
    </div>
    {% endfor %}
    <input type="hidden" name="answer_count" value="{{ answers|length }}">
    <button type="submit">Save Changes</button>
</form>
"""

# Admin: User Management

HTML_ADMIN_USERS = """
<h2>User Management</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>Create New User</h3>
<form action="/admin/users/create" method="POST">
    Name: <input type="text" name="name" required><br><br>
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required minlength="6"><br><br>
    Role:
    <select name="role">
      <option value="employee">Employee</option>
      <option value="admin">Admin</option>
    </select><br><br>
    Company:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        <option value="">-- Select Company --</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    Department:
    <select name="department_id" id="departmentSelect" required disabled>
        <option value="">-- Select Company First --</option>
    </select><br><br>
    <button type="submit">Create User</button>
</form>

<hr>
<h3>Search &amp; Sort</h3>
<form action="/admin/users" method="GET">
    Search (name or email): <input type="text" name="q" value="{{ search_query }}" placeholder="Type to search..."><br><br>
    Sort by:
    <select name="sort">
        <option value="recent"   {{ 'selected' if sort_by=='recent' }}>Most Recent First</option>
        <option value="oldest"   {{ 'selected' if sort_by=='oldest' }}>Oldest First</option>
        <option value="name_asc" {{ 'selected' if sort_by=='name_asc' }}>Name (A-Z)</option>
        <option value="name_desc"{{ 'selected' if sort_by=='name_desc' }}>Name (Z-A)</option>
        <option value="email_asc"{{ 'selected' if sort_by=='email_asc' }}>Email (A-Z)</option>
    </select>
    <button type="submit">Apply</button>
    <a href="/admin/users"><button type="button">Reset</button></a>
</form>

<hr>
<h3>All Users ({{ users|length }})</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Role</th>
        <th>Company</th>
        <th>Department</th>
        <th>Status</th>
        <th>Created</th>
        <th>Actions</th>
    </tr>
    {% for u in users %}
    <tr>
        <td>{{ u[1] }}</td>
        <td>{{ u[2] }}</td>
        <td>{{ u[3] }}</td>
        <td>{{ u[4] if u[4] else 'N/A' }}</td>
        <td>{{ u[5] if u[5] else 'N/A' }}</td>
        <td>{{ u[6] }}</td>
        <td>{{ u[7].strftime('%d %b %Y') if u[7] else '—' }}</td>
        <td>
            <a href="/admin/users/{{ u[0] }}/edit"><button>Edit</button></a>
            <form action="/admin/users/{{ u[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete user {{ u[1] }}? This cannot be undone.')">
                <button type="submit">Delete</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="8">No users found.</td></tr>
    {% endfor %}
</table>

<script>
const departmentsByCompany = {{ departments_by_company_json | safe }};

function loadDepartments() {
    const companyId = document.getElementById('companySelect').value;
    const deptSelect = document.getElementById('departmentSelect');
    deptSelect.innerHTML = '';

    if (!companyId) {
        deptSelect.disabled = true;
        deptSelect.innerHTML = '<option value="">-- Select Company First --</option>';
        return;
    }

    const depts = departmentsByCompany[companyId] || [];
    deptSelect.disabled = false;

    if (depts.length === 0) {
        deptSelect.innerHTML = '<option value="">-- No Departments --</option>';
        return;
    }

    deptSelect.innerHTML = '<option value="">-- Select Department --</option>';
    depts.forEach(function(dept) {
        const opt = document.createElement('option');
        opt.value = dept.id;
        opt.textContent = dept.name;
        deptSelect.appendChild(opt);
    });
}
</script>
"""

# Admin: Edit single user

HTML_ADMIN_USER_EDIT = """
<a href="/admin/users"><button>&larr; Back to User Management</button></a>
<br><br>

<h2>Edit User</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

<form action="/admin/users/{{ user[0] }}/update" method="POST">
    Name: <input type="text" name="name" value="{{ user[1] }}" required><br><br>
    Email: <input type="email" name="email" value="{{ user[2] }}" required><br><br>
    New Password (leave blank to keep current):
    <input type="password" name="password" minlength="6"><br><br>
    Role:
    <select name="role">
      <option value="employee" {{ 'selected' if user[3]=='employee' }}>Employee</option>
      <option value="admin"    {{ 'selected' if user[3]=='admin' }}>Admin</option>
    </select><br><br>
    Status:
    <select name="status">
      <option value="active"   {{ 'selected' if user[6]=='active' }}>Active</option>
      <option value="inactive" {{ 'selected' if user[6]=='inactive' }}>Inactive</option>
    </select><br><br>

    Company:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        {% for c in companies %}
        <option value="{{ c[0] }}" {{ 'selected' if c[0]|string == user[8]|string }}>{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    Department:
    <select name="department_id" id="departmentSelect" required>
        {% for d in current_company_departments %}
        <option value="{{ d[0] }}" {{ 'selected' if d[0]|string == user[9]|string }}>{{ d[1] }}</option>
        {% endfor %}
    </select><br><br>

    <button type="submit">Save Changes</button>
</form>

<script>
const departmentsByCompany = {{ departments_by_company_json | safe }};

function loadDepartments(preserveSelection) {
    const companyId = document.getElementById('companySelect').value;
    const deptSelect = document.getElementById('departmentSelect');
    const depts = departmentsByCompany[companyId] || [];
    deptSelect.innerHTML = '';

    if (depts.length === 0) {
        deptSelect.innerHTML = '<option value="">-- No Departments --</option>';
        return;
    }
    depts.forEach(function(dept) {
        const opt = document.createElement('option');
        opt.value = dept.id;
        opt.textContent = dept.name;
        deptSelect.appendChild(opt);
    });
}
</script>
"""

# DB CONNECTION

def get_db_connection():
    return psycopg2.connect(
        dbname="employee_feedback",
        user="postgres",
        password="postgres",
        host="localhost"
    )

DEFAULT_DEPARTMENT_NAME = "No Department"

def get_or_create_default_department(cursor, company_id):
    """
    Returns the id of the 'No Department' row for this company.
    Creates it if it doesn't exist yet (e.g. for companies created
    before this logic existed, or right after a fresh company create).
    """
    cursor.execute("""
        SELECT id FROM departments
        WHERE company_id = %s AND name = %s
    """, (company_id, DEFAULT_DEPARTMENT_NAME))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("""
        INSERT INTO departments (company_id, name, min_display_count)
        VALUES (%s, %s, NULL)
        RETURNING id
    """, (company_id, DEFAULT_DEPARTMENT_NAME))
    return cursor.fetchone()[0]

def resolve_department_id(cursor, company_id, department_id):
    """
    Ensures department_id actually belongs to company_id.
    If department_id is missing/blank or belongs to a different
    company, falls back to that company's default department.
    """
    if department_id:
        cursor.execute("""
            SELECT id FROM departments
            WHERE id = %s AND company_id = %s
        """, (department_id, company_id))
        if cursor.fetchone():
            return department_id
    return get_or_create_default_department(cursor, company_id)

MAX_QUESTIONS_PER_COMPANY = 3

def ensure_question_department_table():
    """
    The schema document only defines `questions` with a single
    company_id FK. Since a question must support MULTIPLE
    departments, we need a join table. Created once at startup
    if it doesn't already exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_departments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (question_id, department_id)
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Could not ensure question_departments table: {e}")
    finally:
        cursor.close()
        conn.close()

def count_company_questions(cursor, company_id):
    cursor.execute("SELECT COUNT(*) FROM questions WHERE company_id = %s", (company_id,))
    return cursor.fetchone()[0]

# ROLE / ADMIN HELPERS

ROLE_ADMIN    = 'admin'
ROLE_EMPLOYEE = 'employee'

def ensure_role_column():
    """
    The schema document's `employees` table has no role column, but we
    need to distinguish admins from regular employees. Added once at
    startup if missing, defaulting every existing row to 'employee'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'employee'
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Could not ensure role column: {e}")
    finally:
        cursor.close()
        conn.close()

def is_admin():
    return session.get('user_role') == ROLE_ADMIN

def require_admin():
    """Returns a redirect response if the current session isn't an admin, else None."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_admin():
        return redirect(url_for('dashboard'))
    return None

def render_page(template, **kwargs):
    """
    Prepends the role-aware nav bar to a template and renders it.
    The nav is concatenated as plain Python text (not passed through
    Jinja as a variable), so its <a> tags are never HTML-escaped.
    """
    return render_template_string(render_nav() + template, **kwargs)

def get_used_order_indexes(cursor, company_id, exclude_question_id=None):
    """Returns the set of order_index values currently used by this company's questions."""
    if exclude_question_id:
        cursor.execute("""
            SELECT order_index FROM questions
            WHERE company_id = %s AND id != %s
        """, (company_id, exclude_question_id))
    else:
        cursor.execute("SELECT order_index FROM questions WHERE company_id = %s", (company_id,))
    return {row[0] for row in cursor.fetchall()}

def resolve_order_index_conflict(cursor, company_id, desired_index, exclude_question_id=None):
    """
    Ensures `desired_index` (1-3) is completely free for this company. 
    If any other questions hold that index, they are systematically bumped 
    to genuinely free slots until no conflicts remain.
    """
    desired_index = max(1, min(3, int(desired_index)))

    while True:
        if exclude_question_id:
            cursor.execute("""
                SELECT id FROM questions
                WHERE company_id = %s AND order_index = %s AND id != %s
                LIMIT 1
            """, (company_id, desired_index, exclude_question_id))
        else:
            cursor.execute("""
                SELECT id FROM questions
                WHERE company_id = %s AND order_index = %s
                LIMIT 1
            """, (company_id, desired_index))

        conflicting = cursor.fetchone()
        
        if not conflicting:
            break
        conflicting_id = conflicting[0]
        
        with cursor.connection.cursor() as fresh_cursor:
            used = get_used_order_indexes(fresh_cursor, company_id, exclude_question_id=exclude_question_id)
        
        free_index = next((i for i in (1, 2, 3) if i not in used), None)
        
        if free_index is None:
            free_index = next((i for i in (1, 2, 3) if i != desired_index), 2)

        with cursor.connection.cursor() as update_cursor:
            update_cursor.execute("""
                UPDATE questions 
                SET order_index = %s, updated_at = NOW()
                WHERE id = %s
            """, (free_index, conflicting_id))

    return desired_index

# ROUTES

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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM companies ORDER BY name ASC")
    company_list = cursor.fetchall()

    cursor.execute("SELECT id, company_id, name FROM departments ORDER BY name ASC")
    all_departments = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM employees WHERE role = %s", (ROLE_ADMIN,))
    no_admin_yet = cursor.fetchone()[0] == 0

    cursor.close()
    conn.close()

    departments_by_company = {}
    for dept_id, comp_id, dept_name in all_departments:
        departments_by_company.setdefault(str(comp_id), []).append(
            {"id": str(dept_id), "name": dept_name}
        )

    return render_template_string(HTML_SIGNUP,
                                  companies=company_list,
                                  departments_by_company_json=json.dumps(departments_by_company),
                                  no_admin_yet=no_admin_yet,
                                  error_message=None)

def render_signup_with_error(error_message):
    """Helper to re-render the signup page (with company/department data) on validation errors."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM companies ORDER BY name ASC")
    company_list = cursor.fetchall()
    cursor.execute("SELECT id, company_id, name FROM departments ORDER BY name ASC")
    all_departments = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM employees WHERE role = %s", (ROLE_ADMIN,))
    no_admin_yet = cursor.fetchone()[0] == 0
    cursor.close()
    conn.close()

    departments_by_company = {}
    for dept_id, comp_id, dept_name in all_departments:
        departments_by_company.setdefault(str(comp_id), []).append(
            {"id": str(dept_id), "name": dept_name}
        )

    return render_template_string(HTML_SIGNUP,
                                  companies=company_list,
                                  departments_by_company_json=json.dumps(departments_by_company),
                                  no_admin_yet=no_admin_yet,
                                  error_message=error_message)

@app.route('/save_user', methods=['POST'])
def save_user():
    user_name         = request.form['name']
    user_email        = request.form['email']
    raw_password      = request.form['password']
    confirm_password  = request.form.get('confirm_password', '')
    comp_id           = request.form['company_id']
    dept_id           = request.form['department_id']
    wants_admin       = request.form.get('register_as_admin') == 'yes'

    if raw_password != confirm_password:
        return render_signup_with_error('Passwords do not match. Please try again.')

    if not comp_id:
        return render_signup_with_error('Please select a company.')

    encoded_password = generate_password_hash(raw_password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dept_id = resolve_department_id(cursor, comp_id, dept_id)
        role = ROLE_EMPLOYEE
        if wants_admin:
            cursor.execute("SELECT COUNT(*) FROM employees WHERE role = %s", (ROLE_ADMIN,))
            if cursor.fetchone()[0] == 0:
                role = ROLE_ADMIN

        cursor.execute(
            "INSERT INTO employees (company_id, department_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (comp_id, dept_id, user_name, user_email, encoded_password, role)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return render_signup_with_error(f'Database Error: {e}')
    finally:
        cursor.close()
        conn.close()
    return "Success! Account created. <a href='/login'>Go to Login</a>"

@app.route('/process_login', methods=['POST'])
def process_login():
    email_input    = request.form['email']
    password_input = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, password_hash, role FROM employees WHERE email = %s", (email_input,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user[2], password_input):
        session['user_id']   = str(user[0])
        session['user_name'] = user[1]
        session['user_role'] = user[3]
        return redirect(url_for('dashboard'))
    return render_template_string(HTML_LOGIN, error_message='Invalid email or password.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# EMPLOYEE ROUTES

def get_user_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, c.name, d.name, e.name, e.email,
               e.language_preference, e.status, e.created_at,
               e.company_id, e.department_id
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = %s
    """, (user_id,))
    info = cursor.fetchone()
    cursor.close()
    conn.close()
    return info

def get_my_submissions(user_id):
    """
    Returns this employee's past feedback answers, joined with question text,
    most recent first. Includes submission_id so each row can link to
    /my_feedback/<submission_id>/edit.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fs.date_submitted, fs.id AS submission_id, q.question_text_en, fa.answer_text
        FROM feedback_submissions fs
        JOIN feedback_answers fa ON fa.submission_id = fs.id
        JOIN questions q ON q.id = fa.question_id
        WHERE fs.employee_id = %s
        ORDER BY fs.date_submitted DESC, fs.created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_info = get_user_info(session['user_id'])
    if not user_info:
        return redirect(url_for('logout'))

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)
    my_submissions = get_my_submissions(session['user_id'])

    return render_page(HTML_DASHBOARD,
                                  user_name=session['user_name'],
                                  user_info=user_info,
                                  my_submissions=my_submissions,
                                  flash_error=flash_error,
                                  flash_success=flash_success)

@app.route('/edit_profile')
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_info = get_user_info(session['user_id'])
    if not user_info:
        return redirect(url_for('logout'))
    return render_page(HTML_EDIT_PROFILE, user_info=user_info,
                                  error_message=None, success_message=None)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id             = session['user_id']
    name                = request.form['name']
    email               = request.form['email']
    language_preference = request.form.get('language_preference')
    status              = request.form['status']
    company_id          = request.form['company_id']
    department_id       = request.form['department_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        department_id = resolve_department_id(cursor, company_id, department_id)

        cursor.execute("""
            UPDATE employees
            SET name=%s, email=%s, language_preference=%s, status=%s,
                company_id=%s, department_id=%s
            WHERE id=%s
        """, (name, email, language_preference, status, company_id, department_id, user_id))
        conn.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        conn.rollback()
        user_info = get_user_info(user_id)
        return render_page(HTML_EDIT_PROFILE, user_info=user_info,
                                      error_message=f"Error: {e}", success_message=None)
    finally:
        cursor.close()
        conn.close()

@app.route('/feedbacks')
def feedbacks():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            fs.date_submitted,
            CASE WHEN fs.is_anonymous THEN 'Anonymous' ELSE e.name END,
            d.name,
            s.overall_sentiment,
            STRING_AGG(DISTINCT t.topic_label, ', ')
        FROM feedback_submissions fs
        LEFT JOIN employees e ON fs.employee_id = e.id
        LEFT JOIN departments d ON fs.department_id = d.id
        LEFT JOIN feedback_sentiment s ON fs.id = s.submission_id
        LEFT JOIN feedback_topics t ON fs.id = t.submission_id
        GROUP BY fs.id, fs.date_submitted, fs.is_anonymous, e.name, d.name, s.overall_sentiment
        ORDER BY fs.date_submitted DESC
    """)
    feedback_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_page(HTML_FEEDBACKS, feedbacks=feedback_data)

# SUBMIT FEEDBACK ROUTES

@app.route('/submit_feedback', methods=['GET'])
def submit_feedback_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_info = get_user_info(user_id)
    if not user_info:
        return redirect(url_for('logout'))

    company_id    = user_info[8]
    department_id = user_info[9]
    company_name    = user_info[1] or 'N/A'
    department_name = user_info[2] or 'N/A'

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM feedback_submissions
        WHERE employee_id = %s AND date_submitted = CURRENT_DATE
    """, (user_id,))
    already_submitted = cursor.fetchone() is not None

    cursor.execute("""
        SELECT DISTINCT q.id, q.question_text_en, q.order_index
        FROM questions q
        JOIN question_departments qd ON qd.question_id = q.id
        WHERE q.company_id = %s AND qd.department_id = %s AND q.is_active = TRUE
        ORDER BY q.order_index ASC
    """, (company_id, department_id))
    question_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_page(HTML_SUBMIT_FEEDBACK,
                                  company_name=company_name,
                                  department_name=department_name,
                                  questions=question_list,
                                  already_submitted=already_submitted,
                                  error_message=None)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback_save():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_info = get_user_info(user_id)
    if not user_info:
        return redirect(url_for('logout'))

    company_id    = user_info[8]
    department_id = user_info[9]

    question_count = int(request.form.get('question_count', 0))
    answers = []
    for i in range(1, question_count + 1):
        q_id = request.form.get(f'question_id_{i}')
        ans  = request.form.get(f'answer_{i}', '').strip()
        if not q_id or not ans:
            session['flash_error'] = 'All questions must be answered.'
            return redirect(url_for('submit_feedback_page'))
        answers.append((q_id, ans))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id FROM feedback_submissions
            WHERE employee_id = %s AND date_submitted = CURRENT_DATE
        """, (user_id,))
        if cursor.fetchone():
            session['flash_error'] = 'You have already submitted feedback today.'
            return redirect(url_for('dashboard'))

        cursor.execute("""
            INSERT INTO feedback_submissions (company_id, department_id, employee_id, date_submitted, is_anonymous)
            VALUES (%s, %s, %s, CURRENT_DATE, FALSE)
            RETURNING id
        """, (company_id, department_id, user_id))
        submission_id = cursor.fetchone()[0]

        for q_id, ans in answers:
            cursor.execute("""
                INSERT INTO feedback_answers (submission_id, question_id, answer_text)
                VALUES (%s, %s, %s)
            """, (submission_id, q_id, ans))

        conn.commit()
        session['flash_success'] = 'Thank you! Your feedback has been submitted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error submitting feedback: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

# EDIT MY FEEDBACK ROUTES (own submissions only)

@app.route('/my_feedback/<submission_id>/edit')
def my_feedback_edit(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    flash_error = session.pop('flash_error', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date_submitted, employee_id
        FROM feedback_submissions
        WHERE id = %s AND employee_id = %s
    """, (submission_id, user_id))
    submission = cursor.fetchone()

    if not submission:
        cursor.close()
        conn.close()
        session['flash_error'] = 'Feedback not found or you do not have permission to edit it.'
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT fa.id, q.question_text_en, fa.answer_text
        FROM feedback_answers fa
        JOIN questions q ON q.id = fa.question_id
        WHERE fa.submission_id = %s
        ORDER BY q.order_index ASC
    """, (submission_id,))
    answers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_page(HTML_EDIT_MY_FEEDBACK,
                       submission=submission,
                       answers=answers,
                       error_message=flash_error)

@app.route('/my_feedback/<submission_id>/update', methods=['POST'])
def my_feedback_update(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Re-verify ownership before writing anything — this is the
        # authoritative check, not just the one on the edit page.
        cursor.execute("""
            SELECT id FROM feedback_submissions
            WHERE id = %s AND employee_id = %s
        """, (submission_id, user_id))
        if not cursor.fetchone():
            session['flash_error'] = 'Feedback not found or you do not have permission to edit it.'
            return redirect(url_for('dashboard'))

        answer_count = int(request.form.get('answer_count', 0))
        for i in range(1, answer_count + 1):
            answer_id   = request.form.get(f'answer_id_{i}')
            answer_text = request.form.get(f'answer_text_{i}', '').strip()
            if not answer_id or not answer_text:
                continue
            # Extra guard: only update answers that actually belong to
            # this submission (which we already confirmed belongs to this user).
            cursor.execute("""
                UPDATE feedback_answers
                SET answer_text = %s, updated_at = NOW()
                WHERE id = %s AND submission_id = %s
            """, (answer_text, answer_id, submission_id))

        conn.commit()
        session['flash_success'] = 'Your feedback has been updated.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error updating feedback: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

# COMPANY ROUTES

@app.route('/companies')
def companies():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, industry, status, created_at, updated_at
        FROM companies ORDER BY created_at DESC
    """)
    company_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_page(HTML_COMPANIES,
                                  companies=company_list,
                                  flash_error=flash_error,
                                  flash_success=flash_success)

@app.route('/companies/create', methods=['POST'])
def company_create():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    name     = request.form.get('name', '').strip()
    industry = request.form.get('industry', '').strip() or None
    status   = request.form.get('status', 'active')

    if not name:
        session['flash_error'] = 'Company name is required.'
        return redirect(url_for('companies'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO companies (name, industry, status) VALUES (%s, %s, %s) RETURNING id",
            (name, industry, status)
        )
        new_company_id = cursor.fetchone()[0]

        get_or_create_default_department(cursor, new_company_id)

        conn.commit()
        session['flash_success'] = f'Company "{name}" created successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('companies'))

@app.route('/companies/<company_id>/update', methods=['POST'])
def company_update(company_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    name     = request.form.get('name', '').strip()
    industry = request.form.get('industry', '').strip() or None
    status   = request.form.get('status', 'active')
    referrer = request.referrer or ''
    back_to_detail = f'/companies/{company_id}' in referrer and referrer.rstrip('/') != f'http://127.0.0.1:5000/companies'

    if not name:
        session['flash_error'] = 'Company name is required.'
        target = url_for('company_detail', company_id=company_id) if back_to_detail else url_for('companies')
        return redirect(target)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE companies SET name=%s, industry=%s, status=%s, updated_at=NOW()
            WHERE id=%s
        """, (name, industry, status, company_id))
        conn.commit()
        session['flash_success'] = 'Company updated successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()

    if back_to_detail:
        return redirect(url_for('company_detail', company_id=company_id))
    return redirect(url_for('companies'))

@app.route('/companies/<company_id>/delete', methods=['POST'])
def company_delete(company_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM companies WHERE id=%s", (company_id,))
        conn.commit()
        session['flash_success'] = 'Company deleted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('companies'))

@app.route('/companies/<company_id>')
def company_detail(company_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, industry, status, created_at, updated_at
        FROM companies WHERE id=%s
    """, (company_id,))
    company = cursor.fetchone()

    if not company:
        cursor.close()
        conn.close()
        session['flash_error'] = 'Company not found.'
        return redirect(url_for('companies'))

    cursor.execute("""
        SELECT id, company_id, name, min_display_count, created_at, updated_at,
               NULL, NULL, NULL, id
        FROM departments WHERE company_id=%s ORDER BY name ASC
    """, (company_id,))
    departments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_page(HTML_COMPANY_DETAIL,
                                  company=company,
                                  departments=departments,
                                  flash_error=flash_error,
                                  flash_success=flash_success)

# DEPARTMENT ROUTES

@app.route('/companies/<company_id>/departments/create', methods=['POST'])
def department_create(company_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    name              = request.form.get('name', '').strip()
    min_display_count = request.form.get('min_display_count') or None

    if not name:
        session['flash_error'] = 'Department name is required.'
        return redirect(url_for('company_detail', company_id=company_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO departments (company_id, name, min_display_count)
            VALUES (%s, %s, %s)
        """, (company_id, name, min_display_count))
        conn.commit()
        session['flash_success'] = f'Department "{name}" created.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('company_detail', company_id=company_id))

@app.route('/departments/<dept_id>/update', methods=['POST'])
def department_update(dept_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    company_id        = request.form.get('company_id')
    name              = request.form.get('name', '').strip()
    min_display_count = request.form.get('min_display_count') or None

    if not name:
        session['flash_error'] = 'Department name is required.'
        return redirect(url_for('company_detail', company_id=company_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE departments SET name=%s, min_display_count=%s, updated_at=NOW()
            WHERE id=%s
        """, (name, min_display_count, dept_id))
        conn.commit()
        session['flash_success'] = 'Department updated.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('company_detail', company_id=company_id))

@app.route('/departments/<dept_id>/delete', methods=['POST'])
def department_delete(dept_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    company_id = request.form.get('company_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM departments WHERE id=%s", (dept_id,))
        row = cursor.fetchone()
        if row and row[0] == DEFAULT_DEPARTMENT_NAME:
            session['flash_error'] = 'The "No Department" entry cannot be deleted.'
            return redirect(url_for('company_detail', company_id=company_id))

        default_id = get_or_create_default_department(cursor, company_id)
        cursor.execute("""
            UPDATE employees SET department_id=%s
            WHERE department_id=%s
        """, (default_id, dept_id))

        cursor.execute("DELETE FROM departments WHERE id=%s", (dept_id,))
        conn.commit()
        session['flash_success'] = 'Department deleted. Any employees in it were moved to "No Department".'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('company_detail', company_id=company_id))

# QUESTIONS ROUTES

@app.route('/questions')
def questions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM companies ORDER BY name ASC")
    company_list = cursor.fetchall()

    cursor.execute("""
        SELECT q.id, q.company_id, q.question_text_en, q.question_text_tr,
               q.order_index, q.is_active, q.created_at, q.updated_at,
               c.name AS company_name,
               STRING_AGG(d.name, ', ' ORDER BY d.name) AS department_names
        FROM questions q
        LEFT JOIN companies c ON q.company_id = c.id
        LEFT JOIN question_departments qd ON qd.question_id = q.id
        LEFT JOIN departments d ON d.id = qd.department_id
        GROUP BY q.id, q.company_id, q.question_text_en, q.question_text_tr,
                 q.order_index, q.is_active, q.created_at, q.updated_at, c.name
        ORDER BY c.name ASC, q.order_index ASC
    """)
    question_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_page(HTML_QUESTIONS,
                                  companies=company_list,
                                  questions=question_list,
                                  flash_error=flash_error,
                                  flash_success=flash_success)

@app.route('/questions/create', methods=['POST'])
def question_create():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    company_id       = request.form.get('company_id')
    question_text_en = request.form.get('question_text_en', '').strip()
    question_text_tr = request.form.get('question_text_tr', '').strip() or None
    order_index       = request.form.get('order_index') or 1

    try:
        order_index = int(order_index)
    except (TypeError, ValueError):
        order_index = 1

    if not company_id or not question_text_en:
        session['flash_error'] = 'Company and English question text are required.'
        return redirect(url_for('questions'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        existing_count = count_company_questions(cursor, company_id)
        if existing_count >= MAX_QUESTIONS_PER_COMPANY:
            session['flash_error'] = (
                f'This company already has {existing_count} questions. '
                f'Maximum allowed is {MAX_QUESTIONS_PER_COMPANY}.'
            )
            return redirect(url_for('questions'))

        order_index = resolve_order_index_conflict(cursor, company_id, order_index)

        cursor.execute("""
            INSERT INTO questions (company_id, question_text_en, question_text_tr, order_index, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (company_id, question_text_en, question_text_tr, order_index))
        conn.commit()
        session['flash_success'] = 'Question created. Assign departments using the Edit page.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('questions'))

@app.route('/questions/<question_id>/edit')
def question_edit(question_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    flash_error = session.pop('flash_error', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, company_id, question_text_en, question_text_tr,
               order_index, is_active, created_at, updated_at
        FROM questions WHERE id = %s
    """, (question_id,))
    question = cursor.fetchone()

    if not question:
        cursor.close()
        conn.close()
        session['flash_error'] = 'Question not found.'
        return redirect(url_for('questions'))

    company_id = question[1]

    cursor.execute("SELECT name FROM companies WHERE id = %s", (company_id,))
    company_row = cursor.fetchone()
    company_name = company_row[0] if company_row else 'Unknown'

    cursor.execute("""
        SELECT id, name FROM departments
        WHERE company_id = %s ORDER BY name ASC
    """, (company_id,))
    departments = cursor.fetchall()

    cursor.execute("""
        SELECT department_id FROM question_departments WHERE question_id = %s
    """, (question_id,))
    assigned_department_ids = [str(row[0]) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_page(HTML_QUESTION_EDIT,
                                  question=question,
                                  company_name=company_name,
                                  departments=departments,
                                  assigned_department_ids=assigned_department_ids,
                                  flash_error=flash_error)

@app.route('/questions/<question_id>/update', methods=['POST'])
def question_update(question_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    question_text_en = request.form.get('question_text_en', '').strip()
    question_text_tr = request.form.get('question_text_tr', '').strip() or None
    order_index       = request.form.get('order_index') or 1
    is_active         = request.form.get('is_active', 'true') == 'true'
    department_ids    = request.form.getlist('department_ids')  

    try:
        order_index = int(order_index)
    except (TypeError, ValueError):
        order_index = 1

    if not question_text_en:
        session['flash_error'] = 'English question text is required.'
        return redirect(url_for('question_edit', question_id=question_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT company_id FROM questions WHERE id = %s", (question_id,))
        row = cursor.fetchone()
        if not row:
            session['flash_error'] = 'Question not found.'
            return redirect(url_for('questions'))
        company_id = row[0]
        order_index = resolve_order_index_conflict(
            cursor, company_id, order_index, exclude_question_id=question_id
        )

        cursor.execute("""
            UPDATE questions
            SET question_text_en=%s, question_text_tr=%s, order_index=%s,
                is_active=%s, updated_at=NOW()
            WHERE id=%s
        """, (question_text_en, question_text_tr, order_index, is_active, question_id))

        cursor.execute("DELETE FROM question_departments WHERE question_id = %s", (question_id,))
        
        for dept_id in department_ids:
            cursor.execute("""
                INSERT INTO question_departments (question_id, department_id)
                SELECT %s, %s
                WHERE EXISTS (
                    SELECT 1 FROM departments WHERE id = %s AND company_id = %s
                )
                ON CONFLICT (question_id, department_id) DO NOTHING
            """, (question_id, dept_id, dept_id, company_id))

        conn.commit()
        session['flash_success'] = 'Question updated.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('questions'))


@app.route('/questions/<question_id>/delete', methods=['POST'])
def question_delete(question_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
        session['flash_success'] = 'Question deleted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('questions'))

# ADMIN: USER MANAGEMENT ROUTES

def get_companies_and_departments_json():
    """Shared helper: returns (company_list, departments_by_company_json) for dropdowns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM companies ORDER BY name ASC")
    company_list = cursor.fetchall()

    cursor.execute("SELECT id, company_id, name FROM departments ORDER BY name ASC")
    all_departments = cursor.fetchall()
    cursor.close()
    conn.close()

    departments_by_company = {}
    for dept_id, comp_id, dept_name in all_departments:
        departments_by_company.setdefault(str(comp_id), []).append(
            {"id": str(dept_id), "name": dept_name}
        )
    return company_list, json.dumps(departments_by_company)

@app.route('/admin/users', methods=['GET'])
def admin_users():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)

    search_query = request.args.get('q', '').strip()
    sort_by      = request.args.get('sort', 'recent')

    sort_map = {
        'recent':    'e.created_at DESC',
        'oldest':    'e.created_at ASC',
        'name_asc':  'e.name ASC',
        'name_desc': 'e.name DESC',
        'email_asc': 'e.email ASC',
    }
    order_clause = sort_map.get(sort_by, 'e.created_at DESC')

    conn = get_db_connection()
    cursor = conn.cursor()

    base_query = f"""
        SELECT e.id, e.name, e.email, e.role, c.name, d.name, e.status, e.created_at
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE (e.name ILIKE %s OR e.email ILIKE %s)
        ORDER BY {order_clause}
    """
    like_pattern = f"%{search_query}%"
    cursor.execute(base_query, (like_pattern, like_pattern))
    user_list = cursor.fetchall()

    cursor.close()
    conn.close()

    company_list, departments_by_company_json = get_companies_and_departments_json()

    return render_page(HTML_ADMIN_USERS,
                       users=user_list,
                       companies=company_list,
                       departments_by_company_json=departments_by_company_json,
                       search_query=search_query,
                       sort_by=sort_by,
                       flash_error=flash_error,
                       flash_success=flash_success)

@app.route('/admin/users/create', methods=['POST'])
def admin_user_create():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    name       = request.form.get('name', '').strip()
    email      = request.form.get('email', '').strip()
    password   = request.form.get('password', '')
    role       = request.form.get('role', ROLE_EMPLOYEE)
    company_id = request.form.get('company_id')
    dept_id    = request.form.get('department_id')

    if not name or not email or not password or not company_id:
        session['flash_error'] = 'Name, email, password, and company are required.'
        return redirect(url_for('admin_users'))

    if role not in (ROLE_ADMIN, ROLE_EMPLOYEE):
        role = ROLE_EMPLOYEE

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dept_id = resolve_department_id(cursor, company_id, dept_id)
        password_hash = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO employees (company_id, department_id, name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (company_id, dept_id, name, email, password_hash, role))
        conn.commit()
        session['flash_success'] = f'User "{name}" created successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error creating user: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<user_id>/edit')
def admin_user_edit(user_id):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    flash_error = session.pop('flash_error', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, role, company_id, department_id, status, created_at, company_id, department_id
        FROM employees WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        session['flash_error'] = 'User not found.'
        return redirect(url_for('admin_users'))

    company_id = user[8]
    cursor.execute("""
        SELECT id, name FROM departments WHERE company_id = %s ORDER BY name ASC
    """, (company_id,))
    current_company_departments = cursor.fetchall()

    cursor.close()
    conn.close()

    company_list, departments_by_company_json = get_companies_and_departments_json()

    return render_page(HTML_ADMIN_USER_EDIT,
                       user=user,
                       companies=company_list,
                       current_company_departments=current_company_departments,
                       departments_by_company_json=departments_by_company_json,
                       error_message=flash_error)

@app.route('/admin/users/<user_id>/update', methods=['POST'])
def admin_user_update(user_id):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    name        = request.form.get('name', '').strip()
    email       = request.form.get('email', '').strip()
    new_password = request.form.get('password', '')
    role        = request.form.get('role', ROLE_EMPLOYEE)
    status      = request.form.get('status', 'active')
    company_id  = request.form.get('company_id')
    department_id = request.form.get('department_id')

    if role not in (ROLE_ADMIN, ROLE_EMPLOYEE):
        role = ROLE_EMPLOYEE

    if not name or not email or not company_id:
        session['flash_error'] = 'Name, email, and company are required.'
        return redirect(url_for('admin_user_edit', user_id=user_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        department_id = resolve_department_id(cursor, company_id, department_id)

        if new_password:
            password_hash = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE employees
                SET name=%s, email=%s, role=%s, status=%s,
                    company_id=%s, department_id=%s, password_hash=%s, updated_at=NOW()
                WHERE id=%s
            """, (name, email, role, status, company_id, department_id, password_hash, user_id))
        else:
            cursor.execute("""
                UPDATE employees
                SET name=%s, email=%s, role=%s, status=%s,
                    company_id=%s, department_id=%s, updated_at=NOW()
                WHERE id=%s
            """, (name, email, role, status, company_id, department_id, user_id))

        conn.commit()
        session['flash_success'] = f'User "{name}" updated successfully.'

        # If the admin edited their own account, keep the session in sync
        if user_id == session.get('user_id'):
            session['user_name'] = name
            session['user_role'] = role
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error updating user: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<user_id>/delete', methods=['POST'])
def admin_user_delete(user_id):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    if user_id == session.get('user_id'):
        session['flash_error'] = 'You cannot delete your own account while logged in.'
        return redirect(url_for('admin_users'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM employees WHERE id = %s", (user_id,))
        conn.commit()
        session['flash_success'] = 'User deleted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error deleting user: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

# ANALYTICS ROUTE

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM feedback_submissions")
    total_submissions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM departments")
    total_departments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]

    stats = {
        'total_submissions': total_submissions,
        'total_employees': total_employees,
        'total_departments': total_departments,
        'total_companies': total_companies,
    }

    cursor.execute("""
        SELECT overall_sentiment, COUNT(*)
        FROM feedback_sentiment
        GROUP BY overall_sentiment
    """)
    sentiment_rows = cursor.fetchall()
    sentiment_json = json.dumps({
        "labels": [row[0] or "Unknown" for row in sentiment_rows] or ["No Data"],
        "values": [row[1] for row in sentiment_rows] or [0],
    })

    cursor.execute("""
        SELECT d.name, COUNT(fs.id)
        FROM feedback_submissions fs
        LEFT JOIN departments d ON fs.department_id = d.id
        GROUP BY d.name
        ORDER BY COUNT(fs.id) DESC
    """)
    dept_volume_rows = cursor.fetchall()
    dept_volume_json = json.dumps({
        "labels": [row[0] or "Unknown" for row in dept_volume_rows],
        "values": [row[1] for row in dept_volume_rows],
    })

    cursor.execute("""
        SELECT c.name, COUNT(e.id)
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        GROUP BY c.name
        ORDER BY COUNT(e.id) DESC
    """)
    emp_company_rows = cursor.fetchall()
    employees_by_company_json = json.dumps({
        "labels": [row[0] or "Unknown" for row in emp_company_rows],
        "values": [row[1] for row in emp_company_rows],
    })

    cursor.execute("""
        SELECT c.name, COUNT(d.id)
        FROM departments d
        LEFT JOIN companies c ON d.company_id = c.id
        GROUP BY c.name
        ORDER BY COUNT(d.id) DESC
    """)
    dept_company_rows = cursor.fetchall()
    dept_count_by_company_json = json.dumps({
        "labels": [row[0] or "Unknown" for row in dept_company_rows],
        "values": [row[1] for row in dept_company_rows],
    })

    cursor.execute("""
        SELECT date_submitted, COUNT(*)
        FROM feedback_submissions
        GROUP BY date_submitted
        ORDER BY date_submitted ASC
    """)
    timeline_rows = cursor.fetchall()
    submissions_over_time_json = json.dumps({
        "labels": [row[0].strftime('%d %b %Y') if row[0] else 'Unknown' for row in timeline_rows],
        "values": [row[1] for row in timeline_rows],
    })

    cursor.execute("SELECT LENGTH(answer_text) FROM feedback_answers")
    lengths = [row[0] for row in cursor.fetchall() if row[0] is not None]

    buckets = [0, 0, 0, 0, 0]
    for length in lengths:
        if length <= 20:
            buckets[0] += 1
        elif length <= 50:
            buckets[1] += 1
        elif length <= 100:
            buckets[2] += 1
        elif length <= 200:
            buckets[3] += 1
        else:
            buckets[4] += 1

    answer_length_histogram_json = json.dumps({
        "labels": ["0-20 chars", "21-50 chars", "51-100 chars", "101-200 chars", "200+ chars"],
        "values": buckets,
    })

    cursor.close()
    conn.close()

    return render_page(HTML_ANALYTICS,
                       stats=stats,
                       sentiment_json=sentiment_json,
                       dept_volume_json=dept_volume_json,
                       employees_by_company_json=employees_by_company_json,
                       dept_count_by_company_json=dept_count_by_company_json,
                       submissions_over_time_json=submissions_over_time_json,
                       answer_length_histogram_json=answer_length_histogram_json)

if __name__ == '__main__':
    ensure_question_department_table()
    ensure_role_column()
    app.run(port=5000, debug=True)