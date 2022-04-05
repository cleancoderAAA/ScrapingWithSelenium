import time
import json
import requests
from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector as mysql
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

product_names = []
db = mysql.connect(
    host="localhost",
    user="root",
    passwd="marilou21!@",
    database="store"
)
xmlurl = "https://tripanaki.gr/wp-content/uploads/webexpert-skroutz-xml/skroutz.xml"
mystore = "Tripanaki"

def ReadXml():
    print("Loading XML...")
    response = requests.get(xmlurl)
    xml_doc = etree.fromstring(response.content)
    print("Loading XML completed.\n Writing to database...")
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS categories")
    cursor.execute("DROP TABLE IF EXISTS brands")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute(
        "CREATE TABLE `categories` ( `id` INT NOT NULL AUTO_INCREMENT, `name` VARCHAR(200) NOT NULL, PRIMARY KEY (`id`) ) ENGINE=INNODB CHARSET=utf8")
    cursor.execute(
        "CREATE TABLE `brands` ( `id` INT NOT NULL AUTO_INCREMENT, `name` VARCHAR(200) NOT NULL, PRIMARY KEY (`id`) ) ENGINE=INNODB CHARSET=utf8")
    cursor.execute(
        "CREATE TABLE `products` ( `id` INT NOT NULL AUTO_INCREMENT, `name` VARCHAR(200) NOT NULL, `category` INT NOT NULL, `brand` INT NOT NULL,`pid` VARCHAR(200) NOT NULL, `mpn` VARCHAR(200) NOT NULL, `price` FLOAT NOT NULL,`updatedPrice` FLOAT NOT NULL, `imgurl` VARCHAR(1000) NOT NULL, `favourite` INT NOT NULL,`repricing` INT NOT NULL, `changed` INT NOT NULL,PRIMARY KEY (`id`) ) ENGINE=INNODB CHARSET=utf8")
    cursor.execute("INSERT INTO `categories`(`name`) VALUES ('All')")
    db.commit()
    cursor.execute("INSERT INTO `brands`(`name`) VALUES ('All')")
    db.commit()
    products = xml_doc.xpath("//product")
    for product in products:
        productname = product.xpath("name")[0].text
        categoryid = 0
        if len(product.xpath("category")) > 0:
            categoryname = product.xpath("category")[0].text
            query = "SELECT * FROM `categories` WHERE `name` = '" + categoryname + "'"
            cursor.execute(query)
            records = cursor.fetchall()
            if len(records) == 0:
                cursor.execute("INSERT INTO `categories`(`name`) VALUES ('" + categoryname + "')")
                db.commit()
                categoryid = cursor.lastrowid
            else:
                categoryid = records[0][0]
        brandid = 0
        if len(product.xpath("manufacturer")) > 0:
            brandname = product.xpath("manufacturer")[0].text
            query = "SELECT * FROM `brands` WHERE `name` = '" + brandname + "'"
            cursor.execute(query)
            records = cursor.fetchall()
            if len(records) == 0:
                cursor.execute("INSERT INTO `brands`(`name`) VALUES ('" + brandname + "')")
                db.commit()
                brandid = cursor.lastrowid
            else:
                brandid = records[0][0]
        pid = product.xpath("id")[0].text
        mpnObj = product.xpath("mpn")
        mpn = ""
        if len(mpnObj) > 0:
            mpn = mpnObj[0].text
        price = float(product.xpath("price_with_vat")[0].text)
        imgurl = product.xpath("image")[0].text
        query = "INSERT INTO `products`(`name`, `category`, `brand`, `pid`, `mpn`, `price`, `updatedPrice`, `imgurl`) VALUES ('" + productname + "'," + str(categoryid) + "," + str(brandid) + ",'" + pid + "','" + mpn + "'," + str(price) + "," + str(price) + ", '" + imgurl + "')"
        cursor.execute(query)
        db.commit()
        product_names.append(productname)
    print("Writing database completed")
    print("Start scraping")

def acp_api_send_request(driver, message_type, data={}):
    message = {
		# this receiver has to be always set as antiCaptchaPlugin
        'receiver': 'antiCaptchaPlugin',
        # request type, for example setOptions
        'type': message_type,
        # merge with additional data
        **data
    }
    # run JS code in the web page context
    # preceicely we send a standard window.postMessage method
    return driver.execute_script("""
    return window.postMessage({});
    """.format(json.dumps(message)))

