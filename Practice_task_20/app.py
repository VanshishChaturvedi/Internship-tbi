import json
import csv
import io
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, session, redirect, url_for, render_template_string, Response
from flask_babel import Babel, gettext as _, ngettext

app = Flask(__name__)
app.secret_key = "super_secret_development_key"

app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = {
    'en': 'English',
    'fr': 'Français',
}

def get_locale():
    """
    Locale resolution order:
      1. An explicit override just set this request (?lang=xx), stored in session.
      2. The logged-in user's saved language_preference — employees read it
         from `employees.language_preference`; admins have no such column,
         so admins fall back to session/default only.
      3. Flask's best-effort match against the browser's Accept-Language header.
      4. BABEL_DEFAULT_LOCALE ('en').
    """
    if 'locale_override' in session:
        return session['locale_override']

    if 'user_id' in session and session.get('user_type') != 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT language_preference FROM employees WHERE id = %s",
                (session['user_id'],)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
        finally:
            cursor.close()
            conn.close()

    return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'

babel = Babel(app, locale_selector=get_locale)

def render_nav():
    """
    Builds the nav bar HTML. Admin-only links (User Management, Feedback
    Management, Department Management, Company Management, Questions
    Management, Content Translation Management) only appear when the
    logged-in user's role is admin.

    Static labels are wrapped in _() (Flask-Babel's gettext) so
    `pybabel extract` picks them up as translatable strings. The <a> tags
    themselves are still built as plain Python strings (not passed through
    Jinja as a template variable) to avoid the auto-escaping issue from
    earlier in this project — _() runs first and returns a plain str,
    which is then safely embedded the same way as before.
    """
    links = [f'<a href="/dashboard">{_("Dashboard")}</a>']

    if is_admin():
        links += [
            f'<a href="/admin/users">{_("User Management")}</a>',
            f'<a href="/admin/reports">{_("Reports")}</a>',
            f'<a href="/admin/translations">{_("Content Translation Management")}</a>',
            f'<a href="/feedbacks">{_("Feedback Management")}</a>',
            f'<a href="/companies">{_("Company Management")}</a>',
            f'<a href="/companies">{_("Department Management")}</a>',
            f'<a href="/questions">{_("Questions Management")}</a>',
            f'<a href="/analytics">{_("Analytics")}</a>',
        ]
    else:
        links += [
            f'<a href="/companies">{_("Companies")}</a>',
            f'<a href="/questions">{_("Questions")}</a>',
            f'<a href="/feedbacks">{_("Feedbacks")}</a>',
            f'<a href="/analytics">{_("Analytics")}</a>',
        ]

    links.append(f'<a href="/logout">{_("Logout")}</a>')

    nav_html = "<p>\n  " + "\n  | ".join(links) + "\n</p>\n"
    nav_html += render_language_dropdown()
    nav_html += "<hr>\n"
    return nav_html

def render_language_dropdown():
    """
    Renders the language selector shown in the header on every page.
    Submitting it POSTs to /set_language, which updates session (always)
    and employees.language_preference (only for employee sessions — admins
    have no language_preference column) before reloading the current page.
    """
    current_locale = get_locale()
    options_html = ""
    for code, label in app.config['LANGUAGES'].items():
        selected = "selected" if code == current_locale else ""
        options_html += f'<option value="{code}" {selected}>{label}</option>\n'

    return f"""
    <form action="/set_language" method="POST" style="display:inline;">
        <input type="hidden" name="next" value="{request.path}">
        {_("Language")}:
        <select name="lang" onchange="this.form.submit()">
            {options_html}
        </select>
        <noscript><button type="submit">{_("Go")}</button></noscript>
    </form>
    """

# Login

HTML_LOGIN = """
<h2>{{ _('Employee Login') }}</h2>
<form action="/process_login" method="POST">
    {{ _('Email') }}: <input type="email" name="email" required><br><br>
    {{ _('Password') }}: <input type="password" name="password" required><br><br>
    <button type="submit">{{ _('Login') }}</button>
</form>
<p>{{ _("Don't have an account?") }} <a href="/signup">{{ _('Sign up here') }}</a></p>
{% if error_message %}
<p style="color:red;">{{ error_message }}</p>
{% endif %}
"""

# Signup

HTML_SIGNUP = """
<h2>{{ _('Employee Signup') }}</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}
<form action="/save_user" method="POST">
    {{ _('Name') }}: <input type="text" name="name" required><br><br>
    {{ _('Email') }}: <input type="email" name="email" required><br><br>
    {{ _('Password') }}: <input type="password" name="password" required minlength="6"><br><br>
    {{ _('Re-enter Password') }}: <input type="password" name="confirm_password" required minlength="6"><br><br>

    {{ _('Company') }}:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        <option value="">{{ _('-- Select Company --') }}</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>

    {{ _('Department') }}:
    <select name="department_id" id="departmentSelect" required disabled>
        <option value="">{{ _('-- Select Company First --') }}</option>
    </select><br><br>

    <button type="submit">{{ _('Submit to Database') }}</button>
</form>
<p>{{ _('Already registered?') }} <a href="/login">{{ _('Go to Login') }}</a></p>

{% if no_admin_yet %}
<hr>
<h2>{{ _('Register First Admin Account') }}</h2>
<p style="color:blue;">
    {{ _('No admin account exists yet in the system. This form is only shown because admin_users is currently empty — it disappears permanently once the first admin is created.') }}
</p>
{% if admin_error_message %}<p style="color:red;">{{ admin_error_message }}</p>{% endif %}
<form action="/save_admin" method="POST">
    {{ _('Name') }}: <input type="text" name="admin_name" required><br><br>
    {{ _('Email') }}: <input type="email" name="admin_email" required><br><br>
    {{ _('Password') }}: <input type="password" name="admin_password" required minlength="6"><br><br>
    {{ _('Re-enter Password') }}: <input type="password" name="admin_confirm_password" required minlength="6"><br><br>
    {{ _('Company (optional)') }}:
    <select name="admin_company_id">
        <option value="">{{ _('-- None --') }}</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    <button type="submit">{{ _('Register as First Admin (Superadmin)') }}</button>
</form>
{% endif %}

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
<h2>{{ _('Welcome to your Dashboard,') }} {{ user_name }}!</h2>
<h3>{{ _('Your Information:') }}</h3>
<ul>
    <li><strong>{{ _('Employee ID:') }}</strong> {{ user_info[0] }}</li>
    <li><strong>{{ _('Company:') }}</strong> {{ user_info[1] if user_info[1] else _('N/A') }}</li>
    <li><strong>{{ _('Department:') }}</strong> {{ user_info[2] if user_info[2] else _('N/A') }}</li>
    <li><strong>{{ _('Name:') }}</strong> {{ user_info[3] }}</li>
    <li><strong>{{ _('Email:') }}</strong> {{ user_info[4] }}</li>
    <li><strong>{{ _('Language Preference:') }}</strong> {{ user_info[5] if user_info[5] else _('Not Set') }}</li>
    <li><strong>{{ _('Status:') }}</strong> {{ user_info[6] }}</li>
    <li><strong>{{ _('Account Created:') }}</strong> {{ user_info[7] }}</li>
</ul>
<br>

{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}
{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}

<a href="/submit_feedback"><button>{{ _('Submit Feedback') }}</button></a>
<a href="/feedbacks"><button>{{ _('View All Feedback') }}</button></a>
<a href="/edit_profile"><button>{{ _('Edit Profile') }}</button></a>

<hr>
<h3>{{ _('Your Past Submissions') }}</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Date Submitted') }}</th>
        <th>{{ _('Question') }}</th>
        <th>{{ _('Your Answer') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for row in my_submissions %}
    <tr>
        <td>{{ row[0] }}</td>
        <td>
            {% if current_locale == 'fr' and row[3] %}
                {{ row[3] }}
            {% else %}
                {{ row[2] }}
            {% endif %}
        </td>
        <td>{{ row[4] }}</td>
        <td><a href="/my_feedback/{{ row[1] }}/edit"><button>{{ _('Edit') }}</button></a></td>
    </tr>
    {% else %}
    <tr><td colspan="4">{{ _("You haven't submitted any feedback yet.") }}</td></tr>
    {% endfor %}
</table>
"""

