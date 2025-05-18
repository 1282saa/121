import os
import glob
import re
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import logging
from bs4 import BeautifulSoup
import markdown
import json

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.schema.document import Document
from langchain.schema.retriever import BaseRetriever
from langchain.schema.runnable import Runnable, RunnablePassthrough
from langchain.prompts.prompt import PromptTemplate

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/rag_chatbot.log'
)
logger = logging.getLogger(__name__)

# 디렉토리 설정
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
ECONOMY_TERMS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/economy_terms")
RECENT_CONTENTS_DIR = Path("/Users/yeong-gwang/Desktop/work/서울경제신문/경제용/recent_contents_final")

# 폴더가 없는 경우 생성
os.makedirs(ECONOMY_TERMS_DIR, exist_ok=True)
os.makedirs(RECENT_CONTENTS_DIR, exist_ok=True)

class RankingRetriever(BaseRetriever):
    """
    문서들을 리랭킹하는 커스텀 리트리버
    """
    
    def __init__(self, base_retriever, reranker_model):
        super().__init__()
        self.base_retriever = base_retriever
        self.reranker_model = reranker_model
        
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        # 기본 리트리버로 문서 가져오기
        docs = self.base_retriever.get_relevant_documents(query)
        
        if not docs:
            return []
        
        # 재랭킹을 위한 프롬프트 작성
        reranking_template = """
        당신은 검색 엔진의 재랭킹 시스템입니다. 아래 문서 목록에서 질문과 가장 관련성이 높은 문서를 선택해야 합니다.
        
        질문: {query}
        
        문서 목록:
        {doc_list}
        
        문서의 관련성을 0부터 10까지의 점수로 평가해주세요. 형식은 다음과 같아야 합니다:
        
        평가:
        문서1: 점수
        문서2: 점수
        ...
        문서N: 점수
        """
        
        # 문서 목록 준비
        doc_texts = []
        for i, doc in enumerate(docs):
            doc_texts.append(f"문서{i+1}: {doc.page_content[:200]}...")
        
        doc_list_text = "\n\n".join(doc_texts)
        
        # 재랭킹 실행
        reranking_prompt = PromptTemplate(
            template=reranking_template,
            input_variables=["query", "doc_list"]
        )
        
        result = self.reranker_model.invoke(
            reranking_prompt.format(query=query, doc_list=doc_list_text)
        )
        
        # 결과에서 점수 추출
        scores = {}
        for i, doc in enumerate(docs):
            match = re.search(f"문서{i+1}:\\s*(\\d+)", result)
            if match:
                scores[i] = int(match.group(1))
            else:
                scores[i] = 0
        
        # 점수에 따라 정렬
        sorted_docs = [docs[i] for i in sorted(scores.keys(), key=lambda x: scores[x], reverse=True)]
        
        # 상위 3개 문서만 반환
        return sorted_docs[:3]

