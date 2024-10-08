import socket
from urllib.parse import urlparse
from selenium.webdriver.common.by import By  # Used to locate elements by their tag name
from seleniumbase import Driver  # SeleniumBase's Driver to manage the WebDriver session
import time  # Used for sleep pauses in scrolling
import os  # Used to handle paths
import inspect  # Used to inspect the current script's path
from bs4 import BeautifulSoup  # Used to parse the HTML and extract text
import re


# Define the path for configurations and extensions
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))  # Get the current script directory
ext_path = os.path.join(currentdir, "i_care_about_cookies_unpacked")  # Path to the cookie consent extension


def create_webdriver():
    """
    Initializes and returns a Selenium WebDriver instance with specified settings.
    
    Returns:
        driver: A Selenium WebDriver instance configured for Chrome with specific options.
    """
    driver = Driver(
        browser="chrome",          # Use Chrome as the browser
        wire=True,                 # Enable wire mode for undetectable Chrome
        uc=True,                   # Use undetected Chrome mode
        headless2=True,            # Run in headless mode (no GUI)
        incognito=False,           # Disable incognito mode (set to False)
        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",  # User agent
        do_not_track=True,         # Enable 'Do Not Track' header
        undetectable=True,         # Make the browser undetectable by bot detection
        locale_code="de",          # Set locale to German
        extension_dir=ext_path,    # Path to the cookie consent extension
        no_sandbox=True            # Disable sandboxing for potential performance issues
    )
    return driver


def get_result_meta(url):
    """
    Retrieves metadata for a given URL, including IP address and main URL.

    Args:
        url (str): The URL to retrieve metadata for.

    Returns:
        dict: A dictionary containing 'ip' (IP address) and 'main' (main URL).
    """
    try:
        # Parse the URL and extract the hostname
        parsed_uri = urlparse(url)
        hostname = parsed_uri.netloc
        
        # Resolve the IP address for the given hostname
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "-1"  # If there's an error, set IP to "-1"
    
    # Construct the base URL (main URL)
    main = f'{parsed_uri.scheme}://{parsed_uri.netloc}/' if parsed_uri.netloc else url

    # Return the IP and main URL as a dictionary
    return {"ip": ip, "main": main}


def infinite_scroll(driver, pause_time=2):
    """
    Simulates scrolling to the bottom of a page multiple times to load dynamic content.
    
    Args:
        driver: The Selenium WebDriver instance.
        pause_time: Time to wait after each scroll for content to load.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")  # Get the initial scroll height

    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Pause to allow content to load
        time.sleep(pause_time)
        
        # Calculate the new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Break the loop if no new content is loaded
        if new_height == last_height:
            break
        last_height = new_height  # Update last height


def get_text(url):
    """
    Extracts all visible text from a given URL after scrolling to the bottom of the page.
    
    Args:
        url (str): The URL of the page to extract text from.
    """
    driver = create_webdriver()  # Initialize WebDriver
    driver.get(url)  # Navigate to the URL
    infinite_scroll(driver)  # Perform scrolling to load all content
    code = driver.page_source  # Get the page source (HTML)
    soup = BeautifulSoup(code, features="lxml")  # Parse the page with BeautifulSoup
    text = soup.get_text()  # Extract all text from the page
    text = re.sub(r'\n\s*\n', r'\n\n',text.strip(), flags=re.M)
    print(text)  # Print the extracted text


def crawl_url(url):
    """
    Crawls the given URL and extracts all 'href' attributes from anchor tags.
    
    Args:
        url (str): The URL of the webpage to crawl.
    """
    driver = create_webdriver()  # Initialize WebDriver

    try:
        # Open the webpage
        driver.get(url)

        # Scroll to load dynamic content (e.g., infinite scroll)
        infinite_scroll(driver)

        # Retrieve meta information like IP and main URL
        meta = get_result_meta(url)
        main = meta['main']
        main_www = main
        main = main.replace("www.", "")  # Handle URLs with or without 'www'

        # Find all anchor tags (<a>) on the page
        anchor_tags = driver.find_elements(By.TAG_NAME, "a")

        # Extract the 'href' attributes from anchor tags
        hrefs = [tag.get_attribute('href') for tag in anchor_tags]

        urls = []

        # Process and filter valid URLs
        for href in hrefs:
            if href:  # Only consider non-empty hrefs
                if 'http' not in href:
                    href = main + href  # Handle relative URLs
                if 'javascript:void' not in href and (main in href or main_www in href):    
                    urls.append(href)
        
        # Remove duplicates by converting the list to a set
        urls = list(set(urls))

        # Print all found URLS
        print(urls)

        # Limit the URLs for testing
        urls = urls[:3]
  
        # Print all unique URLs and extract their text content
        for url in urls:
            print(url)
            print(get_text(url))

    except Exception as e:
        print(f"An error occurred while crawling the URL: {e}")  # Handle exceptions
    finally:
        # Close the driver
        driver.quit()

if __name__ == '__main__':
    # Crawl a test URL and extract all hrefs
    crawl_url("https://www.spiegel.de")
