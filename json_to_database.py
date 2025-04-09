import json
import mysql.connector
from tkinter import Tk, filedialog

# 函數：連接 MySQL 資料庫
def connect_db():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",  # 替換為你的 MySQL 用戶名
            password="1234",  # 替換為你的 MySQL 密碼
            database="exams"  # 替換為你的資料庫名稱
        )
        print("成功連接到 MySQL 資料庫")
        return db
    except mysql.connector.Error as err:
        print(f"資料庫連接失敗: {err}")
        return None

# 函數：使用視窗選取 JSON 檔案
def select_json_file():
    root = Tk()
    root.withdraw()  # 隱藏主視窗，只顯示檔案對話框
    file_path = filedialog.askopenfilename(
        title="請選擇 JSON 檔案",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()  # 關閉 Tkinter 視窗
    return file_path

# 函數：將 JSON 資料存入 MySQL
def import_json_to_mysql(file_path, db):
    cursor = db.cursor()

    # 讀取 JSON 檔案
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"無法讀取 JSON 檔案: {e}")
        return

    # 插入資料
    for exam in data:
        try:
            # 插入 exams 表格
            cursor.execute("INSERT IGNORE INTO exams (id, title) VALUES (%s, %s)", 
                          (exam['id'], exam['title']))

            # 插入 question_pages 表格
            for q_page in exam['questionPages']:
                # 檢查 explanation 是否存在，若不存在則設為 None
                explanation = q_page.get('explanation', None)
                cursor.execute("""
                    INSERT INTO question_pages (exam_id, `index`, content_type, content_text, explanation)
                    VALUES (%s, %s, %s, %s, %s)
                """, (exam['id'], q_page['index'], q_page['content']['type'], 
                      q_page['content']['text'], explanation))

            # 插入 answer_pages 表格
            for a_page in exam['answerPages']:
                cursor.execute("""
                    INSERT INTO answer_pages (exam_id, `index`, correct_answer_index)
                    VALUES (%s, %s, %s)
                """, (exam['id'], a_page['index'], a_page['correctAnswerIndex']))
                answer_page_id = cursor.lastrowid  # 取得剛插入的 answer_page ID

                # 插入 options 表格
                for option in a_page['options']:
                    cursor.execute("""
                        INSERT INTO options (answer_page_id, `index`, text, explanation)
                        VALUES (%s, %s, %s, %s)
                    """, (answer_page_id, option['index'], option['text'], option['explanation']))

            print(f"成功插入試卷: {exam['id']}")
        except mysql.connector.Error as err:
            print(f"插入資料失敗: {err}")
            db.rollback()  # 回滾交易
            return
        except KeyError as ke:
            print(f"JSON 結構錯誤，缺少欄位: {ke}")
            db.rollback()  # 回滾交易
            return

    # 提交更改
    db.commit()
    print("所有資料已成功存入 MySQL")
    cursor.close()

# 主程式
def main():
    # 連接資料庫
    db = connect_db()
    if db is None:
        return

    # 選取 JSON 檔案
    file_path = select_json_file()
    if not file_path:
        print("未選擇任何檔案")
        db.close()
        return

    print(f"已選擇檔案: {file_path}")
    
    # 將資料存入 MySQL
    import_json_to_mysql(file_path, db)

    # 關閉資料庫連接
    db.close()

if __name__ == "__main__":
    main()