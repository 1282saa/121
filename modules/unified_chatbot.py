import os
import logging
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import json
import asyncio
import concurrent.futures
import requests
import markdown
from bs4 import BeautifulSoup

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.schema.document import Document
from langchain.prompts import ChatPromptTemplate

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger('unified_chatbot')
logger.setLevel(logging.INFO)

# 디렉토리 설정
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
ECONOMY_TERMS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/economy_terms")
RECENT_CONTENTS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/recent_contents_final")

class UnifiedChatbot:
    """GPT와 Perplexity API를 통합한 챗봇 시스템"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.docs = []
        self.vectorstore = None
        self.retriever = None
        self.file_paths = {}
        
        # 초기화 상태
        self.initialized = False
        self.rag_initialized = False
        self.perplexity_initialized = False
        
    def load_documents(self):
        """내부 문서 로드"""
        logger.info("문서 로드 시작")
        
        # 경제 용어 및 최신 콘텐츠 로드
        all_files = list(ECONOMY_TERMS_DIR.glob("*.md")) + list(RECENT_CONTENTS_DIR.glob("*.md"))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 메타데이터 추출
                file_name = file_path.name
                title = file_name.replace(".md", "")
                source_type = "economy_terms" if str(ECONOMY_TERMS_DIR) in str(file_path) else "recent_contents"
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(file_path),
                        "title": title,
                        "file_name": file_name,
                        "source_type": source_type
                    }
                )
                
                self.docs.append(doc)
                self.file_paths[file_name] = file_path
                
            except Exception as e:
                logger.error(f"파일 로드 오류: {file_path}, {str(e)}")
        
        logger.info(f"총 {len(self.docs)}개 문서 로드 완료")
        
    def create_rag_index(self):
        """RAG 인덱스 생성"""
        if not self.docs:
            raise ValueError("문서가 로드되지 않았습니다")
            
        logger.info("RAG 인덱스 생성 시작")
        
        # RecursiveCharacterTextSplitter로 청킹 (토큰 제한 방지)
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # 더 작은 청크 크기
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        chunks = []
        for doc in self.docs:
            # 모든 문서를 청크로 분할
            doc_chunks = text_splitter.create_documents(
                texts=[doc.page_content],
                metadatas=[doc.metadata]
            )
            chunks.extend(doc_chunks)
        
        logger.info(f"총 {len(chunks)}개의 청크 생성")
        
        # 벡터스토어를 배치로 생성
        batch_size = 50  # 한 번에 처리할 청크 수
        
        # 빈 벡터스토어로 시작
        self.vectorstore = None
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            logger.info(f"처리 중: {i}/{len(chunks)}")
            
            if self.vectorstore is None:
                # 첫 배치로 벡터스토어 생성
                self.vectorstore = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    collection_name="unified_collection"
                )
            else:
                # 기존 벡터스토어에 추가
                self.vectorstore.add_documents(batch)
        
        # Ensemble retriever 생성 (Semantic + BM25)
        vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        bm25_retriever = BM25Retriever.from_documents(chunks, k=3)
        
        self.retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.6, 0.4]
        )
        
        self.rag_initialized = True
        logger.info("RAG 인덱스 생성 완료")
        
    def check_perplexity_api(self):
        """Perplexity API 연결 확인"""
        if not self.perplexity_api_key:
            logger.warning("Perplexity API 키가 없습니다")
            self.perplexity_initialized = False
            return False
            
        try:
            # API 연결 테스트
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            # 간단한 테스트 쿼리
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=5
            )
            
            self.perplexity_initialized = response.status_code == 200
            logger.info(f"Perplexity API 연결 확인: {self.perplexity_initialized}")
            return self.perplexity_initialized
            
        except Exception as e:
            logger.error(f"Perplexity API 연결 확인 실패: {str(e)}")
            self.perplexity_initialized = False
            return False
    
    def search_with_perplexity(self, query: str):
        """Perplexity API로 실시간 웹 검색"""
        if not self.perplexity_initialized:
            logger.warning("Perplexity API가 초기화되지 않았습니다")
            return {
                "success": False,
                "answer": "웹 검색 기능을 사용할 수 없습니다.",
                "citations": []
            }
            
        try:
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 최신 한국 경제 정보를 제공하는 전문가입니다. 정확한 정보와 함께 출처를 제공하세요."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.2,
                "return_citations": True,
                "return_related_questions": True
            }
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200:
                # 응답에서 정보 추출
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                # Perplexity API는 citations를 별도로 제공하지 않을 수 있음
                citations = []
                
                return {
                    "success": True,
                    "answer": answer,
                    "citations": citations
                }
            else:
                logger.error(f"Perplexity API 오류: {result}")
                return {
                    "success": False,
                    "answer": "웹 검색 중 오류가 발생했습니다.",
                    "citations": []
                }
                
        except Exception as e:
            logger.error(f"Perplexity 검색 오류: {str(e)}")
            return {
                "success": False,
                "answer": f"검색 중 오류 발생: {str(e)}",
                "citations": []
            }
    
    def search_internal_documents(self, query: str):
        """내부 문서에서 관련 정보 검색"""
        if not self.rag_initialized:
            return []
            
        try:
            docs = self.retriever.get_relevant_documents(query)
            return docs
        except Exception as e:
            logger.error(f"내부 문서 검색 오류: {str(e)}")
            return []
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """사용자 질의 처리 (RAG + Perplexity 통합)"""
        if not self.initialized:
            return {
                "answer": "챗봇이 아직 초기화되지 않았습니다.",
                "citations": [],
                "sources_used": {"internal": False, "web": False}
            }
        
        # 1. 내부 문서 검색
        internal_docs = self.search_internal_documents(query)
        
        # 2. Perplexity로 웹 검색
        web_search_result = self.search_with_perplexity(query)
        
        # 3. 결과 통합
        sources_used = {
            "internal": len(internal_docs) > 0,
            "web": web_search_result.get("success", False)
        }
        
        # 프롬프트 구성
        context_parts = []
        citations = []
        
        # 내부 문서 정보 추가
        if internal_docs:
            context_parts.append("=== 내부 문서 정보 ===")
            for i, doc in enumerate(internal_docs):
                context_parts.append(f"\n[내부문서 {i+1}] {doc.metadata.get('title')}")
                context_parts.append(doc.page_content[:500])
                
                # 문서의 실제 인용 구간 저장
                quoted_content = doc.page_content.strip()[:150]  # 처음 150자
                citations.append({
                    "type": "internal",
                    "title": doc.metadata.get('title'),
                    "source": doc.metadata.get('source'),
                    "file_name": doc.metadata.get('file_name'),
                    "source_type": doc.metadata.get('source_type'),
                    "quoted_text": quoted_content  # 인용된 텍스트 구간
                })
        
        # 웹 검색 정보 추가
        if web_search_result.get("success") and web_search_result.get("answer"):
            context_parts.append("\n=== 최신 웹 정보 ===")
            context_parts.append(web_search_result["answer"])
            
            # 웹 출처 추가
            for citation in web_search_result.get("citations", []):
                if isinstance(citation, dict):
                    citations.append({
                        "type": "web",
                        "title": citation.get("title", "웹 자료"),
                        "url": citation.get("url", ""),
                        "source": citation.get("name", "웹")
                    })
                elif isinstance(citation, str):
                    citations.append({
                        "type": "web",
                        "title": citation,
                        "url": "",
                        "source": "웹"
                    })
        
        # GPT로 최종 답변 생성
        if context_parts:
            # 컨텍스트가 있는 경우
            prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 한국 경제 정보를 제공하는 전문가입니다. 
                제공된 정보를 바탕으로 사용자의 질문에 답변하세요.
                내부 문서와 최신 웹 정보를 적절히 종합하여 답변하세요.
                답변 시 출처를 명확히 밝히세요."""),
                ("human", "{context}\n\n질문: {query}")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "context": "\n".join(context_parts),
                "query": query
            })
            
            answer = response.content
        else:
            # 컨텍스트가 없는 경우 (일반 대화)
            prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 친절한 한국어 대화 AI입니다. 
                경제 관련 전문 지식을 가지고 있지만, 일반적인 대화도 자연스럽게 나눌 수 있습니다."""),
                ("human", "{query}")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({"query": query})
            answer = response.content
        
        return {
            "answer": answer,
            "citations": citations,
            "sources_used": sources_used
        }
    
    def get_status(self):
        """챗봇 상태 정보 반환"""
        return {
            "initialized": self.initialized,
            "rag_initialized": self.rag_initialized,
            "perplexity_initialized": self.perplexity_initialized,
            "document_count": len(self.docs),
            "api_keys": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "perplexity": bool(os.getenv("PERPLEXITY_API_KEY"))
            }
        }

# 싱글톤 인스턴스
_unified_chatbot_instance = None

def get_unified_chatbot_instance():
    """통합 챗봇 싱글톤 인스턴스 반환"""
    global _unified_chatbot_instance
    
    if _unified_chatbot_instance is None:
        _unified_chatbot_instance = UnifiedChatbot()
    
    return _unified_chatbot_instance

def initialize_unified_chatbot():
    """통합 챗봇 초기화"""
    try:
        logger.info("통합 챗봇 초기화 시작")
        
        chatbot = get_unified_chatbot_instance()
        
        # 문서 로드
        chatbot.load_documents()
        
        # RAG 인덱스 생성
        chatbot.create_rag_index()
        
        # Perplexity API 확인
        chatbot.check_perplexity_api()
        
        # 초기화 완료
        chatbot.initialized = True
        logger.info("통합 챗봇 초기화 완료")
        
        return True
        
    except Exception as e:
        logger.error(f"통합 챗봇 초기화 오류: {str(e)}")
        return False