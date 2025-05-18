// Puppeteer 핸들러 테스트 스크립트
const { getUnboxingVideoUrl } = require('./unboxing_handler');

async function test() {
    console.log('Puppeteer 핸들러 테스트 시작...');
    
    try {
        const result = await getUnboxingVideoUrl();
        console.log('결과:', JSON.stringify(result, null, 2));
        
        if (result.success) {
            console.log('성공! 비디오 URL:', result.url);
        } else {
            console.log('실패! 오류:', result.error);
        }
    } catch (error) {
        console.error('테스트 오류:', error);
    }
    
    process.exit();
}

test();