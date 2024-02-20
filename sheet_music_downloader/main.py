#!/usr/bin/env python3

import os
import time
import sys
import re
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from yt_dlp import YoutubeDL
import fitz
import sheet_music_downloader.credentials as credentials
import cairosvg

def close_last_tab(driver):
    if (len(driver.window_handles) == 2):
        driver.switch_to.window(window_name=driver.window_handles[-1])
        driver.close()
        driver.switch_to.window(window_name=driver.window_handles[0])

def install_extensions(driver):
    extension_path = f"{credentials.extensions_location}/adblock_plus-3.23.xpi"
    extension_full_path = os.path.realpath(os.path.expanduser(extension_path))
    driver.install_addon(extension_full_path)
    time.sleep(5)
    close_last_tab(driver)
    #extension_path = f"{credentials.extensions_location}/i_m_not_robot_captcha_clicker-1.3.1.xpi"
    #extension_full_path = os.path.realpath(os.path.expanduser(extension_path))
    #driver.install_addon(extension_full_path)
    #time.sleep(5)
    #close_last_tab(driver)

def get_driver(headless=False):
    print("get_driver")
    options = Options()
    options.set_preference('network.proxy.type', 4)
    options.set_preference('pdfjs.disabled', True)
    options.set_preference('plugin.scan.plid.all', False)
    options.set_preference('plugin.scan.Acrobat', '99.0')
    options.set_preference('browser.download.folderList', 2)
    options.set_preference('browser.download.dir', "/tmp")
    options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/pdf;text/html;application/vnd.ms-excel')
    options.set_preference('browser.download.alwaysOpenPanel', False)
    #options.accept_untrusted_certs = True
    os.environ['CLASS'] = 'selenium'
    if headless == True:
        os.environ['MOZ_HEADLESS'] = '1'
    driver = webdriver.Firefox(options=options)
    return driver

def set_download_dir(driver, directory):
    full_path = os.path.realpath(os.path.expanduser(directory))
    driver.command_executor._commands["SET_CONTEXT"] = ("POST", "/session/$sessionId/moz/context")
    driver.execute("SET_CONTEXT", {"context": "chrome"})

    driver.execute_script("""
        Services.prefs.setBoolPref('browser.download.useDownloadDir', true);
        Services.prefs.setStringPref('browser.download.dir', arguments[0]);
        """, full_path)

    driver.execute("SET_CONTEXT", {"context": "content"})

def open_url(driver, url):
    print(f"open_url start {url}")
    driver.get(url)
    print(f"open_url end {url}")

def wait(driver, xpath, timeout=3600):
    print(f"wait start [{xpath}, {timeout}]")
    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    print(f"wait end [{xpath}, {timeout}]")


def login(driver):
    print("login start")
    open_url(driver, credentials.url_login)
    try:
        driver.find_element(By.CLASS_NAME, "g-recaptcha")
        input("Solve recaptcha and press Return: ")
    except NoSuchElementException:
        pass
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

def get_ensamble_title(driver):
    print("get_ensamble_title start")
    wait(driver, '//*[@class="breadcrumb"]')
    old_title = driver.find_element(by=By.CLASS_NAME, value="breadcrumb").text
    print(f"[DEBUG], [{old_title}]")
    regex = re.compile('[^a-zA-Z /]')
    _, composer, title, style = "_".join(regex.sub('', old_title).lower().split()).split("_/_")
    new_title = "_".join([style, title, composer])
    print(f"[DEBUG], [{new_title}]")
    print("get_ensamble_title end")
    #from IPython import embed; embed()
    return new_title

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
    wait(driver, '//*[@id="videoPreviewViewer"]', timeout=10)
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
        if replace_text is not None:
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
    full_path = os.path.realpath(os.path.expanduser(path))
    for filename in os.listdir(full_path):
        if filename.endswith(".pdf"):
            f = os.path.join(full_path, filename)
            if os.path.isfile(f):
                clean_pdf(f)

def check_if_pdfs_in_dir(download_dir):
    if os.path.exists(download_dir): 
        files = next(os.walk(download_dir))[2]
        return any(f for f in files if ".pdf" in f)
    return False

def download_ensamble_parts(driver, id, download_path):
    login(driver)
    open_url(driver, get_song_url(id))
    title = get_ensamble_title(driver)
    print(f"[DOWN_PRT]: title {title}, {id}")
    download_dir = f"{download_path}/{title}_{id}"
    print(f"[DOWN_PRT]: download_dir {download_dir}")

    if check_if_pdfs_in_dir(download_dir):
        selection = input("Already exist, do you want to redownload? [y/n]: ")
        if selection == "n":
            print("[DOWN_PRT]: skiping download")
            return
        else:
            shutil.rmtree(download_dir, ignore_errors=True)
            print("[DOWN_PRT]: redownloading")


    set_download_dir(driver, download_dir) 
    try:
        youtube_url = get_youtube_url(driver)
        print(f"[DOWN_PRT]: youtube_url {youtube_url}")
        download_youtube_video(youtube_url, download_dir)
    except:
        print("[DOWN_PRT]: Error, no youtube video, skiping")
    #from IPython import embed; embed()
    parts = get_parts(driver)
    index = 0
    total_len = len(parts)
    for name, url in parts.items():
        index += 1
        print(f"[DOWN_PRT] part {index}/{total_len} {name}")
        download_part(driver, url)
    clean_pdfs(download_dir)
    print(f"[ZIP]: {download_dir}.zip")
    shutil.make_archive(f"{title}_{id}", 'zip', download_path)

