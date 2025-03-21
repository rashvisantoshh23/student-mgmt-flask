from flask import Flask, render_template, request, url_for, redirect, jsonify, Response
from pymongo import MongoClient
from config import DB_URL  # Import DB_URL from config.py
from bson import ObjectId
from datetime import datetime
import csv
import io

client = MongoClient(DB_URL)  # Create database connection
db = client['students']  # Create database object

app = Flask(__name__)

@app.route('/')
def index():
    student_list = db.students.find({}).sort("regNo", 1)
    students = []
    for student in student_list:
        attendance = student.get('attendance', {})  
        if not isinstance(attendance, dict):
            attendance = {}  
        total_present = sum(subject.get('attended', 0) for subject in attendance.values() if isinstance(subject, dict))
        total_completed = sum(subject.get('total', 0) for subject in attendance.values() if isinstance(subject, dict))
        percentage = (total_present / total_completed) * 100 if total_completed > 0 else 0
        student['attendance_percentage'] = round(percentage, 2)
        students.append(student)
    return render_template('index.html', student_list=students)

# Complaint Portal
@app.route('/complaint-portal/', methods=['GET', 'POST'])
def complaint_portal():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        category = request.form['category']
        message = request.form['message']
        
        db.complaints.insert_one({
            'name': name,
            'email': email,
            'category': category,
            'message': message,
            'timestamp': datetime.now()
        })
        
        return redirect(url_for('complaint_portal'))

    complaints = list(db.complaints.find().sort("timestamp", -1))
    return render_template('complaint_portal.html', complaints=complaints)

@app.route('/add-student/', methods=['POST'])
def addStudent():
    data = request.form
    db.students.insert_one({
        'name': data['name'],
        'regNo': data['registerNumber'],
        'class': data['class'],
        'email': data['email'],
        'phone': data['phone'],
        'attendance': {}
    })
    return redirect(url_for('index'))

@app.route('/delete-student/<id>/')
def deleteStudent(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

@app.route('/update-student/<id>/', methods=['GET', 'POST'])
def editStudent(id):
    if request.method == 'GET':
        student = db.students.find_one({'_id': ObjectId(id)})
        return render_template('index.html', student=student)
    else:
        db.students.update_one({'_id': ObjectId(id)}, {'$set': request.form})
        return redirect(url_for('index'))

@app.route('/login/', methods=['GET', 'POST'])
def user_login():
    return render_template('user_login.html')

@app.route('/register/', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        db.users.insert_one(request.form)
        return redirect(url_for('user_login'))
    return render_template('user_register.html')

@app.route('/attendance/')
def attendance_page():
    student_list = list(db.students.find({}).sort("regNo", 1))
    return render_template('attendance.html', student_list=student_list)

@app.route('/attendance/', methods=['POST'])
def mark_attendance():
    data = request.json
    for record in data:
        student_id = record.get('student_id')
        subject = record.get('subject')
        status = record.get('status')
        student = db.students.find_one({"_id": ObjectId(student_id)})
        if student:
            attendance = student.get('attendance', {})
            subject_data = attendance.get(subject, {'total': 0, 'attended': 0})
            subject_data['total'] += 1
            if status == "Present":
                subject_data['attended'] += 1
            attendance[subject] = subject_data
            db.students.update_one({"_id": ObjectId(student_id)}, {"$set": {"attendance": attendance}})
    return jsonify({"message": "Attendance recorded successfully!"}), 200

@app.route('/students/', methods=['GET', 'POST'])
def students_page():
    student = None
    if request.method == 'POST':
        reg_no = request.form.get('regNo')
        student = db.students.find_one({"regNo": reg_no})
    return render_template('students.html', student=student)

@app.route('/export/')
def export_data():
    students = db.students.find({})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Register Number', 'Class', 'Email', 'Phone'])
    for student in students:
        writer.writerow([student['name'], student['regNo'], student['class'], student['email'], student['phone']])
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=students.csv"})

@app.route('/view_complaints')
def view_complaints():
    complaints = list(db.complaints.find().sort("timestamp", -1))  # Fetch complaints from MongoDB
    return render_template('view_complaints.html', complaints=complaints)


if __name__ == '__main__':
    app.run(debug=True)
