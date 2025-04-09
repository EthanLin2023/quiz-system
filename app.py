from flask import Flask, jsonify, request, render_template
import mysql.connector
import random
import os

app = Flask(__name__)

# Database connection function with SSL support
def connect_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "mydql-exams-yclin67-539b.k.aivencloud.com"),  # Corrected host
            user=os.getenv("DB_USER", "avnadmin"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "defaultdb"),
            port=int(os.getenv("DB_PORT", 17044)),
            ssl_ca=os.getenv("SSL_CA_PATH", "ca.pem"),  # Path to CA certificate
            ssl_verify_cert=True  # Ensure SSL certificate verification
        )
        return conn
    except mysql.connector.Error as e:
        raise Exception(f"Database connection failed: {str(e)}")

# Test database connection endpoint
@app.route('/test-db')
def test_db():
    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "result": result[0]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Home route: Render index.html
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# API: Get total number of questions
@app.route('/api/questions/count', methods=['GET'])
def get_question_count():
    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM question_pages")
        total = cursor.fetchone()[0]
        cursor.close()
        db.close()
        return jsonify({"total_questions": total})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Get questions within a specified range
@app.route('/api/questions', methods=['GET'])
def get_questions():
    try:
        start = int(request.args.get('start', 1)) - 1  # From 0-based index
        end = int(request.args.get('end', 1))
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        
        query = """
            SELECT qp.id, qp.exam_id, qp.content_text AS question, 
                   ap.correct_answer_index, o.index AS opt_index, o.text AS opt_text, o.explanation AS opt_explanation
            FROM question_pages qp
            LEFT JOIN answer_pages ap ON qp.exam_id = ap.exam_id AND qp.index = ap.index
            LEFT JOIN options o ON ap.id = o.answer_page_id
            WHERE qp.id BETWEEN %s AND %s
        """
        cursor.execute(query, (start + 1, end))
        rows = cursor.fetchall()

        questions = {}
        for row in rows:
            q_id = row['id']
            if q_id not in questions:
                questions[q_id] = {
                    "question": row['question'],
                    "options": [],
                    "correct_answer_index": row['correct_answer_index'],
                    "explanations": {}
                }
            questions[q_id]["options"].append({"index": row['opt_index'], "text": row['opt_text']})
            questions[q_id]["explanations"][row['opt_index']] = row['opt_explanation']

        for q in questions.values():
            random.shuffle(q["options"])
        
        cursor.close()
        db.close()
        return jsonify(list(questions.values()))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)