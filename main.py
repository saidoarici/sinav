from flask import Flask, render_template, request, jsonify, session
import json
import random
import os
import traceback

app = Flask(__name__)
app.secret_key = 'secret-key'

# Sorular dosyalarının yolları
QUESTIONS_PATH = 'sorular.json'  # Arapça sorular
TURKISH_QUESTIONS_PATH = 'sorular_turkce.json'  # Türkçe sorular

# Arapça soruları yükle
if not os.path.exists(QUESTIONS_PATH):
    raise FileNotFoundError(f"{QUESTIONS_PATH} bulunamadı. Lütfen dosyayı doğru dizine koyun.")

try:
    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        arabic_questions = json.load(f)
except Exception as e:
    raise ValueError(f"sorular.json dosyası yüklenemedi: {str(e)}")

# Arapça soruları ID'ye göre hızlı erişim için sözlük yapısına dönüştürme
arabic_questions_dict = {str(q['id']): q for q in arabic_questions}

# Türkçe soruları yükle
if not os.path.exists(TURKISH_QUESTIONS_PATH):
    print(f"Uyarı: {TURKISH_QUESTIONS_PATH} bulunamadı. Türkçe soru hizmeti sağlanamayacak.")
    turkish_questions = []
    turkish_questions_dict = {}
else:
    try:
        with open(TURKISH_QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            turkish_questions = json.load(f)
        # ID'ye göre Türkçe soruları hızlı erişim için sözlük yapısına dönüştürme
        turkish_questions_dict = {str(q['id']): q for q in turkish_questions}
    except Exception as e:
        print(f"Uyarı: sorular_turkce.json dosyası yüklenemedi: {str(e)}")
        turkish_questions = []
        turkish_questions_dict = {}


@app.route('/')
def index():
    try:
        return render_template('exam.html')
    except Exception as e:
        traceback.print_exc()
        return f"Hata: {str(e)}", 500


@app.route('/start-exam', methods=['GET'])
def start_exam():
    try:
        # 40 adet rastgele Arapça soru seç (ID referansı olarak kullanılacak)
        selected_question_ids = random.sample([q['id'] for q in arabic_questions], 40)

        # Doğru cevapları sakla (Arapça sorulara göre)
        correct_answers = {str(q_id): arabic_questions_dict[str(q_id)]['correct_answer'] for q_id in
                           selected_question_ids}
        session['correct_answers'] = correct_answers

        # Kullanıcıya Türkçe soruları gönder (varsa)
        questions_to_send = []
        for q_id in selected_question_ids:
            str_q_id = str(q_id)

            # Öncelikle Türkçe soru var mı diye kontrol et
            if str_q_id in turkish_questions_dict:
                # Türkçe soru varsa onu kullan
                question_data = {
                    'id': q_id,
                    'question': turkish_questions_dict[str_q_id]['question'],
                    'choices': turkish_questions_dict[str_q_id].get('choices', [])
                }
            else:
                # Türkçe soru yoksa Arapça soruyu kullan
                question_data = {
                    'id': q_id,
                    'question': arabic_questions_dict[str_q_id]['question'],
                    'choices': arabic_questions_dict[str_q_id]['choices']
                }

            questions_to_send.append(question_data)

        return jsonify({'questions': questions_to_send})

    except ValueError as ve:
        return jsonify({'error': f'Soru formatı hatalı: {str(ve)}'}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Sınav başlatılamadı. Sunucu hatası.'}), 500


@app.route('/get-arabic-question/<question_id>')
def get_arabic_question(question_id):
    try:
        # question_id string olmalı
        question_id = str(question_id)

        if question_id in arabic_questions_dict:
            arabic_question = arabic_questions_dict[question_id]
            return jsonify({
                'question': arabic_question['question'],
                'id': arabic_question['id'],
                'choices': arabic_question.get('choices', [])
            })
        else:
            return jsonify({'error': 'Arapça soru bulunamadı.'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Arapça soru alınamadı: {str(e)}'}), 500


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
                'choices': turkish_question.get('choices', [])
            })
        else:
            return jsonify({'error': 'Türkçe soru bulunamadı.'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Türkçe soru alınamadı: {str(e)}'}), 500


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