/**
 * 애플리케이션 초기화 모듈
 * 모든 모듈을 로드하고 애플리케이션을 초기화합니다.
 */

// 문서 로드 완료 시 실행
document.addEventListener("DOMContentLoaded", function () {
  try {
    console.log("경제용 뉴스레터 애플리케이션 초기화 중...");

    // 콘텐츠 관리자 초기화
    if (window.ContentManager) {
      window.ContentManager.init();
      console.log("콘텐츠 관리자 초기화 완료");
    } else {
      console.error("콘텐츠 관리자 모듈을 찾을 수 없습니다.");
    }

    // 챗봇 초기화
    if (window.Chatbot) {
      window.Chatbot.init();
      console.log("챗봇 초기화 완료");
    } else {
      console.error("챗봇 모듈을 찾을 수 없습니다.");
    }

    // 푸터 항목 클릭 이벤트 설정
    setupFooterEvents();

    // 전역 검색 창 동작 설정
    setupGlobalSearchEvents();

    console.log("경제용 뉴스레터 애플리케이션 초기화 완료");
  } catch (error) {
    console.error("애플리케이션 초기화 중 오류 발생:", error);
  }
});

/**
 * 푸터 항목 클릭 이벤트 설정
 */
function setupFooterEvents() {
  const footerItems = document.querySelectorAll(".footer-list-item");

  footerItems.forEach((item) => {
    item.addEventListener("click", () => {
      // 제목 추출
      const title = item.querySelector("h3").textContent;

      // 챗봇 탭 활성화
      document.getElementById("tab-chatbot").click();

      // 제목 기반으로 쿼리 생성
      const query = title.replace(/[📈🏦📊]/g, "").trim();

      // 챗봇에 메시지 추가
      window.Chatbot.addMessageToChat("user", query);

      // 챗봇 응답 처리
      setTimeout(() => {
        // 관련 응답 생성
        let response = "";

        if (query.includes("ETF")) {
          response = `ETF(Exchange-Traded Fund)는 주식처럼 거래소에서 거래되는 인덱스 펀드예요! 다양한 자산에 분산 투자할 수 있고, 거래 비용이 낮아 인기가 많습니다. 더 자세한 정보는 경제 용어 섹션에서 확인해보세요!`;
        } else if (query.includes("금리")) {
          response = `금리는 자금 대차에 따른 이자율을 의미해요. 금리가 오르면 예금 이자는 높아지지만, 대출 이자도 높아지고 기업 투자가 위축될 수 있어요. 또한 주식시장에는 부정적인 영향을 미칠 수 있답니다!`;
        } else if (query.includes("주식 투자")) {
          response = `처음 주식 투자를 시작할 때는 기본적인 투자 원칙을 알아두는 것이 중요해요! 분산투자, 장기투자, 가치투자 등의 원칙을 지키고, 무리한 레버리지나 단기매매는 피하는 것이 좋아요. 특히 처음에는 자신이 이해할 수 있는 기업에 투자하는 것이 좋습니다!`;
        } else {
          response = `${query}에 관심이 있으시군요! 이 주제는 최근 많은 투자자들에게 중요한 관심사예요. 궁금한 점이 있으면 구체적으로 질문해 주세요!`;
        }

        window.Chatbot.addMessageToChat("bot", response);
      }, 800);
    });
  });
}

/**
 * 전역 검색 이벤트 설정
 */
function setupGlobalSearchEvents() {
  const globalSearch = document.getElementById("global-search");

  // 포커스 시 스타일 변경
  globalSearch.addEventListener("focus", () => {
    globalSearch.classList.add("ring-2", "ring-orange-500");
  });

  globalSearch.addEventListener("blur", () => {
    globalSearch.classList.remove("ring-2", "ring-orange-500");
  });

  // 모바일 디바이스 검출
  const isMobile = window.innerWidth < 768;

  // 모바일인 경우 검색창 크기 조정
  if (isMobile) {
    globalSearch.setAttribute("placeholder", "검색...");
  }

  // 화면 크기 변경 시 대응
  window.addEventListener("resize", () => {
    const isMobileNow = window.innerWidth < 768;
    if (isMobileNow) {
      globalSearch.setAttribute("placeholder", "검색...");
    } else {
      globalSearch.setAttribute("placeholder", "경제 용어 또는 콘텐츠 검색...");
    }
  });
}
