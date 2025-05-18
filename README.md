# 경제용 AI 챗봇

경제 용어와 최신 경제 콘텐츠를 AI 기반으로 검색하고 학습할 수 있는 웹 애플리케이션입니다.

## 주요 기능

1. **AI 기반 경제 질문 답변**: 경제 용어와 콘텐츠를 기반으로 질문에 답변하는 AI 챗봇
   - 내부 문서 검색 + 실시간 웹 검색을 통한 종합적인 답변
   - 출처와 인용문 제공으로 신뢰성 있는 정보 전달
2. **경제 용어 사전**: 다양한 경제 용어에 대한 설명 제공
3. **최신 경제 콘텐츠**: 최신 경제 트렌드와 뉴스 제공
4. **서울경제 1면 언박싱**: 서울경제신문 1면 동영상 재생 (선택사항)

## 기술 스택

- **프론트엔드**: HTML, TailwindCSS, JavaScript
- **백엔드**: Python 3.11, Flask
- **AI 및 검색**:
  - **벡터 데이터베이스**: ChromaDB
  - **임베딩**: OpenAI (text-embedding-3-small)
  - **언어 모델**: OpenAI GPT-3.5-turbo / GPT-4
  - **실시간 웹 검색**: Perplexity API
  - **프레임워크**: LangChain
  - **검색 기법**: 하이브리드 검색 (Vector + Keyword)

## Railway 배포

### 사전 요구사항

- GitHub 계정
- Railway 계정
- OpenAI API 키
- Perplexity API 키

### 배포 단계

1. GitHub에 코드 푸시

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/economy-chatbot.git
   git push -u origin main
   ```

2. Railway에서 새 프로젝트 생성
   - railway.app 접속
   - "New Project" 클릭
   - "Deploy from GitHub repo" 선택
   - 저장소 선택

3. 환경 변수 설정 (Railway Dashboard)
   - `OPENAI_API_KEY`: OpenAI API 키
   - `PERPLEXITY_API_KEY`: Perplexity API 키
   - `SECRET_KEY`: Flask 시크릿 키 (자동 생성 가능)

4. 배포 시작
   - Railway가 자동으로 빌드 및 배포 진행
   - 배포 완료 후 제공된 URL로 접속

## 로컬 개발

### 사전 요구사항

- Python 3.11 이상
- OpenAI API 키
- Perplexity API 키

### 설치 단계

1. 저장소 클론

   ```bash
   git clone https://github.com/yourusername/economy-chatbot.git
   cd economy-chatbot
   ```

2. 가상환경 생성 및 활성화

   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

3. 의존성 설치

   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정

   ```bash
   cp .env.example .env
   # .env 파일을 열어 API 키 입력
   ```

5. 서버 실행

   ```bash
   python server.py
   ```

6. 웹 브라우저에서 접속
   - http://localhost:5000

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
