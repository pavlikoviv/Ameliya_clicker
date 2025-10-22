import re
import os
import logging
from playwright.sync_api import Playwright, sync_playwright, expect
import time

FILE_PATH = "367001-3.jpg"
name_picture = "367001-3.jpg"
# Configure logging to file
logging.basicConfig(filename='debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def run(playwright: Playwright) -> None:
    logging.debug("Launching browser")
    browser = playwright.chromium.launch(headless=False)
    logging.debug("Browser launched")

    logging.debug("Creating new context")
    context = browser.new_context()
    logging.debug("Context created")

    logging.debug("Creating new page")
    page = context.new_page()
    logging.debug("Page created")

    logging.debug("Navigating to login page")
    page.goto("https://newamelia.mvideo.ru/login", timeout=15000)
    logging.debug("Navigation completed")

    logging.debug("Filling login")
    page.locator("#login-input").click()
    page.locator("#login-input").fill("service-techno@impsa.ru")

    logging.debug("Filling password")
    page.locator("#password-input").click()
    page.locator("#password-input").fill("dfg3456!@#$")

    logging.debug("Clicking login button")
    page.get_by_role("button", name="Войти").click()

    logging.debug("Clicking nav issues")
    page.locator("#nav-dynamic_issues").get_by_role("img").click()

    # 🔥 Ждём, пока индикатор загрузки (q-skeleton) исчезнет
    logging.debug("Waiting for loader to disappear")
    loader = page.locator("div:nth-child(3) > .q-skeleton.q-mb-sm")
    loader.wait_for(state='hidden', timeout=10000)  # Ждать
    logging.debug("Loader disappeared")

    logging.debug("Clicking search textbox")
    page.get_by_role("textbox", name="Поиск").click()
    logging.debug("Filling search with 367001")
    page.get_by_role("textbox", name="Поиск").fill("367001")

    # Найдите кнопку

    logging.debug("Finding claim number element")
    claim_number = page.get_by_role("cell", name="367001")
    box = claim_number.bounding_box()
    if not box:
        logging.error("Элемент не найден или невидим")
        raise Exception("Элемент не найден или невидим")
    logging.debug(f"Координаты элемента: x={box['x']}, y={box['y']}, ширина={box['width']}, высота={box['height']}")

    # 🔥 Расчёт точки клика: немного правее и ниже элемента
    # Например: +50 пикселей по X (правее), +10 по Y (ниже)
    click_x = box['x'] + box['width'] + 20   # Правее границы элемента
    click_y = box['y'] + box['height'] / 2 + 20  # По центру по вертикали, чуть ниже

    # ✅ Кликаем в эту точку
    logging.debug(f"Clicking at point: ({click_x}, {click_y})")
    page.mouse.click(click_x, click_y)

    logging.debug(f"✅ Клик выполнен в точку: ({click_x}, {click_y})")


    logging.debug("Clicking Comments tab")
    page.get_by_role("tab", name="Комментарии").click()

    logging.debug("Waiting for upload area to appear")
    upload_locator = page.locator("#file-field-images")
    upload_locator.wait_for(timeout=10000)
    logging.debug("Upload area appeared")

    logging.debug("Setting input files")
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files(FILE_PATH)
    logging.debug(f"📁 Файл '{FILE_PATH}' успешно установлен!")

    # 🔥 ШАГ 3: Дождёмся, пока файл отобразится в интерфейсе (опционально)
    # В вашем HTML уже есть примеры: <div class="existing-file"> с картинками
    file_name = os.path.basename(FILE_PATH)
    page.wait_for_selector('span.caption:has-text("{FILE_PATH}")', timeout=10000)
    logging.debug("✅ Файл отобразился в списке загруженных!")

    # page.get_by_role("button", name="Добавить").click()
    # page.locator(".form-card-close-icon").click()
    logging.debug("Sleeping for 5 seconds")
    time.sleep(20)

    # ---------------------
    logging.debug("Closing context")
    context.close()
    logging.debug("Closing browser")
    browser.close()
    logging.debug("Browser closed")


with sync_playwright() as playwright:
    run(playwright)
