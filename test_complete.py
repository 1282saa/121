#!/usr/bin/env python3
"""완전한 기능 테스트"""

import requests
import time
import sys

def test_server():
    """서버 테스트"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 경제용 챗봇 기능 테스트 ===\n")
    
    # 서버 상태 확인
    try:
        response = requests.get(f"{base_url}/api/env/check", timeout=5)
    except:
        print("서버가 실행되지 않았습니다. ./run_local.sh를 먼저 실행하세요.")
        return
    
    # 1. 환경 확인
    print("1. 환경 설정 확인")
    print("-" * 30)
    response = requests.get(f"{base_url}/api/env/check")
    env_data = response.json()
    print(f"OpenAI API: {'✓' if env_data['openai_api_key'] else '✗'}")
    print(f"Perplexity API: {'✓' if env_data['perplexity_api_key'] else '✗'}")
    
    # 2. 콘텐츠 확인
    print("\n2. 콘텐츠 파일 확인")
    print("-" * 30)
    response = requests.get(f"{base_url}/api/economy_terms")
    terms = response.json()['files']
    print(f"경제 용어: {len(terms)}개")
    
    response = requests.get(f"{base_url}/api/recent_contents")
    contents = response.json()['files']
    print(f"최신 콘텐츠: {len(contents)}개")
    
    # 3. 챗봇 상태
    print("\n3. 챗봇 초기화 상태")
    print("-" * 30)
    response = requests.get(f"{base_url}/api/chatbot/status")
    status = response.json()
    print(f"준비 상태: {'✓' if status['ready'] else '✗'}")
    print(f"초기화 중: {'예' if status['initializing'] else '아니오'}")
    
    # 4. 챗봇 초기화
    if not status['ready'] and not status['initializing']:
        print("\n챗봇 초기화 시작...")
        response = requests.post(f"{base_url}/api/chatbot/initialize")
        print(response.json()['message'])
        
        # 초기화 대기
        for i in range(20):
            time.sleep(3)
            response = requests.get(f"{base_url}/api/chatbot/status")
            status = response.json()
            if status['ready']:
                print("챗봇 초기화 완료!")
                break
            print(f"대기 중... ({i+1}/20)")
    
    # 5. 질의 테스트
    response = requests.get(f"{base_url}/api/chatbot/status")
    if response.json()['ready']:
        print("\n4. 챗봇 질의 테스트")
        print("-" * 30)
        
        test_queries = [
            "경제용이 뭐야?",
            "최근 한국 경제 상황은 어때?",
            "ETF 투자 방법 알려줘"
        ]
        
        for query in test_queries:
            print(f"\n질문: {query}")
            response = requests.post(f"{base_url}/api/chatbot/query", 
                                   json={'query': query})
            if response.status_code == 200:
                result = response.json()
                answer = result['answer'][:150] + "..." if len(result['answer']) > 150 else result['answer']
                citations = len(result.get('citations', []))
                
                print(f"답변: {answer}")
                print(f"인용: {citations}개")
            else:
                print(f"오류: {response.status_code}")
    
    # 6. 스트리밍 테스트
    print("\n5. 스트리밍 질의 테스트")
    print("-" * 30)
    response = requests.get(f"{base_url}/api/chatbot/stream?query=비트코인 투자는 어떤가요?", stream=True)
    print("스트리밍 응답: ", end="")
    for line in response.iter_lines():
        if line:
            try:
                data = line.decode('utf-8')
                if data.startswith('data: '):
                    print(".", end="", flush=True)
            except:
                pass
    print(" 완료!")
    
    # 7. 언박싱 비디오
    print("\n6. 언박싱 비디오 테스트")
    print("-" * 30)
    response = requests.post(f"{base_url}/api/get-unboxing-video")
    if response.status_code == 200:
        data = response.json()
        print(f"비디오 URL: {data.get('video_url', 'N/A')}")
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("브라우저에서 http://127.0.0.1:5000 으로 접속하세요.")

if __name__ == "__main__":
    test_server()