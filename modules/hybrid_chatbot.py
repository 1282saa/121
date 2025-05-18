import os
import requests
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
import logging
from modules.rag_chatbot import RAGChatbot, get_chatbot_instance
from langchain.schema.document import Document

# 환경 변수 로드
load_dotenv()

# 로깅 설정
import sys
hybrid_logger = logging.getLogger('hybrid_chatbot')
hybrid_logger.setLevel(logging.INFO)

# 기존 핸들러가 있다면 제거
for handler in hybrid_logger.handlers[:]:
    hybrid_logger.removeHandler(handler)

# 파일 핸들러 추가
file_handler = logging.FileHandler('logs/hybrid_chatbot.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
hybrid_logger.addHandler(file_handler)

# 콘솔 핸들러 추가 (디버깅용)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
hybrid_logger.addHandler(console_handler)

logger = hybrid_logger

class HybridChatbot(RAGChatbot):
    """
    RAG + Perplexity API를 결합한 하이브리드 챗봇
    """
    def __init__(self):
        super().__init__()
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        if not self.perplexity_api_key:
            logger.warning("PERPLEXITY_API_KEY가 설정되지 않았습니다. 실시간 검색 기능이 제한됩니다.")
    
    def search_with_perplexity(self, query: str) -> Dict[str, Any]:
        """Perplexity API로 실시간 검색"""
        if not self.perplexity_api_key:
            return {"content": None, "error": "Perplexity API 키가 설정되지 않았습니다."}
        
        url = "https://api.perplexity.ai/chat/completions"
        
        # 경제 관련 검색 쿼리 최적화
        optimized_query = f"{query} 한국 경제 금융 최신 뉴스"
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",  # 온라인 검색 모델
            "messages": [
                {
                    "role": "system", 
                    "content": "당신은 한국 경제 전문가입니다. 최신 경제 동향과 금융 정보를 정확하게 한국어로 제공해주세요."
                },
                {"role": "user", "content": optimized_query}
            ],
            "max_tokens": 1000,
            "temperature": 0.3,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            logger.info(f"Perplexity 검색 성공: {query[:30]}...")
            return {"content": content, "error": None}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API 요청 실패: {str(e)}")
            return {"content": None, "error": str(e)}
    
    def _is_recent_info_needed(self, query: str) -> bool:
        """최신 정보가 필요한 질문인지 판단"""
        recent_keywords = [
            "최근", "현재", "오늘", "지금", "최신", "요즘", 
            "이번", "어제", "내일", "주가", "환율", "시세",
            "동향", "전망", "예측", "실시간", "속보"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in recent_keywords)
    
    def _is_economy_related(self, query: str) -> bool:
        """경제 관련 질문인지 판단"""
        economy_keywords = [
            "경제", "금융", "주식", "투자", "채권", "환율", 
            "금리", "인플레이션", "디플레이션", "GDP", "물가",
            "부동산", "펀드", "예금", "적금", "보험", "연금",
            "코스피", "코스닥", "ETF", "리츠", "은행", "증권"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in economy_keywords)
    
    def _combine_contexts(self, rag_docs: List[Document], perplexity_result: str) -> str:
        """RAG 문서와 Perplexity 결과 결합"""
        context_parts = []
        
        # RAG 문서 내용
        if rag_docs:
            context_parts.append("=== 내부 지식 베이스 ===")
            for i, doc in enumerate(rag_docs[:3]):  # 상위 3개만
                context_parts.append(f"\n[문서 {i+1}: {doc.metadata.get('title', 'Unknown')}]")
                context_parts.append(doc.page_content[:500] + "...")
        
        # Perplexity 검색 결과
        if perplexity_result:
            context_parts.append("\n\n=== 실시간 웹 검색 결과 ===")
            context_parts.append(perplexity_result)
        
        return "\n".join(context_parts)
    
    def get_answer(self, query: str) -> Dict[str, Any]:
        """하이브리드 답변 생성"""
        logger.info(f"하이브리드 질문 처리: {query}")
        
        # 1. 경제 관련 질문인지 확인
        if not self._is_economy_related(query):
            return {
                "answer": "죄송하지만 경제, 투자, 금융 관련 질문만 답변할 수 있어용~ 🦖 다른 경제 관련 궁금한 점이 있으시면 언제든 물어보세용!",
                "sources": {"type": "filtered", "reason": "경제 무관"}
            }
        
        # 2. 기존 RAG로 문서 검색
        rag_docs = self.multiquery_retriever.get_relevant_documents(query)
        
        # 3. 최신 정보가 필요하거나 RAG 결과가 부족한 경우
        need_web_search = (
            self._is_recent_info_needed(query) or 
            len(rag_docs) < 2 or
            not rag_docs
        )
        
        perplexity_result = None
        if need_web_search and self.perplexity_api_key:
            search_result = self.search_with_perplexity(query)
            perplexity_result = search_result.get("content")
        
        # 4. 컨텍스트 결합
        if perplexity_result:
            combined_context = self._combine_contexts(rag_docs, perplexity_result)
            
            # 결합된 컨텍스트로 최종 답변 생성
            prompt = f"""
            당신은 경제 전문 AI 챗봇 '경제용'입니다. 
            제공된 내부 지식과 실시간 검색 결과를 바탕으로 정확하고 친절하게 답변해주세요.
            가끔 '~용' 같은 귀여운 말투를 사용하세요.
            
            컨텍스트:
            {combined_context}
            
            질문: {query}
            
            답변:
            """
            
            response = self.llm.invoke(prompt)
            answer = response.content
            
            sources = {
                "type": "hybrid",
                "internal_docs": [
                    {
                        "title": doc.metadata.get("title", "Unknown"),
                        "source_type": doc.metadata.get("source_type", "")
                    } for doc in rag_docs[:3]
                ],
                "web_search": "Perplexity API 실시간 검색 포함"
            }
        else:
            # RAG만으로 답변 생성
            answer_result = super().get_answer(query)
            answer = answer_result["answer"]
            sources = {
                "type": "rag_only",
                "internal_docs": answer_result["related_docs"]
            }
        
        return {
            "answer": answer,
            "sources": sources
        }

# 싱글톤 인스턴스
_hybrid_chatbot_instance = None

def get_hybrid_chatbot_instance():
    """하이브리드 챗봇 싱글톤 인스턴스 반환"""
    global _hybrid_chatbot_instance
    
    if _hybrid_chatbot_instance is None:
        _hybrid_chatbot_instance = HybridChatbot()
        
    return _hybrid_chatbot_instance

def initialize_hybrid_chatbot():
    """하이브리드 챗봇 초기화"""
    try:
        chatbot = get_hybrid_chatbot_instance()
        chatbot.load_documents()
        chatbot.create_chunks_and_index()
        chatbot.setup_rag_chain()
        logger.info("하이브리드 챗봇 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"하이브리드 챗봇 초기화 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    # 테스트용 코드
    import json
    
    # 초기화
    initialize_hybrid_chatbot()
    chatbot = get_hybrid_chatbot_instance()
    
    # 테스트 질문들
    test_queries = [
        "ETF가 무엇인가요?",  # 기본 RAG 질문
        "오늘 코스피 지수는 어떻게 되나요?",  # 실시간 정보 필요
        "최근 한국 경제 동향은 어떤가요?",  # 최신 정보 필요
    ]
    
    for query in test_queries:
        print(f"\n질문: {query}")
        result = chatbot.get_answer(query)
        print(f"답변: {result['answer'][:100]}...")
        print(f"출처: {result['sources']['type']}")