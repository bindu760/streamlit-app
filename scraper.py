import os
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin

BASE_URL = "https://lict.edu.np"

# Text chunking setup
def chunk_text_by_words(text, max_words=300, overlap_words=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + max_words]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        i += (max_words - overlap_words)
    return chunks

# HTML cleaning logic
def clean_html_content(html_source):
    soup = BeautifulSoup(html_source, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        element.decompose()
    raw_text = soup.get_text(separator=" ")
    clean_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return " ".join(clean_lines)

def main_scraper():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    all_scraped_chunks = []
    
    # We will automatically discover valid internal links from the homepage menu
    discovered_pages = {"Home": f"{BASE_URL}/"}

    try:
        # Step 1: Scan homepage to auto-detect dynamic links (About, Courses, Team etc.)
        print("Scanning homepage to auto-discover active college links...")
        driver.get(f"{BASE_URL}/")
        time.sleep(4)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text().strip()
            
            # Filter internal paths like /about, /courses, /syllabus etc.
            if any(keyword in href.lower() for keyword in ["about", "course", "team", "syllabus", "notice", "qaa", "contact"]):
                full_url = urljoin(BASE_URL, href)
                if full_url.startswith(BASE_URL) and text:
                    page_key = text.replace("\n", "").strip()[:20]
                    discovered_pages[page_key] = full_url

        print(f"🎯 Auto-discovered {len(discovered_pages)} active college URLs! Starting Deep-Scan...\n")

        # Step 2: Scrape only valid discovered URLs
        for page_name, url in discovered_pages.items():
            print(f"Crawling -> {page_name}: {url}...")
            try:
                driver.get(url)
                time.sleep(4)
                
                html_content = driver.page_source
                clean_text = clean_html_content(html_content)
                
                # Double-check to skip broken "Page Not Found" responses
                if "page not found" in clean_text.lower() or "404" in clean_text:
                    print(f"⚠️ Skipped {page_name} (Broken URL or 404 Error page detected).\n")
                    continue
                
                if clean_text and len(clean_text) > 100:
                    text_chunks = chunk_text_by_words(clean_text, max_words=300, overlap_words=50)
                    
                    for index, chunk in enumerate(text_chunks):
                        all_scraped_chunks.append({
                            "source": url,
                            "section_title": f"LICT {page_name} Content (Chunk {index+1})",
                            "content": f"[Context from LICT Website - {page_name} Page - Verified Data]:\n{chunk}"
                        })
                        print(f"   ↳ [Chunk {index+1} Preview]: {chunk[:80]}...")
                    print(f"✅ Successfully processed {page_name} ({len(text_chunks)} chunks)\n")
            except Exception as e:
                print(f"❌ Error loading {url}: {e}\n")

        # Save verified database
        with open("lict_data.json", "w", encoding="utf-8") as json_file:
            json.dump(all_scraped_chunks, json_file, indent=4, ensure_ascii=False)
            
        print(f"🎉 Complete! Pure & verified data saved with {len(all_scraped_chunks)} total segments at 'lict_data.json'")

    finally:
        driver.quit()

if __name__ == "__main__":
    main_scraper()