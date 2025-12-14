from flask import Flask, request, jsonify
from flask_cors import CORS
import pyppeteer
import asyncio

app = Flask(__name__)
# IMPORTANT: This allows your React app on Hostinger to call this API
CORS(app) 

async def run_accessibility_check(url):
    """Launches a browser, goes to URL, and returns a mock analysis."""
    browser = await pyppeteer.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = await browser.newPage()
    try:
        await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
        # For this example, we'll just get the page title.
        # In a real app, you would inject axe-core here.
        title = await page.title()
        results = {
            "status": "success",
            "url": url,
            "title": title,
            "issues": [
                {"id": "mock-1", "description": "This is a mock issue for demonstration.", "type": "alert"}
            ]
        }
        return results
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await browser.close()

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({"error": "URL is required"}), 400

    url_to_check = data['url']
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(run_accessibility_check(url_to_check))
    
    return jsonify(results)

if __name__ == '__main__':
    # The app.run() is for local testing.
    # Cloud Run will use Gunicorn to run this.
    app.run(port=8080, host='0.0.0.0')