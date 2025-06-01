import os
import pandas as pd
import random
import json
import uuid
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)
# 设置 session 配置
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 会话1小时后过期
# 只有在生产环境中才启用安全cookie
if not app.debug:
    app.config['SESSION_COOKIE_SECURE'] = True

# 创建缓存目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Add custom Jinja2 filter for converting index to letter choices
@app.template_filter('upper_alpha')
def upper_alpha(index):
    if isinstance(index, int) or index.isdigit():
        index = int(index)
        return chr(65 + index)  # 65 is ASCII for 'A'
    return index

# 缓存清理：删除1小时前的缓存文件
def clean_old_caches():
    now = time.time()
    try:
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < now - 3600:
                try:
                    os.remove(file_path)
                    print(f"已删除过期缓存: {filename}")
                except Exception as e:
                    print(f"删除缓存文件失败: {filename}, 错误: {e}")
    except Exception as e:
        print(f"清理缓存时出错: {e}")

# 检查会话是否有效
def check_session_valid():
    # 检查会话ID是否存在且有效
    if 'quiz_session_id' in session:
        session_id = session['quiz_session_id']
        # 检查会话文件是否存在
        cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
        if not os.path.exists(cache_file):
            # 会话文件不存在，可能已过期被清理
            if 'quiz_sessions' in session:
                # 从会话中移除
                current_topic = get_current_topic()
                if current_topic in session['quiz_sessions']:
                    del session['quiz_sessions'][current_topic]
                    session.modified = True
            return False
    return True

# 保存题目到缓存文件
def save_questions_to_cache(questions, session_id):
    cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存缓存文件出错: {e}")
        return False

# 从缓存文件加载题目
def load_questions_from_cache(session_id):
    cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
    if not session_id or not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取缓存文件出错: {e}")
        return None

