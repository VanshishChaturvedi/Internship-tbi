import psycopg2
from werkzeug.security import generate_password_hash
from flask import Flask, request

app = Flask(__name__)

# Here are some Dummy IDs for Signing UP.

# dummy company_id 1 = 11111111-1111-1111-1111-111111111111
# dummy department_id 1 for company 1= 11111111-1111-1111-0001-111111111111
# dummy department_id 2 for company 1= 11111111-1111-1111-0002-111111111111

# dummy company_id 2 = 22222222-2222-2222-2222-222222222222
# dummy department_id 1 for company 2= 22222222-2222-2222-0001-222222222222
# dummy department_id 2 for company 2= 22222222-2222-2222-0002-222222222222

HTML_FORM = """
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

@app.route('/')
def show_page():
    return HTML_FORM

@app.route('/save_user', methods=['POST'])
def save_user():

    user_name = request.form['name']
    user_email = request.form['email']
    raw_password = request.form['password']
    comp_id = request.form['company_id']
    dept_id = request.form['department_id']
    encoded_password = generate_password_hash(raw_password)


    conn = psycopg2.connect(
    dbname="employee_feedback",
    user="postgres",
    password="postgres",
    host="localhost"
    )
    cursor = conn.cursor()

    cursor.execute(
    "INSERT INTO employees (company_id, department_id, name, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
    (comp_id, dept_id, user_name, user_email, encoded_password)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return f"Success! {user_name} was saved to the database with a secure encoded password."

if __name__ == '__main__':
    app.run(port=5000, debug=True)