HTML_ADMIN_DASHBOARD = """
<h2>{{ _('Welcome,') }} {{ admin_name }}!</h2>
<h3>{{ _('Your Admin Account:') }}</h3>
<ul>
    <li><strong>{{ _('Admin ID:') }}</strong> {{ admin_info[0] }}</li>
    <li><strong>{{ _('Name:') }}</strong> {{ admin_info[1] }}</li>
    <li><strong>{{ _('Email:') }}</strong> {{ admin_info[2] }}</li>
    <li><strong>{{ _('Admin Role:') }}</strong> {{ admin_info[3] }}</li>
    <li><strong>{{ _('Company:') }}</strong> {{ admin_info[4] if admin_info[4] else _('Not scoped to a company') }}</li>
    <li><strong>{{ _('Account Created:') }}</strong> {{ admin_info[5] }}</li>
</ul>
<br>

{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}
{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
"""

# Edit Profile

HTML_EDIT_PROFILE = """
<h2>{{ _('Edit Your Profile') }}</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}
{% if success_message %}<p style="color:green;">{{ success_message }}</p>{% endif %}
<form action="/update_profile" method="POST">
    <input type="hidden" name="user_id" value="{{ user_info[0] }}">
    {{ _('Name') }}: <input type="text" name="name" value="{{ user_info[3] }}" required><br><br>
    {{ _('Email') }}: <input type="email" name="email" value="{{ user_info[4] }}" required><br><br>
    {{ _('Language Preference') }}:
    <select name="language_preference">
      <option value="en" {{ 'selected' if user_info[5]=='en' }}>{{ _('English') }}</option>
      <option value="fr" {{ 'selected' if user_info[5]=='fr' }}>{{ _('French') }}</option>
    </select><br><br>
    {{ _('Status') }}:
    <select name="status">
      <option value="active"   {{ 'selected' if user_info[6]=='active' }}>{{ _('Active') }}</option>
      <option value="inactive" {{ 'selected' if user_info[6]=='inactive' }}>{{ _('Inactive') }}</option>
    </select><br><br>
    {{ _('Company ID') }}: <input type="text" name="company_id" value="{{ user_info[8] if user_info[8] else '' }}" required><br><br>
    {{ _('Department ID') }}: <input type="text" name="department_id" value="{{ user_info[9] if user_info[9] else '' }}"><br><br>
    <button type="submit">{{ _('Update Profile') }}</button>
</form>
<br>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>
"""

# Feedback

HTML_FEEDBACKS = """
<h2>{{ _('Company Feedback Listing') }}</h2>

__FILTER_UI__

<a href="__EXPORT_URL__"><button>{{ _('Export to CSV') }}</button></a>
<br><br>

<table border="1" cellpadding="10" style="border-collapse: collapse;">
    <tr>
        <th>{{ _('Date Submitted') }}</th>
        <th>{{ _('Employee Name') }}</th>
        <th>{{ _('Department') }}</th>
        <th>{{ _('Overall Sentiment') }}</th>
        <th>{{ _('Topic') }}</th>
    </tr>
    {% for row in feedbacks %}
    <tr>
        <td>{{ row[0] }}</td>
        <td>{{ row[1] }}</td>
        <td>{{ row[2] if row[2] else _('N/A') }}</td>
        <td>{{ row[3] if row[3] else _('Pending AI Analysis') }}</td>
        <td>{{ row[4] if row[4] else _('Pending AI Analysis') }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5">{{ _('No feedback found.') }}</td></tr>
    {% endfor %}
</table>
<br>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>
"""

# Companies list

HTML_COMPANIES = """
<h2>{{ _('Companies') }}</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>{{ _('Create New Company') }}</h3>
<form action="/companies/create" method="POST">
    {{ _('Name') }}: <input type="text" name="name" required><br><br>
    {{ _('Industry') }}: <input type="text" name="industry"><br><br>
    {{ _('Status') }}:
    <select name="status">
      <option value="active">{{ _('Active') }}</option>
      <option value="inactive">{{ _('Inactive') }}</option>
    </select><br><br>
    <button type="submit">{{ _('Create Company') }}</button>
</form>

<hr>
<h3>{{ _('Search Companies') }}</h3>
<input type="text" id="searchInput" placeholder="{{ _('Type to search by name...') }}" oninput="filterTable()"><br><br>

__FILTER_UI__

<a href="__EXPORT_URL__"><button>{{ _('Export to CSV') }}</button></a>
<br><br>

<h3>{{ _('All Companies') }}</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Name') }}</th>
        <th>{{ _('Industry') }}</th>
        <th>{{ _('Status') }}</th>
        <th>{{ _('Created') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for c in companies %}
    <tr class="company-row">
        <td class="company-name">{{ c[1] }}</td>
        <td>{{ c[2] if c[2] else '—' }}</td>
        <td>{{ c[3] }}</td>
        <td>{{ c[4].strftime('%d %b %Y') if c[4] else '—' }}</td>
        <td>
            <a href="/companies/{{ c[0] }}"><button>{{ _('View') }}</button></a>

            <form action="/companies/{{ c[0] }}/update" method="POST" style="display:inline;">
                <input type="text" name="name" value="{{ c[1] }}" required>
                <input type="text" name="industry" value="{{ c[2] if c[2] else '' }}">
                <select name="status">
                  <option value="active"   {{ 'selected' if c[3]=='active' }}>{{ _('Active') }}</option>
                  <option value="inactive" {{ 'selected' if c[3]=='inactive' }}>{{ _('Inactive') }}</option>
                </select>
                <button type="submit">{{ _('Update') }}</button>
            </form>

            <form action="/companies/{{ c[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete {{ c[1] }}?')">
                <button type="submit">{{ _('Delete') }}</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5">{{ _('No companies found.') }}</td></tr>
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
<a href="/companies"><button>&larr; {{ _('Back to Companies') }}</button></a>
<br><br>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h2>{{ _('Company Details') }}</h2>
<ul>
    <li><strong>{{ _('ID:') }}</strong> {{ company[0] }}</li>
    <li><strong>{{ _('Name:') }}</strong> {{ company[1] }}</li>
    <li><strong>{{ _('Industry:') }}</strong> {{ company[2] if company[2] else _('Not specified') }}</li>
    <li><strong>{{ _('Status:') }}</strong> {{ company[3] }}</li>
    <li><strong>{{ _('Created:') }}</strong> {{ company[4].strftime('%d %b %Y') if company[4] else '—' }}</li>
    <li><strong>{{ _('Updated:') }}</strong> {{ company[5].strftime('%d %b %Y') if company[5] else '—' }}</li>
</ul>

<h3>{{ _('Edit Company') }}</h3>
<form action="/companies/{{ company[0] }}/update" method="POST">
    {{ _('Name') }}: <input type="text" name="name" value="{{ company[1] }}" required><br><br>
    {{ _('Industry') }}: <input type="text" name="industry" value="{{ company[2] if company[2] else '' }}"><br><br>
    {{ _('Status') }}:
    <select name="status">
      <option value="active"   {{ 'selected' if company[3]=='active' }}>{{ _('Active') }}</option>
      <option value="inactive" {{ 'selected' if company[3]=='inactive' }}>{{ _('Inactive') }}</option>
    </select><br><br>
    <button type="submit">{{ _('Save Changes') }}</button>
</form>

<hr>
<h2>{{ _('Departments') }} ({{ departments|length }})</h2>

__FILTER_UI__

<a href="__EXPORT_URL__"><button>{{ _('Export to CSV') }}</button></a>
<br><br>

<h3>{{ _('Add Department') }}</h3>
<form action="/companies/{{ company[0] }}/departments/create" method="POST">
    {{ _('Name') }}: <input type="text" name="name" required><br><br>
    {{ _('Min Display Count') }}: <input type="number" name="min_display_count" min="1"><br><br>
    <button type="submit">{{ _('Add Department') }}</button>
</form>

<br>
<table border="2" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Name') }}</th>
        <th>{{ _('Department ID') }}</th>
        <th>{{ _('Min Display Count') }}</th>
        <th>{{ _('Created') }}</th>
        <th>{{ _('Actions') }}</th>
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
                <button type="submit">{{ _('Update') }}</button>
            </form>

            {% if d[2] != 'No Department' %}
            <form action="/departments/{{ d[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete department {{ d[2] }}?')">
                <input type="hidden" name="company_id" value="{{ company[0] }}">
                <button type="submit">{{ _('Delete') }}</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5">{{ _('No departments yet.') }}</td></tr>
    {% endfor %}
</table>
"""

