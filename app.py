from flask import Flask, jsonify, request, render_template
import mysql.connector
import random
import os

app = Flask(__name__)

# 從環境變數中獲取資料庫配置
def connect_db():
    try:
        # 建立連線參數
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", "1234"),
            "database": os.getenv("DB_NAME", "exams"),
            "port": int(os.getenv("DB_PORT", 3306)),
        }

        # 若有設定 SSL_CA_PATH，才加入 SSL 配置
        ssl_ca_path = os.getenv("SSL_CA_PATH")
        if ssl_ca_path:
            config["ssl_ca"] = ssl_ca_path

        return mysql.connector.connect(**config)  # ✅ 正確回傳資料庫連線

    except mysql.connector.Error as err:  # ✅ 捕捉連線錯誤
        print(f"[DB ERROR] 無法連接資料庫: {err}")
        return None

# 首頁路由：渲染 index.html
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# API：取得總題數與題目範圍
@app.route('/api/questions/count', methods=['GET'])
def get_question_count():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM question_pages")
    total = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return jsonify({"total_questions": total})

# API：取得指定範圍的題目資料
@app.route('/api/questions', methods=['GET'])
def get_questions():
    start = int(request.args.get('start', 1)) - 1  # 從 0 開始計數
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)