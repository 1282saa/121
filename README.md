# 경제용 챗봇

경제 용어와 콘텐츠를 쉽게 접근할 수 있는 웹 인터페이스와 RAG(Retrieval-Augmented Generation) 기반 챗봇을 제공하는 프로젝트입니다.

## 주요 기능

1. **RAG 기반 챗봇**: 경제 용어와 콘텐츠를 기반으로 질문에 답변하는 AI 챗봇
   - 사용자의 질문에 대해 관련 경제 문서를 검색하고 답변 생성
   - 관련 문서 링크 제공으로 상세 정보 확인 가능
2. **경제 용어 사전**: 다양한 경제 용어에 대한 설명 제공
3. **최신 경제 콘텐츠**: 최신 경제 트렌드와 뉴스 제공

## 기술 스택

- **프론트엔드**: HTML, CSS, JavaScript
- **백엔드**: Python, Flask
- **RAG 챗봇**:
  - **벡터 데이터베이스**: Chroma
  - **임베딩**: OpenAI (text-embedding-3-small)
  - **언어 모델**: OpenAI (gpt-3.5-turbo)
  - **청킹**: SemanticChunker
  - **검색 기법**: BM25 + 벡터 검색 앙상블
  - **리랭킹**: LLM 기반 재랭킹
  - **쿼리 확장**: MultiQueryRetriever
  - **프레임워크**: LangChain

## 설치 및 실행 방법

### 사전 요구사항

- Python 3.8 이상
- OpenAI API 키

### 설치 단계

1. 저장소 클론하기

   ```bash
   git clone https://github.com/username/경제용챗봇.git
   cd 경제용챗봇
   ```

2. 의존성 패키지 설치

   ```bash
   pip install -r requirements.txt
   ```

3. OpenAI API 키 설정

   ```bash
   cp .env.example .env
   # .env 파일을 열어 API 키 입력
   # OPENAI_API_KEY=your_api_key_here
   ```

4. 서버 실행

   ```bash
   python server.py
   ```

5. 웹 브라우저에서 접속
   - http://localhost:5000 으로 접속

## 프로젝트 구조

```
경제용챗봇/
├── static/                # 정적 파일들
│   ├── css/               # CSS 파일들
│   │   └── styles.css
│   └── js/                # JavaScript 파일들
│       ├── app.js
│       ├── chatbot.js
│       ├── content-data.js
│       └── content-manager.js
├── data/                  # 데이터 폴더
│   ├── economy_terms/     # 경제 용어 마크다운 파일들
│   └── recent_contents/   # 최신 콘텐츠 마크다운 파일들
├── modules/               # Python 모듈 폴더
│   └── rag_chatbot.py     # RAG 챗봇 클래스
├── ui.html                # 메인 HTML 파일
├── server.py              # Flask 서버
├── requirements.txt       # 의존성 패키지 목록
├── .env.example           # 환경 변수 예시 파일
├── .gitignore             # Git 무시 파일 목록
└── README.md              # 프로젝트 README
```

## RAG 챗봇 사용 방법

1. 웹사이트 접속 후 '챗봇' 탭을 클릭하세요.
2. 'AI 고급 기능 활성화' 버튼을 클릭하여 RAG 기능을 초기화하세요.
   - 초기화는 몇 분 정도 소요될 수 있습니다.
   - 초기화가 완료되면 '활성화' 상태로 변경됩니다.
3. 챗봇에 경제, 투자, 금융 관련 질문을 입력하세요.
4. 질문에 관련된 문서를 참조하여 정확한 답변을 제공합니다.
5. 관련 문서 링크를 클릭하면 해당 문서 전체 내용을 확인할 수 있습니다.

## API 엔드포인트

| 엔드포인트                        | 메소드 | 설명                       |
| --------------------------------- | ------ | -------------------------- |
| `/api/economy_terms`              | GET    | 경제 용어 파일 목록 반환   |
| `/api/recent_contents`            | GET    | 최신 콘텐츠 파일 목록 반환 |
| `/api/economy_terms/<filename>`   | GET    | 특정 경제 용어 내용 반환   |
| `/api/recent_contents/<filename>` | GET    | 특정 콘텐츠 내용 반환      |
| `/api/chatbot/status`             | GET    | 챗봇 초기화 상태 확인      |
| `/api/chatbot/initialize`         | POST   | 챗봇 초기화 요청           |
| `/api/chatbot/query`              | POST   | 챗봇에 질의                |
| `/api/chatbot/reset`              | POST   | 챗봇 재설정                |

## 문제 해결

### economy_terms 폴더에 파일이 없는 경우

- 콘텐츠 파일을 `data/economy_terms` 폴더에 추가하세요.
- 마크다운(.md) 형식의 파일을 사용해야 합니다.

### OpenAI API 키 관련 오류

- `.env` 파일이 올바르게 생성되었는지 확인하세요.
- API 키가 유효한지 확인하세요.
- 최신 OpenAI API는 결제 정보가 등록되어 있어야 합니다.

### 서버 실행 오류

- `requirements.txt`의 모든 의존성이 설치되었는지 확인하세요.
- 로그 파일(`server.log`, `rag_chatbot.log`)를 확인하여 상세 오류 정보를 확인하세요.

## 미래 개선 사항

1. **다국어 지원**: 영어 등 추가 언어 지원
2. **모바일 최적화**: 반응형 디자인 개선
3. **로컬 LLM 지원**: 오픈소스 LLM을 통한 비용 절감 및 프라이버시 강화
4. **사용자 피드백 시스템**: 챗봇 응답에 대한 피드백으로 모델 개선

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.
