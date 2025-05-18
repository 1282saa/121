const puppeteer = require('puppeteer');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(express.json());
app.use(cors());

// 언박싱 비디오 URL 가져오기
async function getUnboxingVideoUrl() {
    let browser;
    try {
        browser = await puppeteer.launch({ 
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        
        // 플레이리스트 페이지로 이동
        const playlistUrl = 'https://tv.naver.com/sed.thumb?tab=playlist&playlistNo=972727';
        console.log('플레이리스트 페이지로 이동:', playlistUrl);
        await page.goto(playlistUrl, { waitUntil: 'networkidle2' });
        
        // 3초 대기
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // 전체재생 버튼 찾기
        try {
            console.log('전체재생 버튼 찾기...');
            
            // 여러 가지 방법으로 전체재생 버튼 찾기
            let playAllUrl = null;
            
            // 1. 클래스 이름으로 찾기
            const playButton = await page.$('.PlaylistEnd_button_play__pbqEe');
            if (playButton) {
                playAllUrl = await page.evaluate(el => el.href, playButton);
                console.log('클래스로 찾음:', playAllUrl);
            }
            
            // 2. 텍스트로 찾기
            if (!playAllUrl) {
                playAllUrl = await page.evaluate(() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const playAllLink = links.find(link => link.textContent.trim() === '전체재생');
                    return playAllLink ? playAllLink.href : null;
                });
                if (playAllUrl) {
                    console.log('텍스트로 찾음:', playAllUrl);
                }
            }
            
            // 3. XPath로 찾기
            if (!playAllUrl) {
                const [playAllButton] = await page.$x('//a[contains(text(), "전체재생")]');
                if (playAllButton) {
                    playAllUrl = await page.evaluate(el => el.href, playAllButton);
                    console.log('XPath로 찾음:', playAllUrl);
                }
            }
            
            if (playAllUrl) {
                console.log('전체재생 URL:', playAllUrl);
                
                // 자동재생 파라미터 추가
                const autoPlayUrl = playAllUrl.includes('?') 
                    ? `${playAllUrl}&autoPlay=true`
                    : `${playAllUrl}?autoPlay=true`;
                    
                await browser.close();
                return { success: true, url: autoPlayUrl };
            }
        } catch (e) {
            console.log('전체재생 버튼 찾기 실패:', e.message);
        }
        
        // 폴백: 플레이리스트 URL 반환
        console.log('전체재생 버튼을 찾지 못함, 플레이리스트 URL 반환');
        await browser.close();
        return { success: true, url: playlistUrl };
        
    } catch (error) {
        console.error('Error:', error);
        if (browser) await browser.close();
        return { success: false, error: error.message };
    }
}

// API 엔드포인트
app.post('/api/get-unboxing-video', async (req, res) => {
    console.log('언박싱 비디오 요청 받음');
    
    try {
        const result = await getUnboxingVideoUrl();
        res.json(result);
    } catch (error) {
        console.error('API 오류:', error);
        res.json({ success: false, error: error.message });
    }
});

// 서버 시작
const PORT = 3001;
app.listen(PORT, () => {
    console.log(`Puppeteer 서버가 포트 ${PORT}에서 실행 중입니다.`);
});