const puppeteer = require('puppeteer');

async function testPuppeteer() {
    const browser = await puppeteer.launch({ 
        headless: false, // 브라우저를 표시하여 디버깅
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        // 플레이리스트 페이지로 이동
        const playlistUrl = 'https://tv.naver.com/sed.thumb?tab=playlist&playlistNo=972727';
        console.log('플레이리스트 페이지로 이동:', playlistUrl);
        await page.goto(playlistUrl, { waitUntil: 'networkidle2' });
        
        // 5초 대기
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // 페이지 내 모든 링크 검사
        const links = await page.evaluate(() => {
            const allLinks = Array.from(document.querySelectorAll('a'));
            return allLinks.map(a => ({
                text: a.textContent.trim(),
                href: a.href,
                className: a.className,
                id: a.id
            })).filter(link => link.text.includes('재생') || link.href.includes('play'));
        });
        
        console.log('재생 관련 링크들:');
        console.log(JSON.stringify(links, null, 2));
        
        // 전체 HTML 구조 확인
        const htmlStructure = await page.evaluate(() => {
            const container = document.querySelector('.playlist_header') || 
                           document.querySelector('[class*="playlist"]') ||
                           document.querySelector('[class*="play"]');
            
            if (container) {
                return container.outerHTML.substring(0, 1000);
            }
            return 'Container not found';
        });
        
        console.log('\n플레이리스트 헤더 구조:');
        console.log(htmlStructure);
        
        // XPath로 직접 찾기
        const xpaths = [
            '/html/body/div[1]/div[3]/div[2]/div/div[3]/div/div/div/a',
            '//a[contains(text(), "전체재생")]',
            '//a[contains(@class, "play_all")]',
            '//div[@class="playlist_header"]//a'
        ];
        
        for (const xpath of xpaths) {
            try {
                const elements = await page.$x(xpath);
                if (elements.length > 0) {
                    console.log(`\nXPath로 찾음: ${xpath}`);
                    const href = await page.evaluate(el => el.href, elements[0]);
                    console.log(`URL: ${href}`);
                }
            } catch (e) {
                console.log(`XPath 실패: ${xpath}`);
            }
        }
        
    } catch (error) {
        console.error('Error:', error);
    }
    
    // 10초 후 브라우저 닫기
    setTimeout(async () => {
        await browser.close();
        process.exit();
    }, 10000);
}

testPuppeteer();