# Questions

HTML_QUESTIONS = """
<h2>{{ _('Questions') }}</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>{{ _('Create New Question') }}</h3>
<form action="/questions/create" method="POST">
    {{ _('Company') }}:
    <select name="company_id" required>
        <option value="">{{ _('-- Select Company --') }}</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>

    {{ _('Question Text (English)') }}: <input type="text" name="question_text_en" required style="width:300px;"><br><br>
    {{ _('Question Text (French)') }}: <input type="text" name="question_text_fr" style="width:300px;"><br><br>
    {{ _('Order Index') }}: <input type="number" name="order_index" min="1" max="3" value="1"><br><br>

    <p>{{ _('Note: a company can have a maximum of 3 questions. If the index you pick is already used by another question, that question will automatically move to the remaining free index. Departments can be assigned after creation using the Edit page.') }}</p>
    <button type="submit">{{ _('Create Question') }}</button>
</form>

<hr>
<h3>{{ _('All Questions') }}</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Company') }}</th>
        <th>{{ _('Question (EN)') }}</th>
        <th>{{ _('Question (FR)') }}</th>
        <th>{{ _('Order') }}</th>
        <th>{{ _('Departments') }}</th>
        <th>{{ _('Active') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for q in questions %}
    <tr>
        <td>{{ q[8] }}</td>
        <td>{{ q[2] }}</td>
        <td>{{ q[3] if q[3] else '—' }}</td>
        <td>{{ q[4] }}</td>
        <td>{{ q[9] if q[9] else _('No departments assigned') }}</td>
        <td>{{ _('Yes') if q[5] else _('No') }}</td>
        <td>
            <a href="/questions/{{ q[0] }}/edit"><button>{{ _('Edit') }}</button></a>
            <form action="/questions/{{ q[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete this question?')">
                <button type="submit">{{ _('Delete') }}</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="7">{{ _('No questions found.') }}</td></tr>
    {% endfor %}
</table>
"""

# Edit Question page

HTML_QUESTION_EDIT = """
<a href="/questions"><button>&larr; {{ _('Back to Questions') }}</button></a>
<br><br>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}

<h2>{{ _('Edit Question') }}</h2>
<form action="/questions/{{ question[0] }}/update" method="POST">
    <p><strong>{{ _('Company:') }}</strong> {{ company_name }}</p>

    {{ _('Question Text (English)') }}:
    <input type="text" name="question_text_en" value="{{ question[2] }}" required style="width:300px;"><br><br>

    {{ _('Question Text (French)') }}:
    <input type="text" name="question_text_fr" value="{{ question[3] if question[3] else '' }}" style="width:300px;"><br><br>

    {{ _('Order Index') }}: <input type="number" name="order_index" min="1" max="3" value="{{ question[4] }}" oninput="if(parseInt(this.value) > 3) this.value = 3; if(parseInt(this.value) < 1) this.value = 1;">><br><br>

    {{ _('Active') }}:
    <select name="is_active">
        <option value="true"  {{ 'selected' if question[5] }}>{{ _('Yes') }}</option>
        <option value="false" {{ 'selected' if not question[5] }}>{{ _('No') }}</option>
    </select><br><br>

    <p><strong>{{ _('Departments') }}</strong> {{ _('(this question applies to):') }}</p>
    {% if departments %}
   
    <label style="font-weight: normal; cursor: pointer;">
        <input type="checkbox" id="select-all-toggle"> {{ _('All Departments') }}
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
    <p>{{ _('This company has no departments yet.') }}</p>
    {% endfor %}
    <br>

    <button type="submit">{{ _('Save Changes') }}</button>
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

HTML_ADMIN_TRANSLATIONS = """
<h2>{{ _('Content Translation Management') }}</h2>
<p>{{ _('Edit the English and French text for each question side-by-side. Changes save per-question.') }}</p>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%;">
    <tr>
        <th>{{ _('Company') }}</th>
        <th>{{ _('English') }}</th>
        <th>{{ _('French') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for q in questions %}
    <form action="/admin/translations/{{ q[0] }}/update" method="POST" id="form-{{ q[0] }}"></form>
    <tr>
        <td>{{ q[3] }}</td>
        <td>
            <textarea name="question_text_en" rows="2" cols="40" required form="form-{{ q[0] }}">{{ q[1] }}</textarea>
        </td>
        <td>
            <textarea name="question_text_fr" rows="2" cols="40" placeholder="{{ _('French translation...') }}" form="form-{{ q[0] }}">{{ q[2] if q[2] else '' }}</textarea>
        </td>
        <td>
            <button type="submit" form="form-{{ q[0] }}">{{ _('Save') }}</button>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="4">{{ _('No questions found. Create questions from the Questions Management page first.') }}</td></tr>
    {% endfor %}
</table>

<br>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>
"""

# Submit Feedback page

HTML_SUBMIT_FEEDBACK = """
<a href="/dashboard"><button>&larr; {{ _('Back to Dashboard') }}</button></a>
<br><br>

<h2>{{ _("Submit Today's Feedback") }}</h2>
<p><strong>{{ _('Company:') }}</strong> {{ company_name }} &nbsp;|&nbsp; <strong>{{ _('Department:') }}</strong> {{ department_name }}</p>

{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

{% if already_submitted %}
<p style="color:green;">{{ _('You have already submitted feedback today. Come back tomorrow!') }}</p>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>

{% elif not questions %}
<p>{{ _('There are no questions assigned to your department yet. Please check back later.') }}</p>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>

{% else %}
<form action="/submit_feedback" method="POST">
    {% for q in questions %}
    <div style="margin-bottom:20px;">
        <label><strong>
            {{ loop.index }}.
            {% if current_locale == 'fr' and q[2] %}
                {{ q[2] }}
            {% else %}
                {{ q[1] }}
            {% endif %}
        </strong></label><br>
        <input type="hidden" name="question_id_{{ loop.index }}" value="{{ q[0] }}">
        <textarea name="answer_{{ loop.index }}" rows="3" cols="60" required></textarea>
    </div>
    {% endfor %}
    <input type="hidden" name="question_count" value="{{ questions|length }}">
    <button type="submit">{{ _('Submit Feedback') }}</button>
</form>
{% endif %}
"""

# Analytics Dashboard

HTML_ANALYTICS = """
<h2>{{ _('Analytics Dashboard') }}</h2>
<p>{{ _('Visual overview of feedback, employees, and department activity.') }}</p>

<div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:24px;">
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Feedback Submissions') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_submissions }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Employees') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_employees }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Departments') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_departments }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Companies') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_companies }}</span>
    </div>
</div>

<table border="0" cellspacing="0" cellpadding="0" style="width:100%;">
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Feedback Sentiment Breakdown') }}</h3>
    <canvas id="sentimentPieChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Feedback Volume by Department') }}</h3>
    <canvas id="deptBarChart" height="260"></canvas>
  </td>
</tr>
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Employees per Company') }}</h3>
    <canvas id="employeesPieChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Departments per Company') }}</h3>
    <canvas id="deptCountBarChart" height="260"></canvas>
  </td>
