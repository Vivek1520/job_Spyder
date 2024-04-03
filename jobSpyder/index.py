
import os
import pandas as pd
import time
from flask import Flask, request, send_file, jsonify, render_template, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import Process, Queue

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_job_details', methods=['POST'])
def get_job_details():

    job_title = request.form['job_title']
    location = request.form['location']

    # Create queues for communication between processes
    indeed_queue = Queue()
    naukri_queue = Queue()
    apna_queue = Queue()

    # Create processes for scraping
    indeed_process = Process(target=scrape_indeed, args=(job_title, location, indeed_queue))
    naukri_process = Process(target=scrape_naukri, args=(job_title, location, naukri_queue))
    apna_process = Process(target=scrape_apna, args=(job_title, location, apna_queue))

    # Start processes
    indeed_process.start()
    naukri_process.start()
    apna_process.start()

    # Wait for processes to finish
    indeed_process.join()
    naukri_process.join()
    apna_process.join()

    # Get results from queues
    indeed_data = indeed_queue.get()
    naukri_data = naukri_queue.get()
    apna_data = apna_queue.get()

    # Combine the data from all sources
    all_data = naukri_data + indeed_data + apna_data

    # Create a DataFrame using the combined data
    df = pd.DataFrame(all_data, columns=['Title', 'Company', 'Salary', 'Source'])

    # Create the downloads directory if it doesn't exist
    downloads_dir = os.path.join(app.instance_path, 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)

    # Save DataFrame to Excel
    file_name = 'job_details.xlsx'
    file_path = os.path.join(downloads_dir, file_name)
    df.to_excel(file_path, index=False)

    # Return the download URL in the response
    return jsonify({'download_url': url_for('download_file', file_name=file_name)})

@app.route('/download_file/<file_name>')
def download_file(file_name):
    file_path = os.path.join(app.instance_path, 'downloads', file_name)
    return send_file(file_path, as_attachment=True)

def scrape_naukri(job_title, location, queue):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    # Open Naukri in a new tab
    driver.execute_script("window.open('https://www.naukri.com/mnjuser/homepage', 'new_tab')")
    time.sleep(1)
    driver.switch_to.window(driver.window_handles[1])

    # Perform scraping steps for Naukri
    input_field = WebDriverWait(driver, 6).until(
        EC.presence_of_element_located((By.CLASS_NAME, "nI-gNb-sb__placeholder")))
    input_field.click()
    time.sleep(1)
    input_field1 = driver.find_elements(By.CLASS_NAME, "suggestor-input")
    input_field1[0].send_keys(job_title)
    input_field1[0].send_keys(Keys.ARROW_DOWN)

    time.sleep(1)
    input_field1[1].send_keys(location)
    input_field1[1].send_keys(Keys.ARROW_DOWN)
    input_field1[0].send_keys(Keys.ENTER)
    time.sleep(2)

    title_elements = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "title")))
    company_elements = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "comp-name")))
    salary_elements = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "sal-wrap")))

    job_data = []
    for i in range(len(title_elements)):
        title = title_elements[i].text
        company = company_elements[i].text
        if i < len(salary_elements):
            salary = salary_elements[i].text
        else:
            salary = "N/A"
        job_data.append([ title,company, salary,"Naukri"])

    driver.close()
    queue.put(job_data)




def scrape_indeed(job_title, location, queue):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    # Open Indeed in the first tab
    driver.get("https://in.indeed.com/?advn=2069202823472410&vjk=e0181785d3bc22ab")
    time.sleep(1)
    input_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "text-input-what")))
    input_field.clear()
    input_field.send_keys(job_title)
    time.sleep(1)

    input_field = WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.ID, "text-input-where")))
    input_field.clear()
    input_field.send_keys(location)
    input_field.send_keys(Keys.ARROW_DOWN)
    input_field.send_keys(Keys.ENTER)

    time.sleep(1)

    button = WebDriverWait(driver, 7).until(
        EC.presence_of_element_located((By.CLASS_NAME, "yosegi-InlineWhatWhere-primaryButton")))
    button.click()

    time.sleep(1)

    job_titles = driver.find_elements(By.CLASS_NAME, 'jobTitle')
    time.sleep(2)
    job_locations = driver.find_elements(By.CLASS_NAME, 'company_location')
    time.sleep(2)
    job_salaries = driver.find_elements(By.CLASS_NAME, 'metadata.salary-snippet-container')

    job_data = []
    for i in range(len(job_salaries)):
        title = job_titles[i].text
        address = job_locations[i].text
        salary = job_salaries[i].text
        job_data.append([ title,address,salary,"Indeed"])

    driver.close()
    queue.put(job_data)


def scrape_apna(job_title, location, queue):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    # Open Apna in a new tab
    driver.execute_script(
        "window.open('https://apna.co/candidate/jobs?c_id=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5OTM3OTM3IiwiZXhwIjoxNzA2ODE1NzgzfQ.t4dEIL4SPDwFX_yHNixJnGHT_Tb2_p3yPSfOxKt_mJk', 'new_tab')")
    time.sleep(1)
    driver.switch_to.window(driver.window_handles[-1])  # Assuming apna.com opens in the third tab

    try:
        # Wait for the search input field to be clickable
        input_field = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//p[contains(text(), 'Search jobs by title, company or skill')]")))
        input_field.click()
        time.sleep(1)
        input_fields = driver.find_elements(By.CSS_SELECTOR, '.MuiInputBase-input')

        input_fields[0].send_keys(job_title)
        input_fields[0].send_keys(Keys.ARROW_DOWN)

        driver.implicitly_wait(6)

        input_fields[1].send_keys(location)
        input_fields[1].send_keys(Keys.ARROW_DOWN)

        input_fields[1].send_keys(Keys.ENTER)

        time.sleep(1)
        button = driver.find_element(By.CLASS_NAME,
                                     "Button-sc-1lqin44-0.styles__ApplyButton-sc-163gdpk-16.jNbklR.bYwurR")

        # Click on the button
        button.click()
        time.sleep(2)
        job_titles = driver.find_elements(By.CSS_SELECTOR, '.JobListCardstyles__JobTitle-ffng7u-7.cuaBGE')
        job_locations = driver.find_elements(By.CSS_SELECTOR, '.JobListCardstyles__JobCompany-ffng7u-8.gguURM')

        job_salaries = driver.find_elements(By.CSS_SELECTOR, '.JobListCardstyles__DisplayFlexCenter-ffng7u-10.BmLKA')
        time.sleep(2)
        apna_data = []
        for i in range(len(job_titles)):
            title = job_titles[i].text
            ad = job_locations[i].text
            if i < len(job_salaries):  # Use job_salaries instead of salary_elements
                salary = job_salaries[i].text
            else:
                salary = "N/A"
            apna_data.append([ title,  ad, salary,"Apna"])
        # Put the scraped data into the queue
        queue.put(apna_data)

    except Exception as e:
        print("Error occurred while scraping Apna:", e)

    finally:

        driver.quit()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
