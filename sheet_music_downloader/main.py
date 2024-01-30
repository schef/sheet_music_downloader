#!/usr/bin/env python3

import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from yt_dlp import YoutubeDL
import fitz
import sheet_music_downloader.credentials as credentials


def get_driver(headless=False, download_dir=credentials.download_path):
    print("get_driver")
    options = Options()
    options.set_preference('network.proxy.type', 4)
    options.set_preference('pdfjs.disabled', True)
    options.set_preference('plugin.scan.plid.all', False)
    options.set_preference('plugin.scan.Acrobat', '99.0')
    options.set_preference('browser.download.folderList', 2)
    options.set_preference('browser.download.dir', download_dir)
    options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/pdf;text/html;application/vnd.ms-excel')
    options.set_preference('browser.download.alwaysOpenPanel', False)
    #options.accept_untrusted_certs = True
    os.environ['CLASS'] = 'selenium'
    if headless == True:
        os.environ['MOZ_HEADLESS'] = '1'
    driver = webdriver.Firefox(options=options)
    return driver

def set_download_dir(driver, directory):
      driver.command_executor._commands["SET_CONTEXT"] = ("POST", "/session/$sessionId/moz/context")
      driver.execute("SET_CONTEXT", {"context": "chrome"})

      driver.execute_script("""
        Services.prefs.setBoolPref('browser.download.useDownloadDir', true);
        Services.prefs.setStringPref('browser.download.dir', arguments[0]);
        """, directory)

      driver.execute("SET_CONTEXT", {"context": "content"})

def open_url(driver, url):
    print(f"open_url start {url}")
    driver.get(url)
    print(f"open_url end {url}")

def wait(driver, xpath, timeout=120):
    print(f"wait start [{xpath}, {timeout}]")
    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    print(f"wait end [{xpath}, {timeout}]")


def login(driver):
    print("login start")
    open_url(driver, credentials.url_login)
    driver.find_element(By.ID, "tbReturningCustomerEmail").send_keys(credentials.username)
    driver.find_element(By.ID, "tbReturningCustomerPassword").send_keys(credentials.password)
    driver.find_element(By.ID, "ibSignIn").click()
    print("login end")

def get_song_url(id):
    return credentials.url_song.replace("<ID>", id)

def clean_up_text(text):
    text = ''.join(c.lower() for c in text if not c.isspace())
    text = text.replace("/", "_")
    return text


def get_title(driver):
    print("get_title start")
    wait(driver, '//*[@class="breadcrumb"]')
    title = driver.find_element(by=By.CLASS_NAME, value="breadcrumb").text
    title = clean_up_text(title)
    print("get_title end")
    return title

def get_parts(driver):
    print("get_parts start")
    parts = {}
    wait(driver, '//tbody')
    tbody = driver.find_element(by=By.TAG_NAME, value="tbody")
    trs = tbody.find_elements(by=By.TAG_NAME, value="tr")
    for tr in trs[1:]:
        a = tr.find_element(by=By.TAG_NAME, value="a")
        parts[a.text] = a.get_attribute('href')
    print("get_parts end")
    return parts

def get_youtube_url(driver):
    print("get_youtube_url start")
    wait(driver, '//*[@id="videoPreviewViewer"]')
    iframe = driver.find_element(by=By.ID, value="videoPreviewViewer")
    return iframe.get_attribute("src")

def get_pdf_url(driver):
    wait(driver, '//*[@id="staticScoreViewer"]')
    iframe = driver.find_element(by=By.ID, value="staticScoreViewer")
    return iframe.get_attribute("src")

def download_pdf(driver, url):
    url = url.replace("https://tools.sheetmusic.direct/?url=", "")
    url = url.replace("/inline", "")
    driver.execute_script('setTimeout(function(){window.location.reload(1);}, 10000);')
    open_url(driver, url)

def download_part(driver, url):
    print(f"download_part start {url}")
    open_url(driver, url)
    url = get_pdf_url(driver)
    download_pdf(driver, url)
    print(f"download_part end")

def download_youtube_video(url, download_dir):
    ydl = YoutubeDL()
    info = ydl.extract_info(url, download=False)
    id = info.get("id")
    title = info.get("title")
    title = title.replace("/", " ")

    ydl_opts = {'outtmpl': f'{download_dir}/{title}[{id}].mp4',
        'format': 'mp4/bestaudio/best'}
    ydl = YoutubeDL(ydl_opts)
    ydl.download([url])
    ydl_opts = {
        'outtmpl': f'{download_dir}/{title}[{id}].m4a',
        'format': 'm4a/bestaudio/best',
        # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',}]}
    ydl = YoutubeDL(ydl_opts)
    ydl.download([url])

def get_replace_text_from_page(page):
    for line in page.get_text().splitlines():
        if "Subscription" in line:
            return line
    return None

def clean_pdf(filename):
    print(f"[CLEAN_PDF] {filename}")
    tmp_filename = filename + ".tmp"
    os.rename(filename, tmp_filename)
    doc = fitz.open(tmp_filename)  # the file with the text you want to change
    for page in doc:
        replace_text = get_replace_text_from_page(page)
        print(replace_text)
        found = page.search_for(replace_text)  # list of rectangles where to replace
        for item in found:
            page.add_redact_annot(item, '')  # create redaction for text
            page.apply_redactions()  # apply the redaction now
            #page.insert_text(item.bl - (0, 3), "")
    doc.save(filename)
    os.remove(tmp_filename)

def clean_pdfs(path):
    print(f"[CLEAN_PDFS] {path}")
    for filename in os.listdir(path):
        if filename.endswith(".pdf"):
            f = os.path.join(path, filename)
            if os.path.isfile(f):
                clean_pdf(f)

def download_parts(driver, id):
    login(driver)
    open_url(driver, get_song_url(id))
    title = get_title(driver)
    print(f"[DOWN_PRT]: title {title}, {id}")
    download_dir = f"{credentials.download_path}/{title}"
    print(f"[DOWN_PRT]: download_dir {download_dir}")
    set_download_dir(driver, download_dir) 
    youtube_url = get_youtube_url(driver)
    print(f"[DOWN_PRT]: youtube_url {youtube_url}")
    download_youtube_video(youtube_url, download_dir)
    #from IPython import embed; embed()
    parts = get_parts(driver)
    index = 0
    total_len = len(parts)
    for name, url in parts.items():
        index += 1
        print(f"[DOWN_PRT] part {index}/{total_len} {name}")
        download_part(driver, url)
    clean_pdfs(download_dir)

def run():
    import sys
    try:
        id = sys.argv[1]
    except:
        print("[RUN]: Error: song ID not provided")
        sys.exit(1)
    driver = get_driver()
    download_parts(driver, id)
    #from IPython import embed; embed()
    driver.close()


if __name__ == "__main__":
    run()
