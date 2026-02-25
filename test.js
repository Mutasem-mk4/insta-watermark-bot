const axios = require('axios');

async function testSnapInsta(url) {
    try {
        const formData = new URLSearchParams();
        formData.append('url', url);
        formData.append('action', 'post');

        const response = await axios.post('https://snapinsta.app/action.php', formData, {
            headers: {
                'Origin': 'https://snapinsta.app',
                'Referer': 'https://snapinsta.app/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'application/json, text/plain, */*'
            }
        });
        console.log("Success:", response.data);
    } catch (err) {
        console.error("Error:", err.message);
    }
}

testSnapInsta('https://www.instagram.com/reel/C8_XlOMpZf9/');
