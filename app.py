from flask import Flask, jsonify, request, render_template
import mysql.connector
import random
import os

app = Flask(__name__)

# Database connection
def connect_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
        ssl_ca=os.getenv("SSL_CA_PATH", "ca.pem")
    )

# Home route
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# API: Get list of chapters
@app.route('/api/chapters', methods=['GET'])
def get_chapters():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT title FROM exams WHERE title IN ('chapter_1', 'chapter_2', 'chapter_3', 'chapter_6')")
    chapters = [row[0] for row in cursor.fetchall()]
    cursor.close()
    db.close()
    return jsonify({"chapters": chapters})

# API: Get total question count for a chapter
@app.route('/api/questions/count', methods=['GET'])
def get_question_count():
    chapter = request.args.get('chapter')
    if not chapter:
        return jsonify({"error": "Chapter is required"}), 400
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM question_pages qp JOIN exams e ON qp.exam_id = e.id WHERE e.title = %s", (chapter,))
    total = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return jsonify({"total_questions": total})

# API: Get questions for a specific chapter and range
@app.route('/api/questions', methods=['GET'])
def get_questions():
    chapter = request.args.get('chapter')
    start = int(request.args.get('start', 1)) - 1  # 0-based index
    end = int(request.args.get('end', 1))
    if not chapter:
        return jsonify({"error": "Chapter is required"}), 400

    db = connect_db()
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT qp.id, qp.exam_id, qp.content_text AS question, 
               ap.correct_answer_index, o.index AS opt_index, o.text AS opt_text, o.explanation AS opt_explanation
        FROM question_pages qp
        JOIN exams e ON qp.exam_id = e.id
        LEFT JOIN answer_pages ap ON qp.exam_id = ap.exam_id AND qp.index = ap.index
        LEFT JOIN options o ON ap.id = o.answer_page_id
        WHERE e.title = %s AND qp.id BETWEEN %s AND %s
    """
    cursor.execute(query, (chapter, start + 1, end))
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)