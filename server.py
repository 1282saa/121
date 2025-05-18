from flask import Flask, send_from_directory, jsonify, render_template, request
import os
import logging
from pathlib import Path
import mimetypes
import json
import threading
import time

# 통합 챗봇 모듈 import
import modules.unified_chatbot as unified_chatbot

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

# 서버 시작 시 챗봇 자동 초기화 함수
def initialize_chatbot_at_startup():
    global chatbot_ready, chatbot_initializing
    try:
        logger.info("서버 시작 시 통합 챗봇 자동 초기화 시작")
        chatbot_initializing = True
        success = unified_chatbot.initialize_unified_chatbot()
        chatbot_ready = success
        chatbot_initializing = False
        logger.info(f"통합 챗봇 자동 초기화 완료: {success}")
    except Exception as e:
        logger.error(f"통합 챗봇 자동 초기화 중 오류 발생: {str(e)}")
        chatbot_ready = False
        chatbot_initializing = False

# 서버 시작 시 백그라운드에서 챗봇 초기화 실행
threading.Thread(target=initialize_chatbot_at_startup).start()

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

# API 엔드포인트들
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

# 통합 챗봇 API
@app.route('/api/chatbot/status')
def chatbot_status():
    """챗봇 초기화 상태 확인"""
    global chatbot_ready, chatbot_initializing
    
    status_info = {
        'ready': chatbot_ready,
        'initializing': chatbot_initializing
    }
    
    if chatbot_ready:
        # 챗봇 인스턴스에서 상세 상태 정보 가져오기
        try:
            chatbot = unified_chatbot.get_unified_chatbot_instance()
            detailed_status = chatbot.get_status()
            status_info.update(detailed_status)
        except Exception as e:
            logger.error(f"챗봇 상세 상태 조회 오류: {str(e)}")
    
    return jsonify(status_info)

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
            logger.info("통합 챗봇 초기화 시작")
            chatbot_initializing = True
            success = unified_chatbot.initialize_unified_chatbot()
            chatbot_ready = success
            chatbot_initializing = False
            logger.info(f"통합 챗봇 초기화 완료: {success}")
        except Exception as e:
            logger.error(f"통합 챗봇 초기화 중 오류 발생: {str(e)}")
            chatbot_ready = False
            chatbot_initializing = False
    
    threading.Thread(target=init_chatbot_thread).start()
    
    return jsonify({'status': 'initializing', 'message': '챗봇 초기화가 시작되었습니다.'})

@app.route('/api/chatbot/query', methods=['POST'])
def query_chatbot():
    """통합 챗봇 질의 API"""
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
        
        logger.info(f"통합 챗봇 질의: {query}")
        
        # 통합 챗봇 인스턴스로 질의 처리
        chatbot = unified_chatbot.get_unified_chatbot_instance()
        result = chatbot.process_query(query)
        
        return jsonify({
            'status': 'success',
            'answer': result['answer'],
            'citations': result['citations'],
            'sources_used': result.get('sources_used', {})
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
    unified_chatbot._unified_chatbot_instance = None
    
    return jsonify({'status': 'success', 'message': '챗봇이 재설정되었습니다.'})

# AI 검색 API (통합 챗봇과 동일한 엔드포인트)
@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """AI 검색 API (통합 챗봇 사용)"""
    return query_chatbot()  # 동일한 로직 사용

@app.route('/api/ai-search/status')
def ai_search_status():
    """AI 검색 상태 API (통합 챗봇 상태와 동일)"""
    return chatbot_status()  # 동일한 로직 사용

@app.route('/api/ai-search/initialize', methods=['POST'])
def ai_search_initialize():
    """AI 검색 초기화 API (통합 챗봇 초기화와 동일)"""
    return initialize_chatbot()  # 동일한 로직 사용

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

# 환경 변수 확인 API
@app.route('/api/env/check')
def check_environment():
    """환경 변수 설정 상태 확인"""
    env_status = {
        'openai_api_key': bool(os.getenv('OPENAI_API_KEY')),
        'perplexity_api_key': bool(os.getenv('PERPLEXITY_API_KEY')),
        'required_keys': ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY'],
        'missing_keys': []
    }
    
    for key in env_status['required_keys']:
        if not os.getenv(key):
            env_status['missing_keys'].append(key)
    
    return jsonify(env_status)

if __name__ == '__main__':
    logger.info("통합 경제용 챗봇 서버 시작")
    
    # 환경 변수 확인 (Flask 컨텍스트 밖에서 직접 확인)
    env_status = {
        'openai_api_key': bool(os.getenv('OPENAI_API_KEY')),
        'perplexity_api_key': bool(os.getenv('PERPLEXITY_API_KEY'))
    }
    logger.info(f"환경 변수 상태: {env_status}")
    
    app.run(host='127.0.0.1', port=5000, debug=True) 