</tr>
<tr>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Feedback Submissions Over Time') }}</h3>
    <canvas id="submissionsLineChart" height="260"></canvas>
  </td>
  <td style="width:50%; vertical-align:top; padding:10px;">
    <h3>{{ _('Distribution of Answer Lengths (Histogram)') }}</h3>
    <canvas id="answerLengthHistogram" height="260"></canvas>
  </td>
</tr>
</table>

<br>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>

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
            backgroundColor: '#2196f3'
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
            backgroundColor: '#ff9800'
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
            borderColor: '#673ab7',
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
            backgroundColor: '#009688'
        }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
});
</script>
"""

# Edit My Feedback (own submissions only)

HTML_EDIT_MY_FEEDBACK = """
<a href="/dashboard"><button>&larr; {{ _('Back to Dashboard') }}</button></a>
<br><br>

<h2>{{ _('Edit Your Feedback') }}</h2>
<p><strong>{{ _('Date Submitted:') }}</strong> {{ submission[1] }}</p>

{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

<form action="/my_feedback/{{ submission[0] }}/update" method="POST">
    {% for a in answers %}
<div style="margin-bottom:20px;">
<label><strong>
{{ loop.index }}.
{% if current_locale == 'fr' and a[2] %}
{{ a[2] }}
{% else %}
{{ a[1] }}
{% endif %}
</strong></label><br>
<input type="hidden" name="answer_id_{{ loop.index }}" value="{{ a[0] }}">
<textarea name="answer_text_{{ loop.index }}" rows="3" cols="60" required>{{ a[3] }}</textarea>
</div>
{% endfor %}
    <input type="hidden" name="answer_count" value="{{ answers|length }}">
    <button type="submit">{{ _('Save Changes') }}</button>
</form>
"""

# Admin: User Management

HTML_ADMIN_USERS = """
<h2>{{ _('User Management') }}</h2>

{% if flash_error %}<p style="color:red;">{{ flash_error }}</p>{% endif %}
{% if flash_success %}<p style="color:green;">{{ flash_success }}</p>{% endif %}

<h3>{{ _('Create New Employee') }}</h3>
<form action="/admin/users/create" method="POST">
    {{ _('Name') }}: <input type="text" name="name" required><br><br>
    {{ _('Email') }}: <input type="email" name="email" required><br><br>
    {{ _('Password') }}: <input type="password" name="password" required minlength="6"><br><br>
    {{ _('Company') }}:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        <option value="">{{ _('-- Select Company --') }}</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    {{ _('Department') }}:
    <select name="department_id" id="departmentSelect" required disabled>
        <option value="">{{ _('-- Select Company First --') }}</option>
    </select><br><br>
    <button type="submit">{{ _('Create Employee') }}</button>
</form>

<hr>
<h3>{{ _('Create New Admin') }}</h3>
<form action="/admin/admins/create" method="POST">
    {{ _('Name') }}: <input type="text" name="admin_name" required><br><br>
    {{ _('Email') }}: <input type="email" name="admin_email" required><br><br>
    {{ _('Password') }}: <input type="password" name="admin_password" required minlength="6"><br><br>
    {{ _('Admin Role') }}:
    <select name="admin_role">
      <option value="admin">{{ _('Admin') }}</option>
      <option value="superadmin">{{ _('Superadmin') }}</option>
    </select><br><br>
    {{ _('Company (optional)') }}:
    <select name="admin_company_id">
        <option value="">{{ _('-- None --') }}</option>
        {% for c in companies %}
        <option value="{{ c[0] }}">{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    <button type="submit">{{ _('Create Admin') }}</button>
</form>

<hr>
<h3>{{ _('Search & Sort') }}</h3>
<form action="/admin/users" method="GET">
    {{ _('Search (name or email)') }}: <input type="text" name="q" value="{{ search_query }}" placeholder="{{ _('Type to search...') }}"><br><br>
    {{ _('Sort by') }}:
    <select name="sort">
        <option value="recent"   {{ 'selected' if sort_by=='recent' }}>{{ _('Most Recent First') }}</option>
        <option value="oldest"   {{ 'selected' if sort_by=='oldest' }}>{{ _('Oldest First') }}</option>
        <option value="name_asc" {{ 'selected' if sort_by=='name_asc' }}>{{ _('Name (A-Z)') }}</option>
        <option value="name_desc"{{ 'selected' if sort_by=='name_desc' }}>{{ _('Name (Z-A)') }}</option>
        <option value="email_asc"{{ 'selected' if sort_by=='email_asc' }}>{{ _('Email (A-Z)') }}</option>
    </select>
    <button type="submit">{{ _('Apply') }}</button>
    <a href="/admin/users"><button type="button">{{ _('Reset') }}</button></a>
</form>

<hr>
<h3>{{ _('Employees') }} ({{ employees|length }})</h3>
<a href="/export/employees?q={{ search_query }}&sort={{ sort_by }}"><button>{{ _('Export to CSV') }}</button></a>
<br><br>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Name') }}</th>
        <th>{{ _('Email') }}</th>
        <th>{{ _('Company') }}</th>
        <th>{{ _('Department') }}</th>
        <th>{{ _('Status') }}</th>
        <th>{{ _('Created') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for u in employees %}
    <tr>
        <td>{{ u[1] }}</td>
        <td>{{ u[2] }}</td>
        <td>{{ u[3] if u[3] else _('N/A') }}</td>
        <td>{{ u[4] if u[4] else _('N/A') }}</td>
        <td>{{ u[5] }}</td>
        <td>{{ u[6].strftime('%d %b %Y') if u[6] else '—' }}</td>
        <td>
            <a href="/admin/users/{{ u[0] }}/edit"><button>{{ _('Edit') }}</button></a>
            <form action="/admin/users/{{ u[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete employee {{ u[1] }}? This cannot be undone.')">
                <button type="submit">{{ _('Delete') }}</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="7">{{ _('No employees found.') }}</td></tr>
    {% endfor %}
</table>

<hr>
<h3>{{ _('Admins') }} ({{ admins|length }})</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr>
        <th>{{ _('Name') }}</th>
        <th>{{ _('Email') }}</th>
        <th>{{ _('Admin Role') }}</th>
        <th>{{ _('Company') }}</th>
        <th>{{ _('Created') }}</th>
        <th>{{ _('Actions') }}</th>
    </tr>
    {% for a in admins %}
    <tr>
        <td>{{ a[1] }}</td>
        <td>{{ a[2] }}</td>
        <td>{{ a[3] }}</td>
        <td>{{ a[4] if a[4] else _('N/A') }}</td>
        <td>{{ a[5].strftime('%d %b %Y') if a[5] else '—' }}</td>
        <td>
            <form action="/admin/admins/{{ a[0] }}/delete" method="POST" style="display:inline;"
                  onsubmit="return confirm('Delete admin {{ a[1] }}? This cannot be undone.')">
                <button type="submit">{{ _('Delete') }}</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="6">{{ _('No admins found.') }}</td></tr>
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

# Admin: Edit single employee (admins are not edited here — see admin_users page for admin create/delete)

HTML_ADMIN_USER_EDIT = """
<a href="/admin/users"><button>&larr; {{ _('Back to User Management') }}</button></a>
<br><br>

<h2>{{ _('Edit Employee') }}</h2>
{% if error_message %}<p style="color:red;">{{ error_message }}</p>{% endif %}

<form action="/admin/users/{{ user[0] }}/update" method="POST">
    {{ _('Name') }}: <input type="text" name="name" value="{{ user[1] }}" required><br><br>
    {{ _('Email') }}: <input type="email" name="email" value="{{ user[2] }}" required><br><br>
    {{ _('New Password (leave blank to keep current)') }}:
    <input type="password" name="password" minlength="6"><br><br>
    {{ _('Status') }}:
    <select name="status">
      <option value="active"   {{ 'selected' if user[5]=='active' }}>{{ _('Active') }}</option>
      <option value="inactive" {{ 'selected' if user[5]=='inactive' }}>{{ _('Inactive') }}</option>
    </select><br><br>

    {{ _('Company') }}:
    <select name="company_id" id="companySelect" required onchange="loadDepartments()">
        {% for c in companies %}
        <option value="{{ c[0] }}" {{ 'selected' if c[0]|string == user[7]|string }}>{{ c[1] }}</option>
        {% endfor %}
    </select><br><br>
    {{ _('Department') }}:
    <select name="department_id" id="departmentSelect" required>
        {% for d in current_company_departments %}
        <option value="{{ d[0] }}" {{ 'selected' if d[0]|string == user[8]|string }}>{{ d[1] }}</option>
        {% endfor %}
    </select><br><br>

    <button type="submit">{{ _('Save Changes') }}</button>
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

HTML_ADMIN_REPORTS = """
<h2>{{ _('Reports') }}</h2>

__FILTER_UI__

<div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:24px;">
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Employees') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_employees }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Companies') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_companies }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Departments') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_departments }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Feedback Submissions') }}{{ stats.range_label }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_submissions }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Questions') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_questions }}</span>
    </div>
    <div style="border:1px solid #ccc; padding:14px 20px;">
        <strong>{{ _('Total Admins') }}</strong><br>
        <span style="font-size:28px;">{{ stats.total_admins }}</span>
    </div>