class RAGChatbot:
    """
    RAG 기반 챗봇 클래스
    """
    
    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.bm25_retriever = None
        self.ensemble_retriever = None
        self.chain = None
        self.docs = []
        self.file_paths = {}
        
        # OpenAI API 키 확인
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
        # 임베딩 초기화
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # LLM 초기화 (비용 효율적인 모델 사용)
        self.llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.3)
        self.reranker_model = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
        
    def load_documents(self):
        """문서 로드 및 전처리"""
        logger.info("문서 로드 시작")
        
        # 경제 용어 문서 로드
        economy_terms_files = glob.glob(str(ECONOMY_TERMS_DIR / "*.md"))
        
        # 최신 콘텐츠 문서 로드
        recent_contents_files = glob.glob(str(RECENT_CONTENTS_DIR / "*.md"))
        
        all_files = economy_terms_files + recent_contents_files
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 파일명에서 제목 추출
                file_name = os.path.basename(file_path)
                
                # 마크다운을 HTML로 변환
                html_content = markdown.markdown(content)
                
                # HTML 태그 제거
                soup = BeautifulSoup(html_content, "html.parser")
                text_content = soup.get_text(separator="\n")
                
                # 문서 메타데이터 설정
                source_type = "economy_terms" if file_path in economy_terms_files else "recent_contents"
                
                # 문서 추가
                doc = Document(
                    page_content=text_content,
                    metadata={
                        "source": file_path,
                        "source_type": source_type,
                        "title": file_name.replace(".md", "")
                    }
                )
                
                self.docs.append(doc)
                self.file_paths[file_name] = file_path
                
            except Exception as e:
                logger.error(f"파일 로드 중 오류 발생: {file_path}, 에러: {str(e)}")
        
        logger.info(f"총 {len(self.docs)}개 문서 로드 완료")
        return self.docs
    
    def create_chunks_and_index(self):
        """문서 청킹 및 인덱싱"""
        if not self.docs:
            raise ValueError("문서가 로드되지 않았습니다. load_documents()를 먼저 호출하세요.")
            
        logger.info("문서 청킹 및 인덱싱 시작")
        
        # SemanticChunker를 사용한 청킹
        text_splitter = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type="percentile"
        )
        
        chunks = text_splitter.split_documents(self.docs)
        logger.info(f"총 {len(chunks)}개 청크 생성 완료")
        
        # Chroma 벡터스토어 생성
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name="economy_knowledge"
        )
        
        # BM25 리트리버 생성
        self.bm25_retriever = BM25Retriever.from_documents(chunks)
        self.bm25_retriever.k = 5
        
        # 앙상블 리트리버 생성
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.vectorstore.as_retriever(search_kwargs={"k": 5}), self.bm25_retriever],
            weights=[0.7, 0.3]
        )
        
        # 리랭킹 리트리버 생성
        self.ranking_retriever = RankingRetriever(
            base_retriever=self.ensemble_retriever,
            reranker_model=self.reranker_model
        )
        
        # 쿼리 확장 리트리버 생성
        self.multiquery_retriever = MultiQueryRetriever.from_llm(
            retriever=self.ranking_retriever,
            llm=self.llm
        )
        
        logger.info("인덱싱 완료")
        return self.multiquery_retriever
    
    def setup_rag_chain(self):
        """RAG 체인 설정"""
        if not self.multiquery_retriever:
            raise ValueError("리트리버가 생성되지 않았습니다. create_chunks_and_index()를 먼저 호출하세요.")
            
        # 프롬프트 템플릿 설정
        template = """
        당신은 경제 전문 AI 챗봇 '경제용'입니다. 한국의 경제, 투자, 금융에 관한 질문에 친절하고 정확하게 답변해야 합니다.
        항상 존댓말을 사용하고, 가끔 '~용' 같은 귀여운 말투를 섞어서 사용하세요.
        
        제공된 문서 내용을 바탕으로 질문에 답변해주세요. 문서에 없는 내용을 지어내지 마세요.
        답변할 수 없거나 관련 내용이 없는 경우 솔직하게 모른다고 말하고, 대신 경제, 투자, 금융에 관한 다른 주제를 제안해주세요.
        
        문서:
        {context}
        
        질문: {question}
        
        답변:
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 관련 문서 검색 및 형식화 함수
        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])
        
        # RAG 체인 생성
        self.chain = (
            {
                "context": self.multiquery_retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt
            | self.llm
        )
        
        logger.info("RAG 체인 설정 완료")
        return self.chain
    
    def get_answer(self, query: str) -> Dict[str, Any]:
        """질문에 대한 답변 생성"""
        if not self.chain:
            raise ValueError("RAG 체인이 설정되지 않았습니다. setup_rag_chain()을 먼저 호출하세요.")
            
        logger.info(f"질문 입력: {query}")
        
        # 질문에 대한 관련 문서 검색
        retrieved_docs = self.multiquery_retriever.get_relevant_documents(query)
        
        # 답변 생성
        response = self.chain.invoke(query)
        answer = response.content
        
        # 관련 문서 정보 추출
        related_docs = []
        for doc in retrieved_docs[:3]:  # 상위 3개 문서만 표시
            file_path = doc.metadata.get("source", "")
            file_name = os.path.basename(file_path)
            title = doc.metadata.get("title", file_name.replace(".md", ""))
            source_type = doc.metadata.get("source_type", "")
            
            related_docs.append({
                "title": title,
                "file_name": file_name,
                "source_type": source_type
            })
        
        result = {
            "answer": answer,
            "related_docs": related_docs
        }
        
        logger.info(f"답변 생성 완료: {answer[:50]}...")
        return result

# 싱글톤 인스턴스
_chatbot_instance = None

def get_chatbot_instance():
    """챗봇 싱글톤 인스턴스 반환"""
    global _chatbot_instance
    
    if _chatbot_instance is None:
        _chatbot_instance = RAGChatbot()
        
    return _chatbot_instance

def initialize_chatbot():
    """챗봇 초기화 및 설정"""
    try:
        chatbot = get_chatbot_instance()
        chatbot.load_documents()
        chatbot.create_chunks_and_index()
        chatbot.setup_rag_chain()
        return True
    except Exception as e:
        logger.error(f"챗봇 초기화 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    # 테스트용 코드
    initialize_chatbot()
    chatbot = get_chatbot_instance()
    result = chatbot.get_answer("ETF가 무엇인가요?")
    print(json.dumps(result, ensure_ascii=False, indent=2)) 