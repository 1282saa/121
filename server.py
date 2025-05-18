from flask import Flask, send_from_directory, jsonify, render_template, request
import os
import logging
from pathlib import Path
import mimetypes
import json
import threading
import time

# RAG 챗봇 모듈 import
import modules.rag_chatbot as rag_chatbot
import modules.hybrid_chatbot as hybrid_chatbot
import modules.ai_search as ai_search

app = Flask(__name__)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/server.log'
)
logger = logging.getLogger(__name__)

# MIME 타입 설정
mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

# 디렉토리 설정
ROOT_DIR = Path(__file__).parent
ECONOMY_TERMS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/economy_terms")
RECENT_CONTENTS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/recent_contents_final")

logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"ECONOMY_TERMS_DIR: {ECONOMY_TERMS_DIR}")
logger.info(f"RECENT_CONTENTS_DIR: {RECENT_CONTENTS_DIR}")

# 폴더가 없는 경우 생성
os.makedirs(ECONOMY_TERMS_DIR, exist_ok=True)
os.makedirs(RECENT_CONTENTS_DIR, exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# 챗봇 초기화 상태
chatbot_ready = False
chatbot_initializing = False

# AI 검색 초기화 상태
ai_search_ready = False
ai_search_initializing = False

# 서버 시작 시 AI 검색 자동 초기화 함수
def initialize_ai_search_at_startup():
    global ai_search_ready, ai_search_initializing
    try:
        logger.info("서버 시작 시 AI 검색 자동 초기화 시작")
        ai_search_initializing = True
        success = ai_search.initialize_search_engine()
        ai_search_ready = success
        ai_search_initializing = False
        logger.info(f"AI 검색 자동 초기화 완료: {success}")
    except Exception as e:
        logger.error(f"AI 검색 자동 초기화 중 오류 발생: {str(e)}")
        ai_search_ready = False
        ai_search_initializing = False

# 서버 시작 시 백그라운드에서 AI 검색 초기화 실행
threading.Thread(target=initialize_ai_search_at_startup).start()

# CORS 설정
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@app.route('/')
def index():
    return send_from_directory('templates', 'ui.html')

@app.route('/ai-search')
def ai_search_page():
    return send_from_directory('templates', 'ui.html')

# 정적 파일 제공
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/js/<path:filename>')
def serve_js(filename):
    logger.info(f"JS 파일 요청(레거시 경로): {filename}")
    return send_from_directory('static/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    logger.info(f"CSS 파일 요청(레거시 경로): {filename}")
    return send_from_directory('static/css', filename)

@app.route('/api/economy_terms')
def get_economy_terms():
    """경제 용어 마크다운 파일 목록 반환"""
    files = []
    if ECONOMY_TERMS_DIR.exists():
        try:
            for file in ECONOMY_TERMS_DIR.glob('*.md'):
                files.append(file.name)
            logger.info(f"경제 용어 파일 목록 반환: {len(files)}개")
        except Exception as e:
            logger.error(f"경제 용어 파일 목록 조회 오류: {str(e)}")
    else:
        logger.warning(f"경제 용어 디렉토리가 존재하지 않음: {ECONOMY_TERMS_DIR}")
    
    return jsonify({'files': files})

@app.route('/api/recent_contents')
def get_recent_contents():
    """최신 콘텐츠 마크다운 파일 목록 반환"""
    files = []
    if RECENT_CONTENTS_DIR.exists():
        try:
            for file in RECENT_CONTENTS_DIR.glob('*.md'):
                files.append(file.name)
            logger.info(f"최신 콘텐츠 파일 목록 반환: {len(files)}개")
        except Exception as e:
            logger.error(f"최신 콘텐츠 파일 목록 조회 오류: {str(e)}")
    else:
        logger.warning(f"최신 콘텐츠 디렉토리가 존재하지 않음: {RECENT_CONTENTS_DIR}")
    
    return jsonify({'files': files})

@app.route('/api/economy_terms/<path:filename>')
def get_economy_term(filename):
    """특정 경제 용어 마크다운 파일 내용 반환"""
    try:
        file_path = ECONOMY_TERMS_DIR / filename
        logger.info(f"경제 용어 파일 요청: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"경제 용어 파일 로드 오류: {str(e)}")
        return str(e), 404

@app.route('/api/recent_contents/<path:filename>')
def get_recent_content(filename):
    """특정 최신 콘텐츠 마크다운 파일 내용 반환"""
    try:
        file_path = RECENT_CONTENTS_DIR / filename
        logger.info(f"최신 콘텐츠 파일 요청: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"최신 콘텐츠 파일 로드 오류: {str(e)}")
        return str(e), 404

# RAG 챗봇 API
@app.route('/api/chatbot/status')
def chatbot_status():
    """챗봇 초기화 상태 확인"""
    global chatbot_ready, chatbot_initializing
    return jsonify({
        'ready': chatbot_ready,
        'initializing': chatbot_initializing
    })

@app.route('/api/chatbot/initialize', methods=['POST'])
def initialize_chatbot():
    """챗봇 초기화 API"""
    global chatbot_ready, chatbot_initializing
    
    if chatbot_ready:
        return jsonify({'status': 'success', 'message': '챗봇이 이미 초기화되어 있습니다.'})
    
    if chatbot_initializing:
        return jsonify({'status': 'pending', 'message': '챗봇이 초기화 중입니다.'})
    
    # API 키 검증
    if not os.getenv('OPENAI_API_KEY'):
        return jsonify({
            'status': 'error',
            'message': 'OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.'
        }), 400
    
    # 백그라운드 스레드에서 초기화 실행
    def init_chatbot_thread():
        global chatbot_ready, chatbot_initializing
        try:
            logger.info("하이브리드 챗봇 초기화 시작")
            chatbot_initializing = True
            # 하이브리드 챗봇 초기화
            success = hybrid_chatbot.initialize_hybrid_chatbot()
            chatbot_ready = success
            chatbot_initializing = False
            logger.info(f"하이브리드 챗봇 초기화 완료: {success}")
        except Exception as e:
            logger.error(f"하이브리드 챗봇 초기화 중 오류 발생: {str(e)}")
            chatbot_ready = False
            chatbot_initializing = False
    
    threading.Thread(target=init_chatbot_thread).start()
    
    return jsonify({'status': 'initializing', 'message': '챗봇 초기화가 시작되었습니다.'})

@app.route('/api/chatbot/query', methods=['POST'])
def query_chatbot():
    """챗봇 질의 API"""
    global chatbot_ready
    
    if not chatbot_ready:
        return jsonify({
            'status': 'error', 
            'message': '챗봇이 초기화되지 않았습니다. 먼저 초기화를 진행해주세요.',
            'ready': chatbot_ready
        }), 400
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'status': 'error', 'message': '질문이 없습니다.'}), 400
        
        logger.info(f"챗봇 질의: {query}")
        
        # 하이브리드 챗봇 인스턴스로 질의 처리
        chatbot = hybrid_chatbot.get_hybrid_chatbot_instance()
        result = chatbot.get_answer(query)
        
        return jsonify({
            'status': 'success',
            'answer': result['answer'],
            'sources': result['sources']
        })
        
    except Exception as e:
        logger.error(f"챗봇 질의 처리 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/chatbot/reset', methods=['POST'])
def reset_chatbot():
    """챗봇 재설정 API"""
    global chatbot_ready, chatbot_initializing
    
    chatbot_ready = False
    chatbot_initializing = False
    
    # 싱글톤 인스턴스 초기화
    hybrid_chatbot._hybrid_chatbot_instance = None
    
    return jsonify({'status': 'success', 'message': '챗봇이 재설정되었습니다.'})

# AI 검색 API
@app.route('/api/ai-search/status')
def ai_search_status():
    """AI 검색 초기화 상태 확인"""
    global ai_search_ready, ai_search_initializing
    return jsonify({
        'ready': ai_search_ready,
        'initializing': ai_search_initializing
    })

@app.route('/api/ai-search/initialize', methods=['POST'])
def initialize_ai_search():
    """AI 검색 초기화"""
    global ai_search_ready, ai_search_initializing
    
    if ai_search_ready:
        return jsonify({'status': 'success', 'message': 'AI 검색이 이미 초기화되어 있습니다.'})
    
    if ai_search_initializing:
        return jsonify({'status': 'pending', 'message': 'AI 검색이 초기화 중입니다.'})
    
    # API 키 검증
    if not os.getenv('OPENAI_API_KEY'):
        return jsonify({
            'status': 'error',
            'message': 'OpenAI API 키가 설정되지 않았습니다.'
        }), 400
    
    # 백그라운드 스레드에서 초기화 실행
    def init_ai_search_thread():
        global ai_search_ready, ai_search_initializing
        try:
            logger.info("AI 검색 초기화 시작")
            ai_search_initializing = True
            success = ai_search.initialize_search_engine()
            ai_search_ready = success
            ai_search_initializing = False
            logger.info(f"AI 검색 초기화 완료: {success}")
        except Exception as e:
            logger.error(f"AI 검색 초기화 중 오류 발생: {str(e)}")
            ai_search_ready = False
            ai_search_initializing = False
    
    threading.Thread(target=init_ai_search_thread).start()
    
    return jsonify({'status': 'initializing', 'message': 'AI 검색 초기화가 시작되었습니다.'})

@app.route('/api/ai-search', methods=['POST'])
def ai_search_query():
    """AI 검색 실행"""
    global ai_search_ready
    
    if not ai_search_ready:
        # 자동 초기화 시도
        if not ai_search_initializing:
            initialize_ai_search()
        
        return jsonify({
            'status': 'error',
            'message': 'AI 검색이 초기화 중입니다. 잠시 후 다시 시도해주세요.'
        }), 503
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'status': 'error', 'message': '검색어가 없습니다.'}), 400
        
        logger.info(f"AI 검색 쿼리: {query}")
        
        # AI 검색 실행
        search_engine = ai_search.get_search_instance()
        result = search_engine.search(query)
        
        return jsonify({
            'status': 'success',
            'answer': result['answer'],
            'citations': result['citations']
        })
        
    except Exception as e:
        logger.error(f"AI 검색 처리 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/view/<source_type>/<filename>')
def view_document(source_type, filename):
    """내부 문서 보기 (새 창에서 열 때)"""
    try:
        if source_type == 'economy_terms':
            file_path = ECONOMY_TERMS_DIR / filename
        else:
            file_path = RECENT_CONTENTS_DIR / filename
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 백틱 문자를 미리 이스케이프 처리
        escaped_content = content.replace('`', r'\`')
            
        # 마크다운을 HTML로 변환하여 반환
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{filename.replace('.md', '')}</title>
            <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
        </head>
        <body class="font-sans p-8 max-w-4xl mx-auto">
            <div id="content" class="prose prose-lg"></div>
            <script>
                document.getElementById('content').innerHTML = marked.parse(`{escaped_content}`);
            </script>
        </body>
        </html>
        """
        return html_content
        
    except Exception as e:
        logger.error(f"문서 조회 오류: {str(e)}")
        return f"문서를 찾을 수 없습니다: {filename}", 404

if __name__ == '__main__':
    logger.info("서버 시작")
    app.run(host='127.0.0.1', port=5000, debug=True)