</div>

<a href="__EXPORT_URL__"><button>{{ _('Export to CSV') }}</button></a>

<hr>
<h3>{{ _('Feedback Submissions by Company (within selected range)') }}</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr><th>{{ _('Company') }}</th><th>{{ _('Submissions') }}</th></tr>
    {% for row in submissions_by_company %}
    <tr><td>{{ row[0] if row[0] else _('Unknown') }}</td><td>{{ row[1] }}</td></tr>
    {% else %}
    <tr><td colspan="2">{{ _('No submissions in this range.') }}</td></tr>
    {% endfor %}
</table>

<br>
<a href="/dashboard"><button>{{ _('Back to Dashboard') }}</button></a>
"""

# DB CONNECTION

def get_db_connection():
    return psycopg2.connect(
        dbname="employee_feedback",
        user="postgres",
        password="postgres",
        host="localhost"
    )

from datetime import date, timedelta

def resolve_date_range(filter_type, custom_start=None, custom_end=None):
    """
    Returns (start_date, end_date) as date objects, or (None, None) when
    no filtering should be applied ('all' / unrecognized filter_type).
    filter_type: 'last_week', 'last_month', 'custom', or 'all'.
    """
    today = date.today()

    if filter_type == 'last_week':
        return today - timedelta(days=7), today
    elif filter_type == 'last_month':
        return today - timedelta(days=30), today
    elif filter_type == 'custom' and custom_start and custom_end:
        try:
            start = date.fromisoformat(custom_start)
            end = date.fromisoformat(custom_end)
            return start, end
        except ValueError:
            return None, None
    return None, None

def get_filter_params_from_request():
    """Reads filter_type/start_date/end_date from GET args, used identically
    by the page routes and their CSV export counterparts."""
    filter_type  = request.args.get('filter_type', 'all')
    custom_start = request.args.get('start_date', '')
    custom_end   = request.args.get('end_date', '')
    start_date, end_date = resolve_date_range(filter_type, custom_start, custom_end)
    return filter_type, custom_start, custom_end, start_date, end_date

def render_date_filter_block(action_url, filter_type, custom_start, custom_end, extra_hidden_fields=""):
    return f"""
    <form action="{action_url}" method="GET" style="margin-bottom:16px;">
        {extra_hidden_fields}
        {_('Filter by date')}:
        <select name="filter_type" id="filterTypeSelect" onchange="toggleCustomDates()">
            <option value="all"        {"selected" if filter_type == "all" else ""}>{_('All Time')}</option>
            <option value="last_week"  {"selected" if filter_type == "last_week" else ""}>{_('Last Week')}</option>
            <option value="last_month" {"selected" if filter_type == "last_month" else ""}>{_('Last Month')}</option>
            <option value="custom"     {"selected" if filter_type == "custom" else ""}>{_('Custom Range')}</option>
        </select>
        <span id="customDateFields" style="{"display:inline;" if filter_type == "custom" else "display:none;"}">
            {_('Start')}: <input type="date" name="start_date" value="{custom_start}">
            {_('End')}:   <input type="date" name="end_date" value="{custom_end}">
        </span>
        <button type="submit">{_('Apply Filter')}</button>
        <a href="{action_url}"><button type="button">{_('Clear')}</button></a>
    </form>
    <script>
    function toggleCustomDates() {{
        const val = document.getElementById('filterTypeSelect').value;
        document.getElementById('customDateFields').style.display = (val === 'custom') ? 'inline' : 'none';
    }}
    </script>
    """

def build_export_url(base_path, filter_type, custom_start, custom_end, extra_query=""):
    """Builds the CSV export link so it carries the exact same filter as the current view."""
    query = f"filter_type={filter_type}&start_date={custom_start}&end_date={custom_end}"
    if extra_query:
        query += f"&{extra_query}"
    return f"{base_path}?{query}"

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

# ADMIN AUTH HELPERS (corrected to match original schema)

ROLE_SUPERADMIN = 'superadmin'
ROLE_ADMIN      = 'admin'

def ensure_admin_role_enum():
    """
    Ensures the admin_role ENUM type and admin_users table exist, matching
    the original schema. Safe to run repeatedly (checks pg_type first).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'admin_role') THEN
                    CREATE TYPE admin_role AS ENUM ('superadmin', 'admin');
                END IF;
            END$$;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID REFERENCES companies(id),
                name VARCHAR NOT NULL,
                email VARCHAR NOT NULL UNIQUE,
                password_hash VARCHAR NOT NULL,
                role admin_role NOT NULL DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Could not ensure admin_users table: {e}")
    finally:
        cursor.close()
        conn.close()

def is_admin():
    """
    True only when the current session was authenticated against
    admin_users (see process_login). Employee sessions never satisfy this.
    """
    return session.get('user_type') == 'admin'

def require_admin():
    """Returns a redirect response if the current session isn't an admin_users login, else None."""
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
    cursor.execute("SELECT COUNT(*) FROM admin_users")
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
                                  admin_error_message=None,
                                  error_message=None)

def render_signup_with_error(error_message, admin_error_message=None):
    """Helper to re-render the signup page (with company/department data) on validation errors."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM companies ORDER BY name ASC")
    company_list = cursor.fetchall()
    cursor.execute("SELECT id, company_id, name FROM departments ORDER BY name ASC")
    all_departments = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM admin_users")
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
                                  admin_error_message=admin_error_message,
                                  error_message=error_message)

@app.route('/save_user', methods=['POST'])
def save_user():
    """
    Creates a standard EMPLOYEE account (employees table). Admin accounts
    are created via /save_admin (first-admin bootstrap, only while
    admin_users is empty) or via the User Management page thereafter.
    """
    user_name         = request.form['name']
    user_email        = request.form['email']
    raw_password      = request.form['password']
    confirm_password  = request.form.get('confirm_password', '')
    comp_id           = request.form['company_id']
    dept_id           = request.form['department_id']

    if raw_password != confirm_password:
        return render_signup_with_error('Passwords do not match. Please try again.')

    if not comp_id:
        return render_signup_with_error('Please select a company.')

    encoded_password = generate_password_hash(raw_password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dept_id = resolve_department_id(cursor, comp_id, dept_id)

        cursor.execute(
            "INSERT INTO employees (company_id, department_id, name, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (comp_id, dept_id, user_name, user_email, encoded_password)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return render_signup_with_error(f'Database Error: {e}')
    finally:
        cursor.close()
        conn.close()
    return "Success! Account created. <a href='/login'>Go to Login</a>"

@app.route('/save_admin', methods=['POST'])
def save_admin():
    """
    First-admin bootstrap: creates a row in admin_users, but ONLY if
    admin_users is currently empty. Re-checked server-side here — never
    trust that the form was only reachable because no_admin_yet was True
    when the page was rendered, since that could be stale by the time
    this POST arrives (e.g. two people racing to submit the form).
    Once any admin exists, this route always rejects further attempts,
    permanently closing the bootstrap path.
    """
    admin_name        = request.form.get('admin_name', '').strip()
    admin_email       = request.form.get('admin_email', '').strip()
    raw_password      = request.form.get('admin_password', '')
    confirm_password  = request.form.get('admin_confirm_password', '')
    admin_company_id  = request.form.get('admin_company_id') or None

    if raw_password != confirm_password:
        return render_signup_with_error(None, admin_error_message='Passwords do not match. Please try again.')

    if not admin_name or not admin_email or not raw_password:
        return render_signup_with_error(None, admin_error_message='Name, email, and password are required.')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        if cursor.fetchone()[0] > 0:
            return render_signup_with_error(
                None,
                admin_error_message='An admin account already exists. This registration form is now closed.'
            )

        password_hash = generate_password_hash(raw_password)
        cursor.execute("""
            INSERT INTO admin_users (company_id, name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (admin_company_id, admin_name, admin_email, password_hash, ROLE_SUPERADMIN))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return render_signup_with_error(None, admin_error_message=f'Database Error: {e}')
    finally:
        cursor.close()
        conn.close()
    return "Success! Admin account created. <a href='/login'>Go to Login</a>"

