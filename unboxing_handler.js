const puppeteer = require('puppeteer');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(express.json());
app.use(cors());

// 브라우저 재사용을 위한 전역 변수
let browser = null;

// Puppeteer 브라우저 초기화
async function initBrowser() {
    if (!browser) {
        browser = await puppeteer.launch({ 
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }
    return browser;
}

// 언박싱 비디오 URL 가져오기
async function getUnboxingVideoUrl() {
    const browser = await initBrowser();
    const page = await browser.newPage();
    
    try {
        // 플레이리스트 페이지로 이동
        const playlistUrl = 'https://tv.naver.com/sed.thumb?tab=playlist&playlistNo=972727';
        console.log('플레이리스트 페이지로 이동:', playlistUrl);
        await page.goto(playlistUrl, { waitUntil: 'networkidle2' });
        
        // 페이지 로드 대기 (구버전 Puppeteer 호환)
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // 전체재생 버튼 XPath
        const playAllXpath = '/html/body/div[1]/div[3]/div[2]/div/div[3]/div/div/div/a';
        
        try {
            console.log('전체재생 버튼 찾기...');
            
            // XPath로 전체재생 버튼 찾기
            const [playAllButton] = await page.$x(playAllXpath);
            
            if (playAllButton) {
                console.log('전체재생 버튼 발견');
                
                // 버튼의 href 속성 가져오기
                const playAllUrl = await page.evaluate(el => el.href, playAllButton);
                
                if (playAllUrl) {
                    console.log('전체재생 URL:', playAllUrl);
                    
                    // autoPlay 파라미터 추가
                    const autoPlayUrl = playAllUrl.includes('?') 
                        ? `${playAllUrl}&autoPlay=true`
                        : `${playAllUrl}?autoPlay=true`;
                    
                    return { success: true, url: autoPlayUrl };
                }
                
                // href가 없다면 클릭 시도
                console.log('href가 없음, 클릭 시도...');
                
                // 새 탭에서 열리지 않도록 target 속성 제거
                await page.evaluate(el => {
                    el.removeAttribute('target');
                    // 클릭 이벤트를 막기 위해 onclick도 제거
                    el.onclick = null;
                }, playAllButton);
                
                // 페이지 이동 대기와 클릭
                const [response] = await Promise.all([
                    page.waitForNavigation({ waitUntil: 'networkidle2' }),
                    playAllButton.click()
                ]);
                
                const newUrl = page.url();
                console.log('클릭 후 새 URL:', newUrl);
                
                const autoPlayUrl = newUrl.includes('?') 
                    ? `${newUrl}&autoPlay=true`
                    : `${newUrl}?autoPlay=true`;
                
                return { success: true, url: autoPlayUrl };
            } else {
                console.log('전체재생 버튼을 찾을 수 없음');
                
                // 다른 선택자로 시도
                const alternativeSelectors = [
                    'a[class*="play_all"]',
                    'a[href*="playAll"]',
                    '.play_all_btn',
                    'a:contains("전체재생")'
                ];
                
                for (const selector of alternativeSelectors) {
                    try {
                        const button = await page.$(selector);
                        if (button) {
                            const url = await page.evaluate(el => el.href, button);
                            if (url) {
                                console.log(`대체 선택자로 찾음: ${selector}`);
                                const autoPlayUrl = url.includes('?') 
                                    ? `${url}&autoPlay=true`
                                    : `${url}?autoPlay=true`;
                                return { success: true, url: autoPlayUrl };
                            }
                        }
                    } catch (e) {
                        // 계속 시도
                    }
                }
            }
        } catch (e) {
            console.log('전체재생 버튼 처리 오류:', e.message);
        }
        
        // 전체재생 버튼을 찾지 못한 경우 페이지 구조 확인
        const pageInfo = await page.evaluate(() => {
            const allLinks = Array.from(document.querySelectorAll('a'));
            const playLinks = allLinks.filter(a => 
                a.textContent.includes('전체재생') || 
                a.textContent.includes('재생') ||
                a.className.includes('play')
            );
            
            return {
                totalLinks: allLinks.length,
                playLinks: playLinks.map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    className: a.className,
                    xpath: getXPath(a)
                }))
            };
            
            function getXPath(element) {
                if (element.id !== '')
                    return '//*[@id="' + element.id + '"]';
                if (element === document.body)
                    return element.tagName;
                
                let ix = 0;
                const siblings = element.parentNode.childNodes;
                for (let i = 0; i < siblings.length; i++) {
                    const sibling = siblings[i];
                    if (sibling === element)
                        return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                        ix++;
                }
            }
        });
        
        console.log('페이지 정보:', JSON.stringify(pageInfo, null, 2));
        
        // 전체재생 버튼을 찾지 못한 경우 첫 번째 비디오로 폴백
        
        // 여러 가지 방법으로 첫 번째 비디오 찾기
        console.log('첫 번째 비디오 찾기 시작...');
        
        // 방법 1: CSS 선택자로 시도
        let videoLink = null;
        try {
            videoLink = await page.evaluate(() => {
                // 다양한 선택자 시도
                const selectors = [
                    '.playlist_list li:first-child a',
                    '.thumb_list li:first-child a', 
                    '[class*="playlist"] li:first-child a',
                    'ul li a[href*="sed.thumb"]'
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.href) {
                        console.log(`Found with selector: ${selector}`);
                        return element.href;
                    }
                }
                return null;
            });
            
            if (videoLink) {
                console.log('CSS 선택자로 찾음:', videoLink);
            }
        } catch (e) {
            console.log('CSS 선택자 실패:', e.message);
        }
        
        // 방법 2: XPath로 시도
        if (!videoLink) {
            try {
                const xpaths = [
                    '/html/body/div[1]/div[3]/div[2]/div/div[3]/div/div[1]/ul/li[1]/a',
                    '//div[@id="playlist_list"]/ul/li[1]/a',
                    '//ul[@class="playlist_list"]/li[1]/a'
                ];
                
                for (const xpath of xpaths) {
                    try {
                        const elements = await page.$x(xpath);
                        if (elements.length > 0) {
                            videoLink = await page.evaluate(el => el.href, elements[0]);
                            if (videoLink) {
                                console.log(`XPath로 찾음: ${xpath}`);
                                break;
                            }
                        }
                    } catch (e) {
                        console.log(`XPath 시도 실패 (${xpath}):`, e.message);
                    }
                }
            } catch (e) {
                console.log('XPath 실패:', e.message);
            }
        }
        
        // 방법 3: 간단한 XPath로 시도
        if (!videoLink) {
            try {
                const simpleXpath = '//ul[contains(@class, "playlist_list")]/li[1]/a';
                const elements = await page.$x(simpleXpath);
                
                if (elements.length > 0) {
                    videoLink = await page.evaluate(el => el.href, elements[0]);
                }
            } catch (e) {
                console.log('간단한 XPath 실패:', e.message);
            }
        }
        
        // 결과 확인
        if (videoLink) {
            console.log('비디오 링크 찾음:', videoLink);
            
            // 자동재생 파라미터 추가
            const autoPlayUrl = videoLink.includes('?') 
                ? `${videoLink}&autoPlay=true`
                : `${videoLink}?autoPlay=true`;
                
            return { success: true, url: autoPlayUrl };
        } else {
            console.log('비디오 링크를 찾을 수 없음, 클릭 시도...');
            
            // 방법 4: 직접 클릭해서 페이지 이동
            try {
                // XPath로 첫 번째 비디오 클릭
                const clickXpath = '/html/body/div[1]/div[3]/div[2]/div/div[3]/div/div[1]/ul/li[1]/a';
                const [element] = await page.$x(clickXpath);
                
                if (element) {
                    // 새 탭에서 열리지 않도록 target 속성 제거
                    await page.evaluate(el => el.removeAttribute('target'), element);
                    
                    // 페이지 이동 대기
                    const [response] = await Promise.all([
                        page.waitForNavigation({ waitUntil: 'networkidle2' }),
                        element.click()
                    ]);
                    
                    const newUrl = page.url();
                    console.log('클릭 후 새 URL:', newUrl);
                    
                    const autoPlayUrl = newUrl.includes('?') 
                        ? `${newUrl}&autoPlay=true`
                        : `${newUrl}?autoPlay=true`;
                    
                    return { success: true, url: autoPlayUrl };
                }
            } catch (e) {
                console.log('클릭 방법 실패:', e.message);
            }
            
            // 디버깅: 페이지 구조 확인
            const pageStructure = await page.evaluate(() => {
                const body = document.body.innerHTML;
                const playlist = document.querySelector('[class*="playlist"]');
                const firstLink = document.querySelector('a[href*="sed.thumb"]');
                
                return {
                    hasPlaylist: !!playlist,
                    playlistClasses: playlist?.className,
                    firstLinkHref: firstLink?.href,
                    htmlSample: body.substring(0, 1000)
                };
            });
            console.log('페이지 구조:', JSON.stringify(pageStructure, null, 2));
            
            return { success: false, error: '비디오 요소를 찾을 수 없습니다.' };
        }
    } catch (error) {
        console.error('Error:', error);
        return { success: false, error: error.message };
    } finally {
        await page.close();
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

// 프로세스 종료 시 브라우저 정리
process.on('SIGINT', async () => {
    if (browser) {
        await browser.close();
    }
    process.exit();
});

// Export for testing
module.exports = { getUnboxingVideoUrl };