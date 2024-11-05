from flask import Flask, request, render_template, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',
    'database': 'dreem_house'
}

# Database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Route to display the login form
@app.route('/')
def home_page():
    return render_template('front.html')

@app.route('/log')
def login_form():
    return render_template('index.html')

# Route to handle login form submission
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query to fetch user details
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            # Store the house owner's user_id in the session
            if user['user_type'] == 'houseOwner':
                session['user_id'] = user['user_id']  # Store the house owner's user_id
            else:
                session['user_id'] = user['id']  # Store the contractor's id

            session['username'] = user['username']
            session['user_type'] = user['user_type']
            
            # Redirect based on user type
            if user['user_type'] == 'contractor':
                return redirect(url_for('contractor_dashboard'))
            elif user['user_type'] == 'houseOwner':
                return redirect(url_for('houseowner_dashboard'))
        else:
            return "Invalid credentials. Please try again."

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login_form'))  # Redirect to the login page


# Route to display the contractor sign-up form
@app.route('/signup/contractor')
def contractor_signup_form():
    return render_template('contractor_signup.html')

# Route to handle contractor sign-up form submission
@app.route('/signup/contractor', methods=['POST'])
def contractor_signup():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirmPassword']

    if password != confirm_password:
        return "Passwords do not match. Please try again."

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        user_sql = "INSERT INTO users (username, password, user_type) VALUES (%s, %s, %s)"
        user_values = (username, password, 'contractor')
        cursor.execute(user_sql, user_values)
        user_id = cursor.lastrowid

        name = request.form['name']
        company_name = request.form['companyName']
        experience = request.form['experience']
        approval_no = request.form['approvalNo']
        company_address = request.form['companyAddress']
        milestone_project = request.form['milestoneProject']
        mobile = request.form['mobile']
        email= request.form['email']

        contractor_sql = """
        INSERT INTO contractors (user_id, name, company_name, experience, approval_no, company_address, milestone_project, mobile,email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)
        """
        contractor_values = (user_id, name, company_name, experience, approval_no, company_address, milestone_project, mobile,email)
        cursor.execute(contractor_sql, contractor_values)

        conn.commit()

        return "Sign-up successful!"

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

# Route to display the house owner sign-up form
@app.route('/signup/houseowner')
def houseowner_signup_form():
    return render_template('houseowner_signup.html')

@app.route('/location')
def location_page():
    return render_template('location.html')

#@app.route('/project_details')
#def project_details_page():
    #return render_template('project-details.html')

@app.route('/view-query', methods=['GET', 'POST'])
def view_query():
    progress_sheets = None  # Initialize as None

    if request.method == 'POST':
        house_owner_name = request.form['house_owner_name']
        progress_date = request.form['progressDate']
        
        # Fetch contractor_name using user_id from session
        user_id = session.get('user_id')
        if not user_id:
            return "User not logged in", 401

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Query to get the contractor_name based on user_id
        contractor_query = """
        SELECT name FROM contractors WHERE id = %s
        """
        cursor.execute(contractor_query, (user_id,))
        contractor_result = cursor.fetchone()

        if contractor_result:
            contractor_name = contractor_result['name']

            # Fetch progress details from the database
            progress_query = """
            SELECT progress_date, site_engineer, user_query 
            FROM progress_sheets 
            WHERE contractor_name = %s 
            AND house_owner_id = (
                SELECT id FROM house_owners WHERE owner_name = %s
            ) 
            AND progress_date <= %s
            ORDER BY progress_date DESC
            LIMIT 1
            """
            cursor.execute(progress_query, (contractor_name, house_owner_name, progress_date))
            progress_sheets = cursor.fetchone()
        
        cursor.close()
        connection.close()

    return render_template('view-query.html', progress_sheets=progress_sheets)


