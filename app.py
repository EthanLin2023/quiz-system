from flask import Flask, jsonify, request, render_template
import mysql.connector
import random
import os

app = Flask(__name__)

# 資料庫連線函數
def connect_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
        ssl_ca=os.getenv("SSL_CA_PATH", "ca.pem")
    )

# 首頁路由
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# API：取得章節列表（不重複）
@app.route('/api/chapters', methods=['GET'])
def get_chapters():
    chapters = ['chapter_1', 'chapter_2', 'chapter_3', 'chapter_6']
    return jsonify({"chapters": chapters})

# API：取得指定章節的題目數量
@app.route('/api/questions/count', methods=['GET'])
def get_question_count():
    chapter = request.args.get('chapter')
    if not chapter:
        return jsonify({"error": "必須提供章節名稱"}), 400
    
    # 根據 chapter 映射到 exams.id 的第 9~11 碼
    chapter_map = {
        'chapter_1': 'ch1',
        'chapter_2': 'ch2',
        'chapter_3': 'ch3',
        'chapter_6': 'ch6'
    }
    chapter_code = chapter_map.get(chapter)
    if not chapter_code:
        return jsonify({"error": "無效的章節名稱"}), 400

    db = connect_db()
    cursor = db.cursor()
    # 使用 SUBSTRING 提取 exams.id 的第 9~11 碼進行比對
    query = """
        SELECT COUNT(*) 
        FROM question_pages qp 
        JOIN exams e ON qp.exam_id = e.id 
        WHERE SUBSTRING(e.id, 9, 3) = %s
    """
    cursor.execute(query, (chapter_code,))
    total = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return jsonify({"total_questions": total})

# API：取得指定章節和範圍的題目資料
@app.route('/api/questions', methods=['GET'])
def get_questions():
    chapter = request.args.get('chapter')
    start = int(request.args.get('start', 1)) - 1  # 轉為 0 開始的索引
    end = int(request.args.get('end', 1))
    if not chapter:
        return jsonify({"error": "必須提供章節名稱"}), 400

    # 根據 chapter 映射到 exams.id 的第 9~11 碼
    chapter_map = {
        'chapter_1': 'ch1',
        'chapter_2': 'ch2',
        'chapter_3': 'ch3',
        'chapter_6': 'ch6'
    }
    chapter_code = chapter_map.get(chapter)
    if not chapter_code:
        return jsonify({"error": "無效的章節名稱"}), 400

    db = connect_db()
    cursor = db.cursor(dictionary=True)
    
    # 查詢題目，並提取 exams.id 的最後 2 碼作為題號
    query = """
        SELECT qp.id, qp.exam_id, 
               SUBSTRING(qp.exam_id, -2) AS question_number,  -- 提取 exams.id 的最後 2 碼
               qp.content_text AS question, 
               ap.correct_answer_index, 
               o.index AS opt_index, 
               o.text AS opt_text, 
               o.explanation AS opt_explanation
        FROM question_pages qp
        JOIN exams e ON qp.exam_id = e.id
        LEFT JOIN answer_pages ap ON qp.exam_id = ap.exam_id AND qp.index = ap.index
        LEFT JOIN options o ON ap.id = o.answer_page_id
        WHERE SUBSTRING(e.id, 9, 3) = %s
        ORDER BY qp.id
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (chapter_code, end - start, start))
    rows = cursor.fetchall()

    questions = {}
    for row in rows:
        q_id = row['id']
        if q_id not in questions:
            questions[q_id] = {
                "question": row['question'],
                "question_number": row['question_number'],  # 新增題號
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