@app.route('/process_login', methods=['POST'])
def process_login():
    """
    Dual-login logic per the original schema:
      1. Check admin_users first (dedicated admin table, admin_role ENUM).
      2. If no admin match, fall back to employees (standard user login).
    session['user_type'] distinguishes which table the session belongs to
    ('admin' or 'employee'); is_admin() below relies on this.
    """
    email_input    = request.form['email']
    password_input = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Try admin_users first
    cursor.execute("""
        SELECT id, name, password_hash, role
        FROM admin_users
        WHERE email = %s
    """, (email_input,))
    admin_row = cursor.fetchone()

    if admin_row and check_password_hash(admin_row[2], password_input):
        cursor.close()
        conn.close()
        session['user_id']   = str(admin_row[0])
        session['user_name'] = admin_row[1]
        session['user_type'] = 'admin'
        session['user_role'] = admin_row[3]
        return redirect(url_for('dashboard'))

    # 2. Fall back to employees (standard users)
    cursor.execute("""
        SELECT id, name, password_hash
        FROM employees
        WHERE email = %s
    """, (email_input,))
    employee_row = cursor.fetchone()
    cursor.close()
    conn.close()

    if employee_row and check_password_hash(employee_row[2], password_input):
        session['user_id']   = str(employee_row[0])
        session['user_name'] = employee_row[1]
        session['user_type'] = 'employee'
        session['user_role'] = None
        return redirect(url_for('dashboard'))

    return render_template_string(HTML_LOGIN, error_message='Invalid email or password.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/set_language', methods=['POST'])
def set_language():
    """
    Updates the active UI language. Always stored in session (so it takes
    effect immediately and survives even for admins, who have no
    language_preference column). Additionally persisted to
    employees.language_preference when the current session is a
    standard employee, so their choice is remembered across future logins.
    """
    lang = request.form.get('lang', 'en')
    if lang not in app.config['LANGUAGES']:
        lang = 'en'

    session['locale_override'] = lang

    if 'user_id' in session and session.get('user_type') != 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE employees SET language_preference = %s, updated_at = NOW() WHERE id = %s",
                (lang, session['user_id'])
            )
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    next_page = request.form.get('next') or url_for('dashboard')
    return redirect(next_page)

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

