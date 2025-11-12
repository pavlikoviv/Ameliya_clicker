import re
import os
import logging
import boto3
import tempfile
import shutil # Добавляем для удаления временных директорий
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading

load_dotenv() # Load environment variables from .env file

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# S3_FILE_KEY will now be passed via API request

# Configure logging to file
logging.basicConfig(filename='debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

app = Flask(__name__)

def run_autoclicker_task(s3_file_key: str, identifier: str) -> tuple[dict, int]: # Добавляем identifier
    temp_dir = None
    file_path = None
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.basename(s3_file_key)
        file_path = os.path.join(temp_dir, file_name)

        logging.debug(f"Downloading '{s3_file_key}' from S3 bucket '{S3_BUCKET_NAME}' to '{file_path}'")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.getenv("AWS_S3_ENDPOINT_URL") # Optional: for custom S3 compatible storage
        )
        s3.download_file(S3_BUCKET_NAME, s3_file_key, file_path)
        logging.debug("File downloaded successfully from S3")

        FILE_PATH = file_path
        name_picture = file_name # Используем оригинальное имя файла

        # Извлекаем issue_number из имени файла (первые 6 символов)
        issue_number = name_picture[:6]
        logging.debug(f"Извлечен issue_number: {issue_number}")

        with sync_playwright() as playwright:
            logging.debug("Launching browser")
            browser = playwright.chromium.launch(headless=True)
            # browser = playwright.chromium.launch(headless=False)
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
            page.locator("#login-input").fill(os.getenv("LOGIN_USERNAME"))

            logging.debug("Filling password")
            page.locator("#password-input").click()
            page.locator("#password-input").fill(os.getenv("LOGIN_PASSWORD"))

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
            logging.debug(f"Filling search with {issue_number}")
            page.get_by_role("textbox", name="Поиск").fill(issue_number)

            # Найдите кнопку

            logging.debug("Finding claim number element")
            claim_number = page.get_by_role("cell", name=issue_number)
            time.sleep(4)
            try:
                box = claim_number.bounding_box()
                if not box:
                    logging.error(f"Элемент с issue_number '{issue_number}' не найден или невидим")
                    # Возвращаем ошибку, указывающую на проблему с issue_number
                    return {"error": f"Claim with issue number '{issue_number}' not found or invisible", "identifier": identifier}, 400
            except TimeoutError:
                logging.error(f"Таймаут при поиске элемента с issue_number '{issue_number}'")
                return {"error": f"Timeout while searching for claim with issue number '{issue_number}'", "identifier": identifier}, 400
            except Exception as e:
                logging.error(f"Произошла ошибка при получении bounding_box для issue_number '{issue_number}': {e}")
                return {"error": f"Error getting bounding box for claim with issue number '{issue_number}': {e}", "identifier": identifier}, 400

            # Проверяем наличие поля "в работе"
            if page.locator("text=в работе").is_visible():
                logging.debug("Поле 'в работе' найдено. Выполняем действия для 'Прибыл на объект'.")
                # Добавляем статус и клик по "Прибыл на объект"
                page.get_by_role("row", name=issue_number).get_by_role("img").click()
                time.sleep(1)
                page.get_by_text("Прибыл на объект").wait_for(timeout=10000) # Добавляем ожидание
                page.get_by_text("Прибыл на объект").click()
                time.sleep(1)
                logging.debug("Waiting for 'Прибыл на объект' button to appear")
                page.get_by_role("button", name="Прибыл на объект").wait_for(timeout=10000) # Ожидаем кнопку
                logging.debug("Clicking 'Прибыл на объект' button")
                page.get_by_role("button", name="Прибыл на объект").click() # Кликаем по кнопке
                time.sleep(1) # Задержка по запросу пользователя
            else:
                logging.debug("Поле 'в работе' не найдено. Пропускаем действия для 'Прибыл на объект'.")

            logging.debug(f"Координаты элемента: x={box['x']}, y={box['y']}, ширина={box['width']}, высота={box['height']}")

            # 🔥 Расчёт точки клика: немного правее и ниже элемента
            # Например: +50 пикселей по X (правее), +10 по Y (ниже)
            click_x = box['x'] + box['width'] - 20   # Правее границы элемента
            click_y = box['y'] + box['height'] / 2 - 20  # По центру по вертикали, чуть ниже

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
            # file_name_display = os.path.basename(FILE_PATH[:6])
            page.wait_for_selector(f'span.caption:has-text("{issue_number}")', timeout=10000)
            logging.debug("✅ Файл отобразился в списке загруженных!")

            logging.debug("Clicking 'Add' button")
            page.get_by_role("button", name="Добавить").click()
            logging.debug("Clicking 'Close' button")
            page.locator(".form-card-close-icon").click()
            
            page.get_by_text("Запись успешно обновлена").wait_for(timeout=10000)
            
            
            # logging.debug("Sleeping for 5 seconds")
            # time.sleep(5)

            # ---------------------
            logging.debug("Closing context")
            context.close()
            logging.debug("Closing browser")
            browser.close()
            logging.debug("Browser closed")
            return {"message": f"Autoclicker task completed successfully for S3_FILE_KEY: {s3_file_key}", "identifier": identifier}, 200 # Успешный возврат

    except Exception as e:
        logging.error(f"An error occurred during autoclicker task: {e}")
        return {"error": f"An internal server error occurred: {e}", "identifier": identifier}, 500 # Внутренняя ошибка сервера
    finally:
        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logging.debug(f"Temporary directory '{temp_dir}' deleted.")

@app.route("/run_autoclicker", methods=["POST"])
def trigger_autoclicker():
    data = request.get_json()
    s3_file_key = data.get("s3_file_key")
    identifier = data.get("identifier") # Получаем новый идентификатор

    if not s3_file_key:
        return jsonify({"error": "Missing 's3_file_key' in request body", "identifier": identifier}), 400
    
    if not identifier:
        return jsonify({"error": "Missing 'identifier' in request body"}), 400

    # Выполняем задачу напрямую и возвращаем ее результат
    response_data, status_code = run_autoclicker_task(s3_file_key, identifier) # Передаем identifier
    return jsonify(response_data), status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