@app.route('/project-details/<int:project_id>')
def project_details(project_id):
    if 'user_id' not in session or session['user_type'] != 'contractor':
        return redirect(url_for('login_form'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s AND contractor_id = %s", (project_id, session['user_id']))
        project = cursor.fetchone()
    except Error as e:
        return f"Error: {e}"
    finally:
        cursor.close()
        conn.close()

    if not project:
        return "Project not found."

    return render_template('project-details.html', project=project)

@app.route('/delete-project/<int:project_id>', methods=['GET'])
def delete_project(project_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use %s for placeholders if using pymysql or MySQLdb; for mysql-connector, use %(variable)s
        cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()

    except Exception as e:
        print(f"Error occurred: {e}")
        # Handle error (e.g., show an error page or message)
        return redirect(url_for('contractor_dashboard'))  # Redirect to home or error page

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('contractor_dashboard'))

"""@app.route('/contractor-home')
def contractor_home():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()
        
    except Exception as e:
        print(f"Error occurred: {e}")
        # Handle error (e.g., show an error page or message)
        return redirect(url_for('index'))  # Redirect to an index or error page

    finally:
        cursor.close()
        connection.close()
    
    return render_template('contractor-home.html', projects=projects)
"""
@app.route('/progress-container')
def progress_container():
    # This could render a page where the user selects a project or some other default behavior
    return render_template('send-progress-sheet.html')

@app.route('/submit-progress', methods=['POST'])
def submit_progress():
    conn = None
    cursor = None
    try:
        # Retrieve form data
        progress_date = request.form.get('progressDate')
        site_engineer = request.form.get('siteEngineer')
        type_of_work = request.form.get('typeOfWork')
        number_of_labourers = request.form.get('numberOfLabourers')
        male_workers = request.form.get('maleWorkers')
        female_workers = request.form.get('femaleWorkers')
        material_arrival = request.form.get('materialArrival')
        material_type = request.form.get('materialType', '')  # Default to empty if not provided
        other_info = request.form.get('otherInfo')
        project_name = request.form.get('projectName')

        # Handle file upload
        upload_progress = request.files.get('uploadProgress')
        upload_progress_blob = None
        if upload_progress and upload_progress.filename:
            upload_progress_blob = upload_progress.read()

        # Initialize database connection and cursor
        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve project details based on project name
        cursor.execute("SELECT id, contractor_name, house_owner_id FROM projects WHERE project_name = %s", (project_name,))
        project_details = cursor.fetchone()

        if not project_details:
            return "Error: Project not found", 404

        project_id, contractor_name, house_owner_id = project_details

        # Insert progress sheet data into database, including contractor name
        insert_query = """
        INSERT INTO progress_sheets (progress_date, site_engineer, type_of_work, number_of_labourers, male_workers, female_workers, material_arrival, material_type, upload_progress, other_info, project_id, house_owner_id, project_name, contractor_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (
            progress_date, site_engineer, type_of_work, number_of_labourers,
            male_workers, female_workers, material_arrival, material_type,
            upload_progress_blob, other_info, project_id, house_owner_id, project_name, contractor_name
        ))
        conn.commit()

        return redirect(url_for('contractor_dashboard'))  # Redirect after successful submission

    except KeyError as e:
        return f"Missing form data: {e}"

    except Error as e:
        return f"Error: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/signup/add-project')
def add_project_form():
    return render_template('add-project.html')

@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

# Route to handle adding a new project
@app.route('/add-project', methods=['POST'])
def add_project():
    project_name = request.form['projectName']
    building_area = request.form['buildingArea']
    building_type = request.form['buildingType']
    client_name = request.form['clientName']
    client_mobile = request.form['clientMobile']
    client_email = request.form['clientEmail']
    construction_address = request.form['constructionAddress']
    start_date = request.form['startDate']
    end_date = request.form['endDate']
    
    drawing_blob = None
    if 'projectDrawings' in request.files:
        project_drawings = request.files['projectDrawings']
        if project_drawings.filename != '':
            drawing_blob = project_drawings.read()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        contractor_sql = "SELECT id, name FROM contractors WHERE user_id = %s LIMIT 1"
        cursor.execute(contractor_sql, (session['user_id'],))
        contractor_result = cursor.fetchone()

        if not contractor_result:
            return "No matching contractor found for the logged-in user"

        contractor_id = contractor_result[0]
        contractor_name = contractor_result[1]

        # Check if house owner exists
        owner_sql = "SELECT id FROM house_owners WHERE owner_name = %s AND contractor_name = %s LIMIT 1"
        cursor.execute(owner_sql, (client_name, contractor_name))
        house_owner = cursor.fetchone()

        house_owner_id = house_owner[0] if house_owner else None
        
        # Insert project, allowing house_owner_id to be NULL
        project_sql = """
        INSERT INTO projects (project_name, building_area, building_type, client_name, client_mobile, client_email, construction_address, start_date, end_date, drawing, contractor_id, contractor_name, house_owner_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        project_values = (project_name, building_area, building_type, client_name, client_mobile, client_email, construction_address, start_date, end_date, drawing_blob, contractor_id, contractor_name, house_owner_id)
        cursor.execute(project_sql, project_values)

        conn.commit()

        return redirect(url_for('contractor_dashboard'))

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()



# Route to handle house owner sign-up form submission
@app.route('/signup/houseowner', methods=['POST'])
def houseowner_signup():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirmPassword']

    if password != confirm_password:
        return "Passwords do not match. Please try again."

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if house owner already exists
        existing_owner_sql = "SELECT id FROM house_owners WHERE owner_name = %s AND contractor_name = %s"
        cursor.execute(existing_owner_sql, (request.form['ownerName'], request.form['contractorName']))
        existing_owner = cursor.fetchone()

        if existing_owner:
            house_owner_id = existing_owner[0]
        else:
            # Insert user data into the users table
            user_sql = "INSERT INTO users (username, password, user_type) VALUES (%s, %s, %s)"
            user_values = (username, password, 'houseOwner')
            cursor.execute(user_sql, user_values)
            user_id = cursor.lastrowid

            # Get house owner details from the form
            owner_name = request.form['ownerName']
            contractor_name = request.form['contractorName']
            building_address = request.form['buildingAddress']
            owner_mobile = request.form['ownerMobile']
            email = request.form['email']

            # Insert house owner details into the house_owners table
            house_owner_sql = """
            INSERT INTO house_owners (user_id, owner_name, contractor_name, building_address, owner_mobile, email)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            house_owner_values = (user_id, owner_name, contractor_name, building_address, owner_mobile, email)
            cursor.execute(house_owner_sql, house_owner_values)
            house_owner_id = cursor.lastrowid

            update_user_sql = "UPDATE users SET user_id = %s WHERE id = %s"
            cursor.execute(update_user_sql, (house_owner_id, user_id))

        # Update existing projects with matching contractor_name and client_name
        update_projects_sql = """
        UPDATE projects 
        SET house_owner_id = %s 
        WHERE contractor_name = %s AND client_name = %s AND house_owner_id IS NULL
        """
        cursor.execute(update_projects_sql, (house_owner_id, request.form['contractorName'], request.form['ownerName']))

        conn.commit()

        return "Sign-up successful!"

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()


# Route to display the contractor dashboard
# Route to display the contractor dashboard (contractor-home.html)
@app.route('/contractor-home')
def contractor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'contractor':
        return redirect(url_for('login_form'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch projects assigned to this contractor
        cursor.execute("SELECT id, project_name FROM projects WHERE contractor_id = %s", (session['user_id'],))
        projects = cursor.fetchall()

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

    return render_template('contractor-home.html', projects=projects)

# Route to display the house owner dashboard
@app.route('/house-owner-home', methods=['GET'])
def houseowner_dashboard():
    user_id = session.get('user_id')  # Fetch user_id from the session, which should correspond to house_owner_id

    if not user_id:
        return redirect('/login')  # Redirect to login if the user is not logged in

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Debug: Log the user_id
        #print(f"Debug: user_id = {user_id}")

        # Query to get the latest project name, contractor name, and site engineer name
        cursor.execute("""
            SELECT project_name, contractor_name, site_engineer 
            FROM progress_sheets
            WHERE house_owner_id = %s
            ORDER BY progress_date DESC
            LIMIT 1
        """, (user_id,))
        progress = cursor.fetchone()

        # Debug: Log the query result
        #print(f"Debug: progress data = {progress}")

    except Error as e:
        #print(f"Error: {e}")  # Log the error for debugging
        return render_template('houseowner-home.html', error="Error fetching data.")

    finally:
        cursor.close()
        conn.close()

    if progress:
        return render_template('houseowner-home.html', 
                               project_name=progress['project_name'],
                               contractor_name=progress['contractor_name'],
                               siteEngineer=progress['site_engineer'])
    else:
        return render_template('houseowner-home.html', error="No progress data found.")

@app.route('/get-progress', methods=['POST'])
def get_progress():
    house_owner_id = session.get('user_id')  # Get house_owner_id from the session
    progress_date = request.form.get('progressDate')  # Get the date entered by the user

    if not house_owner_id or not progress_date:
        return redirect('/login')  # Redirect to login if user is not logged in or date is not provided

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query to get the progress details for the given date
        cursor.execute("""
            SELECT progress_date, site_engineer, type_of_work, number_of_labourers, 
                   male_workers, female_workers, material_arrival, material_type, 
                   other_info, upload_progress
            FROM progress_sheets
            WHERE house_owner_id = %s AND progress_date <= %s
            ORDER BY progress_date DESC
            LIMIT 1
        """, (house_owner_id, progress_date))
        progress = cursor.fetchone()

        # Convert the BLOB to a base64 string if there is an image
        if progress and progress['upload_progress']:
            progress['upload_progress'] = base64.b64encode(progress['upload_progress']).decode('utf-8')

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

    if progress:
        return render_template('get-progress.html', progress_sheets=progress)
    else:
        error_message = "No progress data found for the selected date."
        return render_template('houseowner-home.html', error=error_message)

@app.route('/send-query', methods=['POST'])
def send_query():
    house_owner_id = session.get('user_id')
    user_query = request.form.get('userQuery')
    progress_date = request.form.get('progress_date')

    if not house_owner_id or not user_query or not progress_date:
        return redirect('/house-owner-home')  # Redirect if required data is missing

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the query into the progress_sheets table
        cursor.execute("""
            UPDATE progress_sheets
            SET user_query = %s
            WHERE house_owner_id = %s AND progress_date = %s
        """, (user_query, house_owner_id, progress_date))
        conn.commit()

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

    return redirect('/house-owner-home')  # Redirect back to the house owner home page after submission

@app.route('/submit-query', methods=['POST'])
def submit_query():
    house_owner_id = session.get('user_id')
    user_query = request.form.get('userQuery')
    progress_date = request.form.get('progress_date')

    if not house_owner_id or not user_query or not progress_date:
        return redirect('/house-owner-home')  # Redirect if required data is missing

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the query into the progress_sheets table
        cursor.execute("""
            UPDATE progress_sheets
            SET user_query = %s
            WHERE house_owner_id = %s AND progress_date = %s
        """, (user_query, house_owner_id, progress_date))
        conn.commit()

    except Error as e:
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

    return redirect('/house-owner-home')  # Redirect back to the house owner home page after submission

if __name__ == '__main__':
    app.run(debug=True)