def get_admin_info(admin_id):
    """Admin equivalent of get_user_info — looks up admin_users, not employees."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name, a.email, a.role, c.name, a.created_at, a.company_id
        FROM admin_users a
        LEFT JOIN companies c ON a.company_id = c.id
        WHERE a.id = %s
    """, (admin_id,))
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
    SELECT fs.date_submitted, fs.id AS submission_id, q.question_text_en, q.question_text_fr, fa.answer_text
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

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)
    if session.get('user_type') == 'admin':
        admin_info = get_admin_info(session['user_id'])
        if not admin_info:
            return redirect(url_for('logout'))

        return render_page(HTML_ADMIN_DASHBOARD,
                           admin_name=session['user_name'],
                           admin_info=admin_info,
                           flash_error=flash_error,
                           flash_success=flash_success)

    # Standard employee dashboard
    user_info = get_user_info(session['user_id'])
    if not user_info:
        return redirect(url_for('logout'))

    my_submissions = get_my_submissions(session['user_id'])

    user_info = get_user_info(session['user_id'])
    if not user_info:
        return redirect(url_for('logout'))

    my_submissions = get_my_submissions(session['user_id'])
    current_locale = get_locale()

    return render_page(HTML_DASHBOARD,
    user_name=session['user_name'],
    user_info=user_info,
    my_submissions=my_submissions,
    current_locale=current_locale,
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

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
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
        WHERE 1=1
    """
    params = []
    if start_date and end_date:
        query += " AND fs.date_submitted BETWEEN %s AND %s"
        params += [start_date, end_date]
    query += """
        GROUP BY fs.id, fs.date_submitted, fs.is_anonymous, e.name, d.name, s.overall_sentiment
        ORDER BY fs.date_submitted DESC
    """

    cursor.execute(query, tuple(params))
    feedback_data = cursor.fetchall()
    cursor.close()
    conn.close()

    filter_ui = render_date_filter_block('/feedbacks', filter_type, custom_start, custom_end)
    export_url = build_export_url('/export/feedbacks', filter_type, custom_start, custom_end)
    template = HTML_FEEDBACKS.replace('__FILTER_UI__', filter_ui).replace('__EXPORT_URL__', export_url)

    return render_page(template, feedbacks=feedback_data)

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
        SELECT DISTINCT q.id, q.question_text_en, q.question_text_fr, q.order_index
        FROM questions q
        JOIN question_departments qd ON qd.question_id = q.id
        WHERE q.company_id = %s AND qd.department_id = %s AND q.is_active = TRUE
        ORDER BY q.order_index ASC
    """, (company_id, department_id))
    question_list = cursor.fetchall()

    cursor.close()
    conn.close()

    current_locale = get_locale()

    return render_page(HTML_SUBMIT_FEEDBACK,
                                  company_name=company_name,
                                  department_name=department_name,
                                  questions=question_list,
                                  already_submitted=already_submitted,
                                  current_locale=current_locale,
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
        SELECT fa.id, q.question_text_en, q.question_text_fr, fa.answer_text
        FROM feedback_answers fa
        JOIN questions q ON q.id = fa.question_id
        WHERE fa.submission_id = %s
        ORDER BY q.order_index ASC
    """, (submission_id,))
    answers = cursor.fetchall()

    cursor.close()
    conn.close()

    current_locale = get_locale()

    return render_page(HTML_EDIT_MY_FEEDBACK,
    submission=submission,
    answers=answers,
    current_locale=current_locale,
    error_message=flash_error)

@app.route('/my_feedback/<submission_id>/update', methods=['POST'])
def my_feedback_update(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()

    if start_date and end_date:
        cursor.execute("""
            SELECT id, name, industry, status, created_at, updated_at
            FROM companies
            WHERE created_at::date BETWEEN %s AND %s
            ORDER BY created_at DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, name, industry, status, created_at, updated_at
            FROM companies ORDER BY created_at DESC
        """)
    company_list = cursor.fetchall()
    cursor.close()
    conn.close()

    filter_ui = render_date_filter_block('/companies', filter_type, custom_start, custom_end)
    export_url = build_export_url('/export/companies', filter_type, custom_start, custom_end)
    template = HTML_COMPANIES.replace('__FILTER_UI__', filter_ui).replace('__EXPORT_URL__', export_url)

    return render_page(template,
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

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

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

    if start_date and end_date:
        cursor.execute("""
            SELECT id, company_id, name, min_display_count, created_at, updated_at,
                   NULL, NULL, NULL, id
            FROM departments
            WHERE company_id=%s AND created_at::date BETWEEN %s AND %s
            ORDER BY name ASC
        """, (company_id, start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, company_id, name, min_display_count, created_at, updated_at,
                   NULL, NULL, NULL, id
            FROM departments WHERE company_id=%s ORDER BY name ASC
        """, (company_id,))
    departments = cursor.fetchall()

    cursor.close()
    conn.close()

    filter_ui = render_date_filter_block(f'/companies/{company_id}', filter_type, custom_start, custom_end)
    export_url = build_export_url('/export/departments', filter_type, custom_start, custom_end,
                                  extra_query=f'company_id={company_id}')
    template = HTML_COMPANY_DETAIL.replace('__FILTER_UI__', filter_ui).replace('__EXPORT_URL__', export_url)

    return render_page(template,
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
        SELECT q.id, q.company_id, q.question_text_en, q.question_text_fr,
               q.order_index, q.is_active, q.created_at, q.updated_at,
               c.name AS company_name,
               STRING_AGG(d.name, ', ' ORDER BY d.name) AS department_names
        FROM questions q
        LEFT JOIN companies c ON q.company_id = c.id
        LEFT JOIN question_departments qd ON qd.question_id = q.id
        LEFT JOIN departments d ON d.id = qd.department_id
        GROUP BY q.id, q.company_id, q.question_text_en, q.question_text_fr,
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
    question_text_fr = request.form.get('question_text_fr', '').strip() or None
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
            INSERT INTO questions (company_id, question_text_en, question_text_fr, order_index, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (company_id, question_text_en, question_text_fr, order_index))
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
        SELECT id, company_id, question_text_en, question_text_fr,
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
    question_text_fr = request.form.get('question_text_fr', '').strip() or None
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
            SET question_text_en=%s, question_text_fr=%s, order_index=%s,
                is_active=%s, updated_at=NOW()
            WHERE id=%s
        """, (question_text_en, question_text_fr, order_index, is_active, question_id))

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

    sort_map_employees = {
        'recent':    'e.created_at DESC',
        'oldest':    'e.created_at ASC',
        'name_asc':  'e.name ASC',
        'name_desc': 'e.name DESC',
        'email_asc': 'e.email ASC',
    }
    sort_map_admins = {
        'recent':    'a.created_at DESC',
        'oldest':    'a.created_at ASC',
        'name_asc':  'a.name ASC',
        'name_desc': 'a.name DESC',
        'email_asc': 'a.email ASC',
    }
    employee_order = sort_map_employees.get(sort_by, 'e.created_at DESC')
    admin_order     = sort_map_admins.get(sort_by, 'a.created_at DESC')

    conn = get_db_connection()
    cursor = conn.cursor()

    like_pattern = f"%{search_query}%"

    # Standard users come from `employees` (no role column — corrected per schema)
    cursor.execute(f"""
        SELECT e.id, e.name, e.email, c.name, d.name, e.status, e.created_at
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE (e.name ILIKE %s OR e.email ILIKE %s)
        ORDER BY {employee_order}
    """, (like_pattern, like_pattern))
    employee_list = cursor.fetchall()

    # Admins come from the dedicated `admin_users` table with admin_role ENUM
    cursor.execute(f"""
        SELECT a.id, a.name, a.email, a.role, c.name, a.created_at
        FROM admin_users a
        LEFT JOIN companies c ON a.company_id = c.id
        WHERE (a.name ILIKE %s OR a.email ILIKE %s)
        ORDER BY {admin_order}
    """, (like_pattern, like_pattern))
    admin_list = cursor.fetchall()

    cursor.close()
    conn.close()

    company_list, departments_by_company_json = get_companies_and_departments_json()

    return render_page(HTML_ADMIN_USERS,
                       employees=employee_list,
                       admins=admin_list,
                       companies=company_list,
                       departments_by_company_json=departments_by_company_json,
                       search_query=search_query,
                       sort_by=sort_by,
                       flash_error=flash_error,
                       flash_success=flash_success)

@app.route('/admin/users/create', methods=['POST'])
def admin_user_create():
    """Creates a standard EMPLOYEE (employees table). For admin accounts, use /admin/admins/create."""
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    name       = request.form.get('name', '').strip()
    email      = request.form.get('email', '').strip()
    password   = request.form.get('password', '')
    company_id = request.form.get('company_id')
    dept_id    = request.form.get('department_id')

    if not name or not email or not password or not company_id:
        session['flash_error'] = 'Name, email, password, and company are required.'
        return redirect(url_for('admin_users'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dept_id = resolve_department_id(cursor, company_id, dept_id)
        password_hash = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO employees (company_id, department_id, name, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
        """, (company_id, dept_id, name, email, password_hash))
        conn.commit()
        session['flash_success'] = f'Employee "{name}" created successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error creating employee: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/admins/create', methods=['POST'])