def Scrap():
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS competitors")
    cursor.execute("CREATE TABLE `competitors` ( `id` INT NOT NULL AUTO_INCREMENT, `product` INT NOT NULL, `storename` VARCHAR(200) NOT NULL, `place` INT NOT NULL, `totalnum` INT NOT NULL, `price` VARCHAR(50) NOT NULL, `shipping` VARCHAR(50) NOT NULL, `delivery` VARCHAR(50) NOT NULL, `availability` VARCHAR(1000) NOT NULL, PRIMARY KEY (`id`) ) ENGINE=INNODB CHARSET=utf8")
    st = 0
    interval = 1000
    product_num = len(product_names)
    options = Options()
    ua = UserAgent()
    userAgent = ua.random
    options.add_argument(f'user-agent={userAgent}')
    options.add_extension('anticaptcha-plugin_v0.62.crx')
    driver = webdriver.Chrome(chrome_options=options,service=Service(ChromeDriverManager().install()))
    driver.maximize_window()
    driver.get("https://www.skroutz.gr/")

    acp_api_send_request(
        driver,
        'setOptions',
        {'options': {'antiCaptchaApiKey': '3cc92dd56f82ead0f09617bd80cdbf06'}}
    )

                # 3 seconds pause
    time.sleep(3)

    driver.get("https://www.skroutz.gr")
    #driver.find_element(By.ID, "accept-all").click()
    f = 0
    for it in range(0, product_num):
        product_name = product_names[it]
        search_bar = WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.XPATH, '//input[@id="search-bar-input"]')))
        search_bar.clear()
        search_bar.send_keys(product_name)
        search_bar.send_keys(Keys.RETURN)
        cursor.execute("SELECT id FROM products WHERE `name` = '" + product_name + "'")
        tempids = cursor.fetchall()
        if len(tempids) == 0:
            continue
        product_id = tempids[0][0]
        searched = 0
        try:
            link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@class='js-sku-link']")))
        except TimeoutException:
            #time.sleep(1)
            continue
        try:
            page_title = driver.find_element(By.XPATH, "//h1[@class='page-title']")
            #time.sleep(1)
            continue
        except NoSuchElementException:
            #time.sleep(1)
            driver.execute_script("arguments[0].click();", link)
            try:
                product_cards = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, '//li[@class="card js-product-card"]')))
                #time.sleep(1)
            except TimeoutException:
                #time.sleep(1)
                continue
            num_cards = len(product_cards)
            i = 0
            flag = 0
            for product_card in product_cards:
                ActionChains(driver).move_to_element(product_card).perform()                
                try:
                    ignored_exceptions = (NoSuchElementException, StaleElementReferenceException,)
                    wait = WebDriverWait(driver, 10, ignored_exceptions=ignored_exceptions)
                    store_name = wait.until(lambda d:product_card.find_element(By.CLASS_NAME, "shop-name")).text
                    if store_name == mystore:
                        flag = 1
                    if flag == 0 and i >= 4:
                        i = i + 1
                        continue
                    price = wait.until(lambda d:product_card.find_element(By.CLASS_NAME, "dominant-price")).text
                    shipping_prices = wait.until(lambda d:product_card.find_elements(By.CSS_SELECTOR, ".extra-cost.cf>em"))
                    shipping = shipping_prices[0].text
                    delivery = shipping_prices[1].text
                    deliver_time = wait.until(lambda d:product_card.find_element(By.CSS_SELECTOR, "span.availability")).text
                except :
                    continue
                query = "INSERT INTO `competitors`(`product`, `storename`, `place`, `totalnum`, `price`, `shipping`, `delivery`, `availability`)" \
                        "VALUES(" + str(product_id) + ", '" + store_name + "', " + str(i + 1) + ", " + str(num_cards) + ", '" + price + "', '" + shipping + \
                        "', '" + delivery + "', '" + deliver_time + "')"
                cursor.execute(query)
                db.commit()
                i = i + 1
                if i >= 5:
                    if flag == 1: break
            #time.sleep(1)
    st = st + interval
    driver.quit()
    print("Scraping completed")

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    ReadXml()
    Scrap()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
