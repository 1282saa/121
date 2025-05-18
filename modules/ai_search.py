import os
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
import logging
import requests
from bs4 import BeautifulSoup
import markdown
import asyncio
import concurrent.futures

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.schema.document import Document
from langchain.prompts import ChatPromptTemplate

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger('ai_search')
logger.setLevel(logging.INFO)

# 디렉토리 설정
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
ECONOMY_TERMS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/economy_terms")
RECENT_CONTENTS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/recent_contents_final")

class PerplexityStyleSearch:
    """Perplexity 스타일의 AI 검색 시스템"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.docs = []
        self.vectorstore = None
        self.retriever = None
        self.file_paths = {}
        
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
                
                # 마크다운을 텍스트로 변환
                html_content = markdown.markdown(content)
                text_content = BeautifulSoup(html_content, "html.parser").get_text(separator="\n")
                
                doc = Document(
                    page_content=text_content,
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
    
    def create_search_index(self):
        """검색 인덱스 생성"""
        if not self.docs:
            raise ValueError("문서가 로드되지 않았습니다")
            
        # SemanticChunker로 청킹
        text_splitter = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type="percentile"
        )
        
        chunks = text_splitter.split_documents(self.docs)
        
        # 벡터 스토어 생성
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name="economy_knowledge_search"
        )
        
        # BM25 리트리버 생성
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 10
        
        # 앙상블 리트리버
        self.retriever = EnsembleRetriever(
            retrievers=[self.vectorstore.as_retriever(search_kwargs={"k": 10}), bm25_retriever],
            weights=[0.7, 0.3]
        )
        
        logger.info("검색 인덱스 생성 완료")
    
    def search_perplexity(self, query: str) -> Dict[str, Any]:
        """Perplexity API로 웹 검색"""
        if not self.perplexity_api_key:
            return {"content": None, "citations": []}
            
        url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 한국 경제 전문가입니다. 웹에서 검색한 정보를 바탕으로 정확하고 최신의 경제 정보를 한국어로 제공하세요. 출처를 반드시 포함하세요."
                },
                {"role": "user", "content": f"{query} (한국 경제 관련)"}
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
            "return_citations": True,
            "search_domain_filter": ["naver.com", "news.naver.com", "finance.naver.com", "www.sedaily.com", "www.hankyung.com", "www.mk.co.kr", "www.fnnews.com"],
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
            
            # 인용 정보 추출
            citations = []
            if 'citations' in result:
                citations = result['citations']
            
            return {"content": content, "citations": citations}
            
        except Exception as e:
            logger.error(f"Perplexity API 오류: {str(e)}")
            return {"content": None, "citations": []}
    
    def search_internal_docs(self, query: str) -> List[Document]:
        """내부 문서 검색"""
        if not self.retriever:
            return []
            
        try:
            # 쿼리 확장을 위한 MultiQueryRetriever 사용
            multiquery_retriever = MultiQueryRetriever.from_llm(
                retriever=self.retriever,
                llm=self.llm
            )
            
            docs = multiquery_retriever.get_relevant_documents(query)
            return docs[:5]  # 상위 5개만 반환
            
        except Exception as e:
            logger.error(f"내부 문서 검색 오류: {str(e)}")
            return []
    
    def generate_final_answer(self, query: str, internal_docs: List[Document], perplexity_result: Dict[str, Any]) -> Dict[str, Any]:
        """최종 답변 생성"""
        
        # 컨텍스트 준비
        context_parts = []
        citations = []
        
        # 내부 문서 컨텍스트
        if internal_docs:
            for i, doc in enumerate(internal_docs):
                cite_num = len(citations) + 1
                citations.append({
                    "number": cite_num,
                    "type": "internal",
                    "title": doc.metadata.get("title", "Unknown"),
                    "file_name": doc.metadata.get("file_name", ""),
                    "source_type": doc.metadata.get("source_type", ""),
                    "content": doc.page_content[:200] + "..."
                })
                context_parts.append(f"[{cite_num}] {doc.page_content}")
        
        # Perplexity 검색 결과
        if perplexity_result.get("content"):
            cite_num = len(citations) + 1
            citations.append({
                "number": cite_num,
                "type": "web",
                "title": "웹 검색 결과",
                "content": perplexity_result["content"][:200] + "...",
                "web_citations": perplexity_result.get("citations", [])
            })
            context_parts.append(f"[{cite_num}] {perplexity_result['content']}")
        
        # 문맥 결합
        combined_context = "\n\n".join(context_parts)
        
        # 프롬프트 템플릿
        template = """
        당신은 한국 경제 전문 AI 검색 엔진입니다. 
        제공된 정보를 바탕으로 사용자의 질문에 대해 정확하고 포괄적인 답변을 제공하세요.
        
        **중요한 지침:**
        1. 답변에는 반드시 출처 표시([1], [2] 등)를 포함하세요
        2. 내부 문서의 정보를 우선적으로 활용하고, 웹 검색 결과로 보완하세요
        3. 숫자나 데이터를 언급할 때는 반드시 출처를 명시하세요
        4. 읽기 쉽도록 문단을 나누고 중요한 내용은 **강조**하세요
        5. 경제 전문 용어는 쉽게 설명하세요
        
        컨텍스트:
        {context}
        
        질문: {query}
        
        답변:
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        response = self.llm.invoke(prompt.format(context=combined_context, query=query))
        
        return {
            "answer": response.content,
            "citations": citations
        }
    
    def search(self, query: str) -> Dict[str, Any]:
        """통합 검색 실행"""
        logger.info(f"검색 쿼리: {query}")
        
        # 병렬 처리로 내부 문서 검색과 웹 검색 동시 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 내부 문서 검색
            internal_future = executor.submit(self.search_internal_docs, query)
            
            # Perplexity 웹 검색
            perplexity_future = executor.submit(self.search_perplexity, query)
            
            # 결과 수집
            internal_docs = internal_future.result()
            perplexity_result = perplexity_future.result()
        
        # 최종 답변 생성
        result = self.generate_final_answer(query, internal_docs, perplexity_result)
        
        return result

# 싱글톤 인스턴스
_search_instance = None

def get_search_instance():
    """검색 엔진 싱글톤 인스턴스 반환"""
    global _search_instance
    
    if _search_instance is None:
        _search_instance = PerplexityStyleSearch()
        
    return _search_instance

def initialize_search_engine():
    """검색 엔진 초기화"""
    try:
        search = get_search_instance()
        search.load_documents()
        search.create_search_index()
        logger.info("AI 검색 엔진 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"AI 검색 엔진 초기화 오류: {str(e)}")
        return False

if __name__ == "__main__":
    # 테스트
    import json
    
    initialize_search_engine()
    search = get_search_instance()
    
    test_query = "최근 한국 증시 동향은 어떤가요?"
    result = search.search(test_query)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))