import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
        page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type in ['error', 'warning'] else None)
        
        await page.goto("http://localhost:5173/")
        
        # Inject fake token
        await page.evaluate("""() => {
            localStorage.setItem('docToken', 'fake_token');
        }""")
        
        # We need the backend to return a dummy document
        # Instead, we can intercept network requests and return a dummy document
        await page.route("**/api/v1/documents/", lambda route: route.fulfill(
            json=[{"id": 1, "title": "lecture 2.pdf", "status": "ready", "created_at": "2026-04-19T00:00:00Z"}]
        ))
        
        await page.goto("http://localhost:5173/documents")
        await page.wait_for_selector("text=lecture 2.pdf", timeout=5000)
        
        button = await page.wait_for_selector("text=Chat With Doc", timeout=5000)
        await button.click()
        
        await page.wait_for_timeout(2000)
        
        print("Captured Errors:")
        for err in errors:
            print(err)
            
        await browser.close()

asyncio.run(main())
