// api/trigger-update.js
export default async function handler(req, res) {
  // CORS 헤더 설정 (모든 응답에 적용)
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  // OPTIONS 요청 처리 (CORS preflight)
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // POST 요청만 허용
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
    const GITHUB_OWNER = process.env.GITHUB_OWNER;
    const GITHUB_REPO = process.env.GITHUB_REPO;

    console.log('Environment check:', {
      hasToken: !!GITHUB_TOKEN,
      owner: GITHUB_OWNER,
      repo: GITHUB_REPO
    });

    if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
      return res.status(500).json({ 
        error: '환경 변수가 설정되지 않았습니다.',
        debug: {
          hasToken: !!GITHUB_TOKEN,
          hasOwner: !!GITHUB_OWNER,
          hasRepo: !!GITHUB_REPO
        }
      });
    }

    // GitHub Actions workflow dispatch API 호출
    const githubUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/update_prices.yml/dispatches`;
    
    console.log('Calling GitHub API:', githubUrl);

    const response = await fetch(githubUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Stock-Price-Updater'
      },
      body: JSON.stringify({
        ref: 'main'
      })
    });

    console.log('GitHub API response status:', response.status);

    if (response.status === 204) {
      return res.status(200).json({ 
        success: true, 
        message: '주가 업데이트가 시작되었습니다. 1-2분 후 완료됩니다.' 
      });
    } else {
      const errorText = await response.text();
      console.error('GitHub API 오류:', response.status, errorText);
      return res.status(500).json({ 
        error: 'GitHub Actions 트리거 실패',
        status: response.status,
        details: errorText
      });
    }

  } catch (error) {
    console.error('서버 오류:', error);
    return res.status(500).json({ 
      error: '서버 오류가 발생했습니다.',
      message: error.message 
    });
  }
}
