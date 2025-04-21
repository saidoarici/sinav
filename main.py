from flask import Flask, render_template, request, jsonify, session
import json
import random
import os
import traceback

app = Flask(__name__)
app.secret_key = 'secret-key'

# Sorular dosyasının yolu
QUESTIONS_PATH = 'sorular.json'

# Soruları yükle
if not os.path.exists(QUESTIONS_PATH):
    raise FileNotFoundError(f"{QUESTIONS_PATH} bulunamadı. Lütfen dosyayı doğru dizine koyun.")

try:
    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)
except Exception as e:
    raise ValueError(f"sorular.json dosyası yüklenemedi: {str(e)}")

# Türkçe soruları yükle
TURKISH_QUESTIONS_PATH = 'sorular_turkce.json'

# Türkçe sorular dosyasının varlığını kontrol et
if not os.path.exists(TURKISH_QUESTIONS_PATH):
    print(f"Uyarı: {TURKISH_QUESTIONS_PATH} bulunamadı. Türkçe soru hizmeti sağlanamayacak.")
    turkish_questions = []
else:
    try:
        with open(TURKISH_QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            turkish_questions = json.load(f)
        # ID'ye göre Türkçe soruları hızlı erişim için sözlük yapısına dönüştürme
        turkish_questions_dict = {str(q['id']): q for q in turkish_questions}
    except Exception as e:
        print(f"Uyarı: sorular_turkce.json dosyası yüklenemedi: {str(e)}")
        turkish_questions_dict = {}


@app.route('/get-turkish-question/<question_id>')
def get_turkish_question(question_id):
    try:
        # question_id string olmalı
        question_id = str(question_id)

        if question_id in turkish_questions_dict:
            turkish_question = turkish_questions_dict[question_id]
            return jsonify({
                'question': turkish_question['question'],
                'id': turkish_question['id'],
                'choices': turkish_question.get('choices', [])  # Seçenekleri de dahil et
            })
        else:
            return jsonify({'error': 'Türkçe soru bulunamadı.'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Türkçe soru alınamadı: {str(e)}'}), 500




@app.route('/')
def index():
    try:
        return render_template('exam.html')
    except Exception as e:
        traceback.print_exc()
        return f"Hata: {str(e)}", 500


@app.route('/start-exam', methods=['GET'])  # frontend bunu bu şekilde çağırıyor
def start_exam():
    try:
        selected_questions = random.sample(all_questions, 40)
        correct_answers = {str(q['id']): q['correct_answer'] for q in selected_questions}
        session['correct_answers'] = correct_answers

        # Kullanıcıya doğru cevabı göndermeden soruları ilet
        questions_to_send = []
        for q in selected_questions:
            question_data = {
                'id': q['id'],
                'question': q['question'],
                'choices': q['choices']
            }
            questions_to_send.append(question_data)

        return jsonify({'questions': questions_to_send})

    except ValueError as ve:
        return jsonify({'error': f'Soru formatı hatalı: {str(ve)}'}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Sınav başlatılamadı. Sunucu hatası.'}), 500


@app.route('/check-answer', methods=['POST'])
def check_answer():
    try:
        data = request.get_json()
        question_id = str(data.get('question_id'))
        user_answer = data.get('answer')
        correct_answers = session.get('correct_answers', {})

        if question_id not in correct_answers:
            return jsonify({'status': 'error', 'message': 'Soru bulunamadı.'}), 400

        correct_answer = correct_answers[question_id]
        is_correct = user_answer == correct_answer
        return jsonify({'correct': is_correct, 'correct_answer': correct_answer})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'Cevap kontrolünde hata oluştu.'}), 500


@app.route('/submit-exam', methods=['POST'])
def submit_exam():
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        correct_answers = session.get('correct_answers', {})

        score = sum(1 for qid, ans in answers.items() if correct_answers.get(str(qid)) == ans)
        passed = score >= 28
        return jsonify({'score': score, 'passed': passed})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Sınav sonucu hesaplanamadı.'}), 500





# Hata yöneticileri
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Sayfa bulunamadı (404)', 'url': request.url}), 404


@app.errorhandler(500)
def internal_error(e):
    traceback.print_exc()
    return jsonify({'error': 'Sunucu hatası oluştu (500).'}), 500


if __name__ == '__main__':
    app.run(debug=False, port=4000, host='0.0.0.0')