# 保存用户答题历史
def save_user_answers(session_id, answers):
    if not session_id:
        return False
        
    answers_file = os.path.join(CACHE_DIR, f"{session_id}_answers.json")
    try:
        with open(answers_file, 'w', encoding='utf-8') as f:
            json.dump(answers, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存用户答案出错: {e}")
        return False

# 加载用户答题历史
def load_user_answers(session_id):
    answers_file = os.path.join(CACHE_DIR, f"{session_id}_answers.json")
    if not session_id or not os.path.exists(answers_file):
        return {}
    
    try:
        with open(answers_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取用户答案出错: {e}")
        return {}

# 获取当前练习的主题
def get_current_topic():
    if 'quiz_session_id' in session and 'quiz_sessions' in session:
        session_id = session['quiz_session_id']
        for topic, sid in session['quiz_sessions'].items():
            if sid == session_id:
                return topic
    return 'random'

# Load quiz data from Excel file
def load_quiz_data():
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'C919飞机机型培训题库.xlsx')
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到题库文件: {file_path}")
        return []
    
    try:
        df = pd.read_excel(file_path)
        
        questions = []
        for _, row in df.iterrows():
            # Extract choices that are not NaN
            choices = []
            for i in range(1, 11):
                choice_col = f'Choice {i}'
                if choice_col in row and pd.notna(row[choice_col]) and str(row[choice_col]).strip():
                    choices.append(str(row[choice_col]))
            
            # Only add questions with valid data
            if pd.notna(row['Question Title']) and pd.notna(row['Correct Answer']) and choices:
                # The correct answer in the data is given as A, B, C, etc.
                correct_answer = str(row['Correct Answer']).strip()
                # Sometimes there might be \t in the answer
                if '\t' in correct_answer:
                    correct_answer = correct_answer.replace('\t', '')
                
                question = {
                    'id': str(row['SID']) if pd.notna(row['SID']) else str(uuid.uuid4()),
                    'topic': str(row['Topic Name']) if pd.notna(row['Topic Name']) else 'Unknown',
                    'subtopic': str(row['SubTopicName']) if pd.notna(row['SubTopicName']) else 'Unknown',
                    'question': str(row['Question Title']),
                    'correct_answer': correct_answer,
                    'choices': choices,
                    'difficulty': str(row['Difficulty']) if pd.notna(row['Difficulty']) else 'Medium',
                }
                questions.append(question)
        
        return questions
    except Exception as e:
        print(f"加载题库数据时出错: {e}")
        return []

@app.route('/')
def index():
    # 每次访问首页，清理旧缓存
    clean_old_caches()
    
    # 确保会话持久化
    session.permanent = True
    
    # 显示练习进度
    progress = {}
    if 'quiz_sessions' in session:
        for topic, session_id in session['quiz_sessions'].items():
            answers = load_user_answers(session_id)
            questions = load_questions_from_cache(session_id)
            if questions and answers:
                total = len(questions)
                answered = len(answers)
                progress[topic] = {
                    'total': total,
                    'answered': answered,
                    'percentage': int((answered / total) * 100) if total > 0 else 0,
                    'session_id': session_id
                }
    
    return render_template('index.html', progress=progress)

@app.route('/quiz')
def quiz():
    # 检查是否有新的练习标记和主题
    new_session = request.args.get('new_session', 'false') == 'true'
    topic = request.args.get('topic', 'random')
    
    # 检查会话有效性
    is_session_valid = check_session_valid()
    
    # 如果是随机练习且有进行中的随机练习
    if topic == 'random' and not new_session and is_session_valid and 'quiz_sessions' in session and 'random' in session['quiz_sessions']:
        session_id = session['quiz_sessions']['random']
        questions = load_questions_from_cache(session_id)
        answers = load_user_answers(session_id)
        
        if questions and answers is not None:
            # 继续之前的练习
            current_q = len(answers)
            session['quiz_session_id'] = session_id
            session['current_question'] = current_q
            session['current_topic'] = 'random'
            
            # 如果已全部回答完，跳转到结果页
            if current_q >= len(questions):
                return redirect(url_for('results'))
            
            question = questions[current_q]
            print(f"继续随机练习，题目: {question['question']}")
            return render_template('quiz.html', 
                                   question=question, 
                                   question_number=current_q+1, 
                                   total_questions=len(questions),
                                   topic='random')
    
    # 如果是按主题练习且有进行中的主题练习
    if topic != 'random' and not new_session and is_session_valid and 'quiz_sessions' in session and topic in session['quiz_sessions']:
        session_id = session['quiz_sessions'][topic]
        questions = load_questions_from_cache(session_id)
        answers = load_user_answers(session_id)
        
        if questions and answers is not None:
            # 继续之前的练习
            current_q = len(answers)
            session['quiz_session_id'] = session_id
            session['current_question'] = current_q
            session['current_topic'] = topic
            
            # 如果已全部回答完，跳转到结果页
            if current_q >= len(questions):
                return redirect(url_for('results'))
            
            question = questions[current_q]
            print(f"继续{topic}练习，题目: {question['question']}")
            return render_template('quiz.html', 
                                   question=question, 
                                   question_number=current_q+1, 
                                   total_questions=len(questions),
                                   topic=topic)
    
    # 创建新的quiz session
    session_id = str(uuid.uuid4())
    session['quiz_session_id'] = session_id
    session['current_question'] = 0
    session['score'] = 0
    session['current_topic'] = topic
    
    # 确保存在quiz_sessions字典
    if 'quiz_sessions' not in session:
        session['quiz_sessions'] = {}
    
    # 根据主题加载题目
    if topic != 'random':
        all_questions = load_quiz_data()
        topic_questions = [q for q in all_questions if q['topic'] == topic or q['subtopic'] == topic]
        
        if not topic_questions:
            return redirect(url_for('index'))
        
        questions = topic_questions
        session['quiz_sessions'][topic] = session_id
    else:
        # 随机练习
        questions = load_quiz_data()
        random.shuffle(questions)
        session['quiz_sessions']['random'] = session_id
    
    # 保存题目到缓存
    random.shuffle(questions)
    save_questions_to_cache(questions, session_id)
    
    # 初始化答题历史
    save_user_answers(session_id, {})
    
    question = questions[0]
    print(f"新建练习，题目: {question['question']}")
    print(f"正确答案: {question['correct_answer']}")
    
    return render_template('quiz.html', 
                           question=question, 
                           question_number=1, 
                           total_questions=len(questions),
                           topic=topic)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if 'quiz_session_id' not in session:
        return jsonify({
            'error': True,
            'message': '会话已过期',
            'redirect': url_for('quiz')
        }), 400
    
    # 检查会话有效性
    if not check_session_valid():
        return jsonify({
            'error': True,
            'message': '会话已过期',
            'redirect': url_for('quiz')
        }), 400
    
    session_id = session['quiz_session_id']
    user_answer = request.form.get('answer')
    
    # 验证答案格式
    if not user_answer or not isinstance(user_answer, str) or len(user_answer) != 1:
        return jsonify({
            'error': True,
            'message': '无效的答案格式'
        }), 400
        
    current_q = session.get('current_question', 0)
    current_topic = session.get('current_topic', 'random')
    
    # 从缓存加载题目和答题历史
    questions = load_questions_from_cache(session_id)
    answers = load_user_answers(session_id)
    
    if not questions or current_q >= len(questions):
        return jsonify({
            'error': True,
            'message': '题目不存在或已完成',
            'redirect': url_for('quiz')
        }), 400
    
    question = questions[current_q]
    
    print(f"用户提交答案: {user_answer}")
    print(f"正确答案: {question['correct_answer']}")
    
    is_correct = False
    if user_answer == question['correct_answer']:
        is_correct = True
        session['score'] = session.get('score', 0) + 1
        print(f"回答正确!")
    else:
        print(f"回答错误!")
    
    # 保存用户答题记录
    answer_data = {
        'question_id': question['id'],
        'question': question['question'],
        'user_answer': user_answer,
        'correct_answer': question['correct_answer'],
        'is_correct': is_correct,
        'topic': question['topic'],
        'subtopic': question['subtopic'],
        'choices': question['choices']
    }
    
    answers[str(current_q)] = answer_data
    save_result = save_user_answers(session_id, answers)
    
    if not save_result:
        print("保存答案失败")
    
    session['current_question'] = current_q + 1
    session.modified = True
    
    return jsonify({
        'is_correct': is_correct,
        'correct_answer': question['correct_answer'],
        'topic': current_topic
    })

@app.route('/next_question')
def next_question():
    # 获取当前主题，确保继续当前主题的练习
    current_topic = session.get('current_topic', 'random')
    if current_topic != 'random':
        return redirect(url_for('quiz', topic=current_topic))
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    if 'quiz_session_id' not in session:
        return redirect(url_for('index'))
    
    # 检查会话有效性
    if not check_session_valid():
        return redirect(url_for('index'))
    
    session_id = session['quiz_session_id']
    questions = load_questions_from_cache(session_id)
    answers = load_user_answers(session_id)
    
    if not questions:
        return redirect(url_for('quiz'))
    
    total_questions = len(questions)
    
    # 统计正确率
    correct_count = 0
    incorrect_questions = []
    
    for q_idx, answer_data in answers.items():
        if answer_data['is_correct']:
            correct_count += 1
        else:
            # 收集错误答案的详情
            incorrect_questions.append({
                'question': answer_data['question'],
                'user_answer': answer_data['user_answer'],
                'correct_answer': answer_data['correct_answer'],
                'topic': answer_data['topic'],
                'subtopic': answer_data['subtopic'],
                'choices': answer_data['choices']
            })
    
    score = correct_count
    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    
    # 按主题统计错误情况
    topic_stats = {}
    for wrong_q in incorrect_questions:
        topic = wrong_q['topic']
        if topic not in topic_stats:
            topic_stats[topic] = {'count': 0}
        topic_stats[topic]['count'] += 1
    
    # 获取当前主题，用于返回按钮
    current_topic = session.get('current_topic', 'random')
    
    return render_template('results.html', 
                           score=score, 
                           total_questions=total_questions,
                           percentage=percentage,
                           session_id=session_id,
                           incorrect_questions=incorrect_questions,
                           topic_stats=topic_stats,
                           current_topic=current_topic)

@app.route('/reset')
def reset():
    # 清理当前会话的缓存文件
    if 'quiz_session_id' in session:
        cache_file = os.path.join(CACHE_DIR, f"{session['quiz_session_id']}.json")
        answers_file = os.path.join(CACHE_DIR, f"{session['quiz_session_id']}_answers.json")
        
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except:
                pass
        
        if os.path.exists(answers_file):
            try:
                os.remove(answers_file)
            except:
                pass
    
    session.clear()
    return redirect(url_for('index'))

@app.route('/reset_topic/<topic>')
def reset_topic(topic):
    if 'quiz_sessions' in session and topic in session['quiz_sessions']:
        session_id = session['quiz_sessions'][topic]
        
        # 删除缓存文件
        cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
        answers_file = os.path.join(CACHE_DIR, f"{session_id}_answers.json")
        
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except:
                pass
        
        if os.path.exists(answers_file):
            try:
                os.remove(answers_file)
            except:
                pass
        
        # 从session中删除
        del session['quiz_sessions'][topic]
        session.modified = True
    
    return redirect(url_for('index'))

@app.route('/topic/<topic>')
def topic_quiz(topic):
    # 检查是否要重新开始
    new_session = request.args.get('new_session', 'false') == 'true'
    
    if new_session:
        # 如果存在旧session，重置它
        if 'quiz_sessions' in session and topic in session['quiz_sessions']:
            old_session_id = session['quiz_sessions'][topic]
            cache_file = os.path.join(CACHE_DIR, f"{old_session_id}.json")
            answers_file = os.path.join(CACHE_DIR, f"{old_session_id}_answers.json")
            
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except:
                    pass
            
            if os.path.exists(answers_file):
                try:
                    os.remove(answers_file)
                except:
                    pass
    
    return redirect(url_for('quiz', topic=topic, new_session=new_session))

@app.route('/topics')
def topics():
    questions = load_quiz_data()
    topics_list = sorted(list(set(q['topic'] for q in questions if q['topic'] != 'Unknown')))
    subtopics_list = sorted(list(set(q['subtopic'] for q in questions if q['subtopic'] != 'Unknown')))
    
    # 获取每个主题的完成进度
    progress = {}
    if 'quiz_sessions' in session:
        for topic, session_id in session['quiz_sessions'].items():
            if topic == 'random':
                continue
                
            answers = load_user_answers(session_id)
            questions = load_questions_from_cache(session_id)
            if questions and answers:
                total = len(questions)
                answered = len(answers)
                progress[topic] = {
                    'total': total,
                    'answered': answered,
                    'percentage': int((answered / total) * 100) if total > 0 else 0,
                    'session_id': session_id
                }
    
    return render_template('topics.html', 
                           topics=topics_list, 
                           subtopics=subtopics_list,
                           progress=progress)

@app.route('/review/<session_id>')
def review(session_id):
    # 验证 session_id 的格式 (应该是 UUID 格式)
    try:
        uuid_obj = uuid.UUID(session_id)
        if str(uuid_obj) != session_id:
            return redirect(url_for('index'))
    except ValueError:
        return redirect(url_for('index'))
    
    # 检查文件是否存在
    questions = load_questions_from_cache(session_id)
    answers = load_user_answers(session_id)
    
    if not questions or not answers:
        return redirect(url_for('index'))
    
    review_data = []
    for q_idx, answer_data in answers.items():
        review_data.append(answer_data)
    
    return render_template('review.html', 
                           review_data=review_data, 
                           total_questions=len(questions))

if __name__ == '__main__':
    app.run(debug=True) 

# 添加这行使Vercel能够导入应用
app.debug = False 