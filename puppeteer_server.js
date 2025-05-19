const express = require('express');
const puppeteer = require('puppeteer');
const cors = require('cors');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Puppeteer 브라우저 인스턴스
let browser = null;

// 브라우저 초기화
async function initBrowser() {
    if (!browser) {
        browser = await puppeteer.launch({
            headless: false, // GUI 모드로 실행 (디버깅용)
            defaultViewport: null,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }
    return browser;
}

// 1면 언박싱 비디오 URL 가져오기
app.post('/api/get-unboxing-video', async (req, res) => {
    console.log('언박싱 비디오 요청 받음');
    
    try {
        const browser = await initBrowser();
        const page = await browser.newPage();
        
        // 서울경제 1면 언박싱 페이지로 이동
        const url = 'https://tv.naver.com/sedtv';
        console.log(`페이지 이동: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // 잠시 대기
        await page.waitForTimeout(2000);
        
        // 1면 언박싱 플레이리스트 찾기
        console.log('1면 언박싱 플레이리스트 찾는 중...');
        
        // 여러 전략으로 1면 언박싱 찾기
        const strategies = [
            // 전략 1: 텍스트로 직접 찾기
            async () => {
                const element = await page.evaluateHandle(() => {
                    const elements = Array.from(document.querySelectorAll('a, div, span'));
                    return elements.find(el => el.textContent && el.textContent.includes('1면 언박싱'));
                });
                if (element && element.asElement()) {
                    await element.asElement().click();
                    return true;
                }
                return false;
            },
            
            // 전략 2: 플레이리스트 카드 찾기
            async () => {
                await page.evaluate(() => {
                    const cards = Array.from(document.querySelectorAll('.cds_area.playlist .cds'));
                    const unboxingCard = cards.find(card => {
                        const title = card.querySelector('.title');
                        return title && title.textContent.includes('1면 언박싱');
                    });
                    if (unboxingCard) {
                        unboxingCard.click();
                        return true;
                    }
                    return false;
                });
            }
        ];
        
        // 전략들 시도
        let clicked = false;
        for (const strategy of strategies) {
            try {
                clicked = await strategy();
                if (clicked) break;
            } catch (e) {
                console.log('전략 실패:', e.message);
            }
        }
        
        if (!clicked) {
            // 직접 플레이리스트 URL로 이동
            const playlistUrl = 'https://tv.naver.com/sed.thumb?tab=playlist&playlistNo=972727';
            console.log(`직접 플레이리스트로 이동: ${playlistUrl}`);
            await page.goto(playlistUrl, { waitUntil: 'networkidle2' });
        }
        
        // 페이지 로드 대기
        await page.waitForTimeout(3000);
        
        // 전체재생 버튼 찾기
        console.log('전체재생 버튼 찾는 중...');
        
        const playButtonStrategies = [
            // 전략 1: 전체재생 텍스트로 찾기
            async () => {
                await page.click('button:has-text("전체재생")', { timeout: 5000 });
            },
            
            // 전략 2: CSS 선택자로 찾기
            async () => {
                await page.click('.play_all button', { timeout: 5000 });
            },
            
            // 전략 3: JavaScript로 찾기
            async () => {
                await page.evaluate(() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const playButton = buttons.find(btn => btn.textContent.includes('전체재생'));
                    if (playButton) playButton.click();
                });
            }
        ];
        
        // 재생 버튼 클릭 시도
        for (const strategy of playButtonStrategies) {
            try {
                await strategy();
                console.log('전체재생 버튼 클릭 성공!');
                break;
            } catch (e) {
                console.log('재생 버튼 전략 실패:', e.message);
            }
        }
        
        // 비디오가 재생되기를 대기
        await page.waitForTimeout(2000);
        
        // 현재 URL 반환
        const finalUrl = page.url();
        console.log(`최종 URL: ${finalUrl}`);
        
        res.json({
            success: true,
            url: finalUrl,
            autoplay: true
        });
        
    } catch (error) {
        console.error('오류 발생:', error);
        res.json({
            success: false,
            error: error.message,
            url: 'https://tv.naver.com/sed.thumb?tab=playlist&playlistNo=972727'
        });
    }
});

// 브라우저 종료 엔드포인트
app.post('/api/close-browser', async (req, res) => {
    if (browser) {
        await browser.close();
        browser = null;
    }
    res.json({ success: true });
});

// 서버 시작
app.listen(PORT, () => {
    console.log(`Puppeteer 서버가 포트 ${PORT}에서 실행 중입니다.`);
});