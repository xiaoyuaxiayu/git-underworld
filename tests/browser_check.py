"""Run against python run.py. Optional dependency: playwright with Chromium installed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
out=root/'.test-output'
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1080})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8765')
    page.get_by_role('button',name='模拟还魂',exact=True).first.click()
    assert page.locator('#alive').inner_text()=='1 次'
    page.locator('#force').click()
    assert '不检测真实强推' in page.locator('#message').inner_text()
    page.locator('#close').click()
    page.locator('#repo-path').fill(str(root/'demo-repository'))
    page.locator('#scan').click()
    expect(page.locator('#scanned')).to_have_text('6 / 6', timeout=60000)
    assert page.locator('#rows tr').count()==2
    assert not page.locator('#force').is_visible()
    assert page.get_by_role('button',name='模拟还魂',exact=True).count()==0
    assert page.locator('#rows img').count()==0
    assert '<img src=x onerror=alert(1)>' in page.locator('#rows').inner_text()
    page.screenshot(path=str(out/'real-analysis.png'),full_page=True)
    page.get_by_role('button',name='判决书',exact=True).first.click()
    assert '中文 空格.txt' in page.locator('#verdict-fields').inner_text()
    page.locator('#judgment').screenshot(path=str(out/'verdict.png'))
    page.locator('#verdict-close').click()
    page.locator('#search').fill('不存在')
    assert '暂无匹配' in page.locator('#rows').inner_text()
    page.locator('#search').fill('')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#repo-path').fill(str(root/'frontend'))
    page.locator('#scan').click()
    expect(page.locator('#scan')).to_be_enabled(timeout=60000)
    # frontend is inside the project Git repo; use a genuinely nonexistent path.
    page.locator('#repo-path').fill(str(root/'missing-directory'))
    page.locator('#scan').click()
    expect(page.locator('#warnings')).to_contain_text('目录不存在', timeout=60000)
    page.locator('#demo').click()
    assert page.locator('#rows tr').count()==4
    assert not errors,errors
    browser.close()
print('Browser checks passed: demo, real analysis, XSS text, verdict, search, mobile, errors, mode switch.')
