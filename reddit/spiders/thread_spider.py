import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from time import sleep
import logging
import json

class ThreadSpider(scrapy.Spider):
    name = "thread"
    visitedUrls = []
    config = {}

    def __init__(self, name=None, **kwargs):
        with open('config.json') as con:
            self.config = json.load(con)
        self.startUrlDriver()
        self.start_urls = self.getNextUrl()

    # Starts the selenium urldriver and clicks cookies button
    def startUrlDriver(self):
        optionsurl = Options()
        # Enable headless by removing comment below
        #optionsurl.add_argument("--headless")
        _browser_profile = webdriver.FirefoxProfile()
        _browser_profile.set_preference("dom.webnotifications.enabled", False)
        self.urldriver = webdriver.Firefox(
            firefox_profile=_browser_profile, executable_path='geckodriver.exe', firefox_options=optionsurl)
        self.urldriver.get("https://www.reddit.com/r/letstalkmusic")
        for xpath in self.config["xpath"]["urlDriverLoad"]:
            page_loaded = WebDriverWait(self.urldriver, 10).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
            if page_loaded:
                # Find and click the button.
                button = self.urldriver.find_element_by_xpath(xpath)
                button.click()

    # Finds urls on subreddit and returns a list of url strings
    def getNextUrl(self):
        xpath = self.config["xpath"]["urlXPath"]
        threadUrls = self.urldriver.find_elements_by_xpath(xpath)
        urls = []

        for url in threadUrls:
            if url.get_attribute("href") not in self.visitedUrls:
                self.visitedUrls.append(url.get_attribute("href"))
                urls.append(url.get_attribute("href"))
        return urls
    
    def scrollUrlDriver(self):
        xpath = self.config["xpath"]["urlXPath"]
        threadUrls = self.urldriver.find_elements_by_xpath(xpath)
        element = threadUrls[-1]
        element.location_once_scrolled_into_view
        

    def parse(self, response):
        if self.checkDynamic(response): # Dynamic.
            hrefList = self.parseDynamic(response)
        else: # Static.
            hrefList = self.parseStatic(response)
        # hreflist for continue this thread
        if len(hrefList) != 0:
            for href in hrefList:
                yield response.follow(href, callback=self.parse)
        # hreflist = 0, thread is done scraped
        urls = self.getNextUrl()
        for url in urls:
            yield response.follow(url, callback=self.parse)
        self.scrollUrlDriver()
        

    # Parses the HTML, treating it as if it contains dynamic content.
    def parseDynamic(self, response):
        # This disables the browser asking for notifications.
        options = Options()
        # Enable headless by removing comment below
        #options.add_argument("--headless")
        _browser_profile = webdriver.FirefoxProfile()
        _browser_profile.set_preference("dom.webnotifications.enabled", False)
        self.driver = webdriver.Firefox(
            firefox_profile=_browser_profile, executable_path='geckodriver.exe', firefox_options=options)
        self.driver.get(response.url)
        # page_loaded will be True if it finds the element within 10 seconds, False otherwise.
        xpath = self.config["xpath"]["threadDriverLoad"]
        page_loaded = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, xpath[0]))
        )
        hrefList = []
        if page_loaded:
            # Find and click the cookies button.
            for path in xpath:
                button = self.driver.find_element_by_xpath(path)
                button.click()
            self.clickMoreComments()
            hrefList = self.continueDynamic(response)
        self.driver.close()
        return hrefList

    # Parses the HTML, treating it as if it contains dynamic content.
    def parseStatic(self, response):
        return self.continueStatic(response)

    # This loop will continue until it does not find any more Continue This Thread elements.
    def continueDynamic(self, response):
        continuexpath = self.config["xpath"]["threadDriverContinueThread"]
        continue_elements = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, continuexpath)
            )
        )
        print(continue_elements)
        hrefList = []
        continuexpath += "/.."
        if continue_elements:
            cont = self.driver.find_elements_by_xpath(continuexpath)
            for c in cont:
                href = c.get_attribute("href")
                hrefList.append(href)
            return hrefList

    # Finds "continue this thread" elements statically.
    def continueStatic(self, response):
        continuexpath = self.config["xpath"]["threadDriverContinueThread"]
        continuexpath += "/../@href"
        href = response.xpath(continuexpath).getall()
        hList = []
        for h in href:
            hList.append(h)
        return hList

    # Returns true if page is dynamic, false otherwise
    def checkDynamic(self, response):
        xpath = self.config["xpath"]["threadDriverLoadComments"][0]
        return len(response.xpath(xpath).getall()) != 0

    # This loop will continue until it does not find any more More replies to click.
    def clickMoreComments(self):
        loop = True
        xpath = self.config["xpath"]["threadDriverLoadComments"][0]
        while (loop):
            try:
                more_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, xpath))
                )
            except TimeoutException as te:
                print(str(te))
                loop = False
                break
            if more_elements:
                elements = self.driver.find_elements_by_xpath(
                    xpath)
                for e in elements:
                    try:
                        e.click()
                    except Exception as ex:
                        print(str(ex))
                self.clickDownvoted()
            else:
                loop = False

    # Attempts to click downvoted comments.
    def clickDownvoted(self):
        xpath = self.config["xpath"]["threadDriverLoadComments"][1]
        downvoted = self.driver.find_elements_by_xpath(
            xpath)
        for d in downvoted:
            try:
                d.click()
            except Exception as ex:
                print(str(ex))