def admin_admin_create():
    """Creates an admin account directly in admin_users, per the original schema."""
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    name       = request.form.get('admin_name', '').strip()
    email      = request.form.get('admin_email', '').strip()
    password   = request.form.get('admin_password', '')
    admin_role_value = request.form.get('admin_role', ROLE_ADMIN)
    company_id = request.form.get('admin_company_id') or None

    if admin_role_value not in (ROLE_SUPERADMIN, ROLE_ADMIN):
        admin_role_value = ROLE_ADMIN

    if not name or not email or not password:
        session['flash_error'] = 'Name, email, and password are required for admin accounts.'
        return redirect(url_for('admin_users'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO admin_users (company_id, name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (company_id, name, email, password_hash, admin_role_value))
        conn.commit()
        session['flash_success'] = f'Admin "{name}" created successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error creating admin: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<user_id>/edit')
def admin_user_edit(user_id):
    """Edits a standard employee. Admin editing uses /admin/admins/<id>/edit instead."""
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    flash_error = session.pop('flash_error', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, company_id, department_id, status, created_at, company_id, department_id
        FROM employees WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        session['flash_error'] = 'Employee not found.'
        return redirect(url_for('admin_users'))

    company_id = user[7]
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
    status      = request.form.get('status', 'active')
    company_id  = request.form.get('company_id')
    department_id = request.form.get('department_id')

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
                SET name=%s, email=%s, status=%s,
                    company_id=%s, department_id=%s, password_hash=%s, updated_at=NOW()
                WHERE id=%s
            """, (name, email, status, company_id, department_id, password_hash, user_id))
        else:
            cursor.execute("""
                UPDATE employees
                SET name=%s, email=%s, status=%s,
                    company_id=%s, department_id=%s, updated_at=NOW()
                WHERE id=%s
            """, (name, email, status, company_id, department_id, user_id))

        conn.commit()
        session['flash_success'] = f'Employee "{name}" updated successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error updating employee: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<user_id>/delete', methods=['POST'])
def admin_user_delete(user_id):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM employees WHERE id = %s", (user_id,))
        conn.commit()
        session['flash_success'] = 'Employee deleted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error deleting employee: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/admins/<admin_id>/delete', methods=['POST'])
def admin_admin_delete(admin_id):
    """Deletes an admin_users row. An admin cannot delete their own account while logged in."""
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    if admin_id == session.get('user_id'):
        session['flash_error'] = 'You cannot delete your own admin account while logged in.'
        return redirect(url_for('admin_users'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM admin_users WHERE id = %s", (admin_id,))
        conn.commit()
        session['flash_success'] = 'Admin deleted.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error deleting admin: {e}'
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

    # Top summary numbers
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

    # 1. PIE — Sentiment breakdown across all feedback_sentiment rows
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

    # 2. BAR — Feedback submission volume grouped by department
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

    # 3. PIE — Employee headcount per company
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

    # 4. BAR — Department count per company
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

    # 5. LINE — Feedback submissions over time (daily counts)
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

    # 6. HISTOGRAM — Distribution of answer text lengths, bucketed into
    cursor.execute("SELECT LENGTH(answer_text) FROM feedback_answers")
    lengths = [row[0] for row in cursor.fetchall() if row[0] is not None]

    buckets = [0, 0, 0, 0, 0]  # 0-20, 21-50, 51-100, 101-200, 200+
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

# ADMIN REPORTS ROUTE (Task 2 + Task 3 date filtering)

@app.route('/admin/reports')
def admin_reports():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM departments")
    total_departments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM admin_users")
    total_admins = cursor.fetchone()[0]

    # Feedback submissions COUNT — respects the active date filter (Task 3)
    if start_date and end_date:
        cursor.execute("""
            SELECT COUNT(*) FROM feedback_submissions
            WHERE date_submitted BETWEEN %s AND %s
        """, (start_date, end_date))
        range_label = f" ({start_date} {_('to')} {end_date})"
    else:
        cursor.execute("SELECT COUNT(*) FROM feedback_submissions")
        range_label = f" ({_('All Time')})"
    total_submissions = cursor.fetchone()[0]

    # Per-company breakdown, same date filter applied
    if start_date and end_date:
        cursor.execute("""
            SELECT c.name, COUNT(fs.id)
            FROM feedback_submissions fs
            LEFT JOIN companies c ON fs.company_id = c.id
            WHERE fs.date_submitted BETWEEN %s AND %s
            GROUP BY c.name
            ORDER BY COUNT(fs.id) DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT c.name, COUNT(fs.id)
            FROM feedback_submissions fs
            LEFT JOIN companies c ON fs.company_id = c.id
            GROUP BY c.name
            ORDER BY COUNT(fs.id) DESC
        """)
    submissions_by_company = cursor.fetchall()

    cursor.close()
    conn.close()

    stats = {
        'total_employees': total_employees,
        'total_companies': total_companies,
        'total_departments': total_departments,
        'total_questions': total_questions,
        'total_admins': total_admins,
        'total_submissions': total_submissions,
        'range_label': range_label,
    }

    filter_ui = render_date_filter_block('/admin/reports', filter_type, custom_start, custom_end)
    export_url = build_export_url('/export/reports', filter_type, custom_start, custom_end)

    template = HTML_ADMIN_REPORTS.replace('__FILTER_UI__', filter_ui).replace('__EXPORT_URL__', export_url)

    return render_page(template,
                       stats=stats,
                       submissions_by_company=submissions_by_company)

# CSV EXPORT ROUTES (Task 4)

def send_csv(filename, header_row, data_rows):
    """Builds an in-memory CSV using Python's csv module and returns it as a download."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header_row)
    writer.writerows(data_rows)

    response = Response(buffer.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/export/reports')
def export_reports():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()

    if start_date and end_date:
        cursor.execute("""
            SELECT c.name, COUNT(fs.id)
            FROM feedback_submissions fs
            LEFT JOIN companies c ON fs.company_id = c.id
            WHERE fs.date_submitted BETWEEN %s AND %s
            GROUP BY c.name
            ORDER BY COUNT(fs.id) DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT c.name, COUNT(fs.id)
            FROM feedback_submissions fs
            LEFT JOIN companies c ON fs.company_id = c.id
            GROUP BY c.name
            ORDER BY COUNT(fs.id) DESC
        """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return send_csv('reports_export.csv',
                    ['Company', 'Feedback Submissions'],
                    [(r[0] or 'Unknown', r[1]) for r in rows])

@app.route('/export/companies')
def export_companies():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT name, industry, status, created_at, updated_at
            FROM companies
            WHERE created_at::date BETWEEN %s AND %s
            ORDER BY created_at DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT name, industry, status, created_at, updated_at
            FROM companies ORDER BY created_at DESC
        """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return send_csv('companies_export.csv',
                    ['Name', 'Industry', 'Status', 'Created At', 'Updated At'],
                    rows)

@app.route('/export/departments')
def export_departments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()
    company_id = request.args.get('company_id')  # optional: scope to one company, like the detail page does

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT d.name, c.name, d.min_display_count, d.created_at
        FROM departments d
        LEFT JOIN companies c ON d.company_id = c.id
        WHERE 1=1
    """
    params = []
    if company_id:
        query += " AND d.company_id = %s"
        params.append(company_id)
    if start_date and end_date:
        query += " AND d.created_at::date BETWEEN %s AND %s"
        params += [start_date, end_date]
    query += " ORDER BY d.created_at DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return send_csv('departments_export.csv',
                    ['Department Name', 'Company', 'Min Display Count', 'Created At'],
                    rows)

@app.route('/export/feedbacks')
def export_feedbacks():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    filter_type, custom_start, custom_end, start_date, end_date = get_filter_params_from_request()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
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
        WHERE 1=1
    """
    params = []
    if start_date and end_date:
        query += " AND fs.date_submitted BETWEEN %s AND %s"
        params += [start_date, end_date]
    query += """
        GROUP BY fs.id, fs.date_submitted, fs.is_anonymous, e.name, d.name, s.overall_sentiment
        ORDER BY fs.date_submitted DESC
    """

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    formatted_rows = [
        (r[0], r[1], r[2] or 'N/A', r[3] or 'Pending', r[4] or 'Pending')
        for r in rows
    ]

    return send_csv('feedbacks_export.csv',
                    ['Date Submitted', 'Employee', 'Department', 'Sentiment', 'Topics'],
                    formatted_rows)

# CONTENT TRANSLATION MANAGEMENT ROUTES (Task 4)

@app.route('/admin/translations')
def admin_translations():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    flash_error   = session.pop('flash_error',   None)
    flash_success = session.pop('flash_success', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.id, q.question_text_en, q.question_text_fr, c.name
        FROM questions q
        LEFT JOIN companies c ON q.company_id = c.id
        ORDER BY c.name ASC, q.order_index ASC
    """)
    question_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_page(HTML_ADMIN_TRANSLATIONS,
                       questions=question_list,
                       flash_error=flash_error,
                       flash_success=flash_success)

@app.route('/admin/translations/<question_id>/update', methods=['POST'])
def admin_translation_update(question_id):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    question_text_en = request.form.get('question_text_en', '').strip()
    question_text_fr = request.form.get('question_text_fr', '').strip() or None

    if not question_text_en:
        session['flash_error'] = 'English text is required.'
        return redirect(url_for('admin_translations'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE questions
            SET question_text_en = %s, question_text_fr = %s, updated_at = NOW()
            WHERE id = %s
        """, (question_text_en, question_text_fr, question_id))
        conn.commit()
        session['flash_success'] = 'Translation updated successfully.'
    except Exception as e:
        conn.rollback()
        session['flash_error'] = f'Error updating translation: {e}'
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_translations'))

@app.route('/export/employees')
def export_employees():
    """
    Was linked from the User Management page's 'Export to CSV' button but
    the route itself was missing — added here. Mirrors the same search/sort
    params as /admin/users so the export matches whatever the admin is
    currently viewing.
    """
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    search_query = request.args.get('q', '').strip()
    sort_by      = request.args.get('sort', 'recent')
    sort_map_employees = {
        'recent':    'e.created_at DESC',
        'oldest':    'e.created_at ASC',
        'name_asc':  'e.name ASC',
        'name_desc': 'e.name DESC',
        'email_asc': 'e.email ASC',
    }
    employee_order = sort_map_employees.get(sort_by, 'e.created_at DESC')
    like_pattern = f"%{search_query}%"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT e.name, e.email, c.name, d.name, e.status, e.created_at
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE (e.name ILIKE %s OR e.email ILIKE %s)
        ORDER BY {employee_order}
    """, (like_pattern, like_pattern))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    formatted_rows = [
        (r[0], r[1], r[2] or 'N/A', r[3] or 'N/A', r[4], r[5])
        for r in rows
    ]

    return send_csv('employees_export.csv',
                    ['Name', 'Email', 'Company', 'Department', 'Status', 'Created At'],
                    formatted_rows)

if __name__ == '__main__':
    ensure_question_department_table()
    ensure_admin_role_enum()
    app.run(port=5000, debug=True)