def download_piano_parts(driver, id, download_path):
    login(driver)
    open_url(driver, get_song_url(id))
    title_text = driver.find_element(by=By.TAG_NAME, value="title").get_attribute("textContent").strip()
    song_name, composer, category = title_text.split(" | ")
    title = f"{category}_{song_name.replace(' Sheet Music', '')}_{composer}_{id}".lower().replace(" ", "_")

    print(f"[DOWN_PNO]: title {title}")
    download_dir = f"{download_path}/{title}"
    print(f"[DOWN_PNO]: download_dir {download_dir}")

    if check_if_pdfs_in_dir(download_dir):
        selection = input("Already exist, do you want to redownload? [y/n]: ")
        if selection == "n":
            print("[DOWN_PNO]: skiping download")
            return
        else:
            shutil.rmtree(download_dir, ignore_errors=True)
            print("[DOWN_PNO]: redownloading")
            os.mkdir(download_dir)
    else:
        shutil.rmtree(download_dir, ignore_errors=True)
        os.mkdir(download_dir)

    #try:
    #    youtube_url = get_youtube_url(driver)
    #    print(f"[DOWN_PNO]: youtube_url {youtube_url}")
    #    download_youtube_video(youtube_url, download_dir)
    #except:
    #    print("[DOWN_PNO]: Error, no youtube video, skiping")

    wait(driver, "//iframe")
    time.sleep(1)
    driver.switch_to.frame(driver.find_element(by=By.TAG_NAME, value="iframe"))
    wait(driver, "//*[@id = 'pagesContainer']")
    pages_container = driver.find_element(by=By.ID, value="pagesContainer")
    back_button = pages_container.find_element(by=By.ID, value="pageTurnerBack")
    forward_button = pages_container.find_element(by=By.ID, value="pageTurnerForward")
    pages = pages_container.find_elements(by=By.XPATH, value="//div[starts-with(@id, 'page-')]")
    pdfs = []
    svgs = []
    for page in pages:
        time.sleep(1)
        page_name = page.get_attribute('id')
        print(f"[DOWN_PNO] part {page_name}")
        #from IPython import embed; embed()
        wait(page, ".//*[local-name()='svg']")
        svg = page.find_element(by=By.TAG_NAME, value="svg")
        driver.execute_script("arguments[0].setAttribute('xmlns','http://www.w3.org/2000/svg')", svg)
        svg_obj = svg.get_attribute('outerHTML')
        save_path_svg = f"{download_dir}/{page_name}.svg"
        save_path_pdf = f"{download_dir}/{page_name}.pdf"
        pdfs.append(save_path_pdf)
        svgs.append(save_path_svg)
        with open(save_path_svg, 'w') as f:
            f.write(svg_obj)
        cairosvg.svg2pdf(url=save_path_svg, write_to=save_path_pdf)
        if forward_button.is_displayed():
            forward_button.click()
    clean_pdfs(download_dir)
    doc = fitz.open()
    for pdf in pdfs:
        doc.insert_file(pdf)
    doc.save(f"{download_dir}/{title}.pdf")
    doc.close()
    for pdf in pdfs:
        os.remove(pdf)
    for svg in svgs:
        os.remove(svg)


def download_by_id(id, download_path):
    driver = get_driver()
    install_extensions(driver)
    #download_ensamble_parts(driver, id, download_path)
    download_piano_parts(driver, id, download_path)
    #from IPython import embed; embed()
    driver.close()

def comment_id(filename, id):
    with open(filename, 'r') as txt:
        lines = txt.readlines()
        for i in range(len(lines)):
            if id in lines[i]:
                lines[i] = f"#{lines[i]}"

        with open(filename, 'w') as txt:
            txt.writelines(lines)

def run():
    print("[RUN]: start")
    ids = []
    download_path = "./"
    filename = None
    try:
        data = sys.argv[1]
        if data.isdigit():
            print("[RUN]: id found")
            ids.append(data)
        elif os.path.isfile(data):
            print("[RUN]: file found")
            with open(data, 'r') as f:
                for l in f.readlines():
                    if l.strip().isdigit():
                        ids.append(l.strip())
            filename = data
            download_path, _ = os.path.splitext(filename)
            try:
                os.mkdir(download_path)
            except FileExistsError:
                pass
        else:
            print(f"[RUN]: {data} is nor id nor file")
    except Exception as e:
        print(f"[RUN]: Error with {e}")
        sys.exit(1)

    for id in ids:
        download_by_id(id, download_path)
        if filename is not None:
            comment_id(filename, id)
    print("[RUN]: end")

if __name__ == "__main__":
    pass
