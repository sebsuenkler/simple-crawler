import socket
from urllib.parse import urlparse
from selenium.webdriver.common.by import By  # Used to locate elements by their tag name
from seleniumbase import Driver  # SeleniumBase's Driver to manage the WebDriver session
import time  # Used for sleep pauses in scrolling
import os  # Used to handle paths
import inspect  # Used to inspect the current script's path
from bs4 import BeautifulSoup  # Used to parse the HTML and extract text
import re  # Regular expressions for cleaning up text
import requests  # For handling HTTP requests
import csv
import sys


# Define the path for configurations and extensions
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))  # Get the current script directory
ext_path = os.path.join(currentdir, "i_care_about_cookies_unpacked")  # Path to the cookie consent extension


def create_webdriver():
    """
    Initializes and returns a Selenium WebDriver instance with specified settings.

    Returns:
        driver: A Selenium WebDriver instance configured for Chrome with specific options.
    """
    try:
        # Initialize the WebDriver with the specified configuration
        driver = Driver(
            browser="chrome",          # Use Chrome as the browser
            wire=True,                 # Enable wire mode for undetectable Chrome
            uc=True,                   # Use undetected Chrome mode
            headless2=True,            # Run in headless mode (no GUI)
            incognito=False,           # Disable incognito mode
            agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",  # User agent
            do_not_track=True,         # Enable 'Do Not Track' header
            undetectable=True,         # Make the browser undetectable by bot detection
            locale_code="de",          # Set locale to German
            extension_dir=ext_path,    # Path to the cookie consent extension
            no_sandbox=True            # Disable sandboxing for performance
        )
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return None  # Return None if driver initialization fails


def get_result_meta(url):
    """
    Retrieves metadata for a given URL, including its IP address and main URL.

    Args:
        url (str): The URL to retrieve metadata for.

    Returns:
        dict: A dictionary containing 'ip' (IP address) and 'main' (main URL).
    """
    try:
        parsed_uri = urlparse(url)  # Parse the URL to extract the hostname
        hostname = parsed_uri.netloc
        ip = socket.gethostbyname(hostname)  # Resolve the IP address for the hostname
    except Exception:
        ip = "-1"  # If an error occurs, set IP to "-1"
    
    main = f'{parsed_uri.scheme}://{parsed_uri.netloc}/' if parsed_uri.netloc else url  # Construct base URL

    return {"ip": ip, "main": main}


def get_url_header(url):
    """
    Retrieves the HTTP headers and status code for a given URL.

    Args:
        url (str): The URL to retrieve headers for.

    Returns:
        dict: A dictionary containing 'content_type' and 'status_code'.
    """
    driver = create_webdriver()  # Initialize WebDriver
    if driver is None:
        return {}  # Exit if the WebDriver couldn't be initialized

    try:
        # Get metadata such as main URL for filtering requests
        meta = get_result_meta(url)
        main = meta.get("main", "")

        content_type = ""
        status_code = -1

        try:
            # Perform an HTTP GET request to retrieve the status and headers
            response = requests.get(url, verify=False, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            })
            status_code = response.status_code
            
            try:
                headers = requests.head(url, timeout=3).headers
                content_type = headers.get('Content-Type', "")
            except Exception:
                if any(tag in response.text.lower() for tag in ["!doctype html", "/html>"]):
                    content_type = "html"  # Assume HTML if tags are detected

        except Exception:
            import mimetypes
            mt = mimetypes.guess_type(url)  # Guess the content type based on URL
            if mt:
                content_type = mt[0]

        # If status code is a redirect (302) or forbidden (403), treat it as successful (200)
        if status_code in [302, 403]:
            status_code = 200

        # Check if the WebDriver intercepted any network requests matching the URL
        if status_code not in [200, -1]:
            try:
                for request in driver.requests:
                    if main in request.url:
                        status_code = request.response.status_code
                        content_type = request.response.headers.get('Content-Type', "")
                        if status_code in [200, 302]:
                            break
            except Exception as e:
                print(f"Error processing requests: {e}")

        # Fallback handling for missing content type
        if not content_type:
            if "binary" in content_type or "json" in content_type or "plain" in content_type:
                content_type = "html"  # Assume it's HTML if no clear type
            else:
                content_type = "error"  # Unknown content type

        return {"content_type": content_type, "status_code": status_code}
    
    finally:
        driver.quit()  # Close the WebDriver instance


def infinite_scroll(driver, pause_time=2):
    """
    Simulates scrolling to the bottom of a page multiple times to load dynamic content.

    Args:
        driver: The Selenium WebDriver instance.
        pause_time: Time to wait after each scroll for content to load.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")  # Get initial scroll height

    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        time.sleep(pause_time)  # Wait for new content to load
        
        new_height = driver.execute_script("return document.body.scrollHeight")  # Check new scroll height
        
        if new_height == last_height:  # Stop if no new content was loaded
            break
        last_height = new_height  # Update last height for the next scroll


def get_text(url):
    """
    Extracts all visible text from a given URL after scrolling to the bottom of the page.

    Args:
        url (str): The URL of the page to extract text from.
    """
    driver = create_webdriver()  # Initialize WebDriver
    if driver is None:
        return  # Exit if WebDriver initialization fails

    try:
        driver.get(url)  # Open the URL in the browser
        infinite_scroll(driver)  # Scroll to load dynamic content

        code = driver.page_source  # Get the full HTML of the page
        soup = BeautifulSoup(code, features="lxml")  # Parse the HTML with BeautifulSoup
        
        text = soup.get_text()  # Extract visible text
        text = re.sub(r'\n\s*\n', r'\n\n', text.strip(), flags=re.M)  # Clean up whitespace

        print(text)  # Output the extracted text
    finally:
        driver.quit()  # Close the WebDriver instance


def crawl_url(url, dict_request, url_kw):
    """
    Crawls the given URL and extracts all 'href' attributes from anchor tags.

    Args:
        url (str): The URL of the webpage to crawl.
        dict_request (dict): A dictionary with URL metadata (status code, content type).

    Returns:
        list: A list of unique URLs (hrefs) extracted from the page.
    """
    driver = create_webdriver()  # Initialize WebDriver
    if driver is None:
        return []  # Return empty list if WebDriver initialization fails

    try:
        driver.get(url)  # Open the URL in the browser

        if (dict_request["status_code"] == 200 or dict_request["status_code"] == 302) and "html" in dict_request["content_type"]:
            infinite_scroll(driver)  # Scroll to load dynamic content

            meta = get_result_meta(url)  # Get metadata such as main URL
            main = meta['main'].replace("www.", "")  # Normalize URLs by removing 'www.'
            main_www = meta['main']

            anchor_tags = driver.find_elements(By.TAG_NAME, "a")  # Find all anchor tags

            hrefs = [tag.get_attribute('href') for tag in anchor_tags if tag.get_attribute('href')]  # Get 'href' attributes

            # Process and filter valid URLs
            urls = []
            for href in hrefs:
                if 'http' not in href:
                    href = main + href  # Handle relative URLs
                if (main in href or main_www in href) and "javascript:void(0)" not in href and "#" not in href and "mailto:" not in href and url_kw in href:  # Only include URLs from the main domain
                    urls.append(href)
            
            return list(dict.fromkeys(urls))  # Remove duplicates by converting list to dict then back to list
        else:
            return []
    except Exception as e:
        print(f"Error crawling URL: {e}")
        return []
    finally:
        driver.quit()  # Close the WebDriver instance


def crawl_sub_urls(urls, crawled_urls, url_kw):
    """
    Recursively crawls sub-URLs found on a webpage, avoiding duplicates.

    Args:
        urls (list): A list of URLs to crawl.
        crawled_urls (list): A list of already crawled URLs to avoid duplicates.

    Returns:
        tuple: A tuple containing two lists - new result URLs and updated crawled URLs.
    """
    result_urls = []
    for url in urls:
        if url not in crawled_urls:  # Avoid re-crawling already processed URLs
            try:
                dict_request = get_url_header(url)  # Get URL metadata
                print(dict_request)

                if (dict_request["status_code"] == 200 or dict_request["status_code"] == 302) and "html" in dict_request["content_type"]:
                    print(f"Crawling: {url}")

                    result_urls.append(url)  # Add URL to results
                    
                    new_urls = crawl_url(url, dict_request, url_kw)  # Crawl the URL and get new URLs
                    
                    crawled_urls.append(url)  # Mark URL as crawled
                    
                    result_urls.extend(new_urls)  # Add new URLs to results
            except Exception as e:
                print(f"Error crawling sub-URL {url}: {e}")
                pass

    return list(dict.fromkeys(result_urls)), list(dict.fromkeys(crawled_urls))  # Remove duplicates and return results


if __name__ == '__main__':
    # Initial URL to crawl

    # Check if enough arguments are provided
    if len(sys.argv) != 3:
        print("Usage: python crawler.py <url> <url_kw>")
        sys.exit(1)  # Exit with an error status

    # Get the URL from the command-line argument
    url = [sys.argv[1]]
    url_kw = sys.argv[2]


    file_name = url[0].replace("https://", "").replace("www.", "").replace(".html", "").replace("/","_").replace("#","_").replace("?","_")+".csv"                                                           

    dict_request = get_url_header(url[0])

    try:
        # Level 0 URLs: Just the URLs from the given main URL
        level_0_urls = crawl_url(url[0], dict_request, url_kw)
        crawled_level_0_urls = [url[0]]  # Store the main URL as already crawled
    except:
        level_0_urls = []
        crawled_level_0_urls = []

    try:
        # Level 1 URLs: Crawl sub-URLs found on level 0 URLs
        level_1_urls, crawled_level_1_urls = crawl_sub_urls(level_0_urls, crawled_level_0_urls, url_kw)
    except:
        level_1_urls = []
        crawled_level_1_urls = []

    # try:
    #     # Level 2 URLs: Crawl sub-URLs found on level 1 URLs
    #     level_2_urls, crawled_level_2_urls = crawl_sub_urls(level_1_urls, crawled_level_1_urls, url_kw)
    # except:
    #     level_2_urls = []
    #     crawled_level_2_urls = []

    # try:
    #     # Level 3 URLs: Crawl sub-URLs found on level 1 URLs
    #     level_3_urls, crawled_level_3_urls = crawl_sub_urls(level_2_urls, crawled_level_2_urls, url_kw)   
    # except:
    #     level_3_urls = []
    #     crawled_level_3_urls = []

    # try:
    #     # Level 4 URLs: Crawl sub-URLs found on level 1 URLs
    #     level_4_urls, crawled_level_4_urls = crawl_sub_urls(level_3_urls, crawled_level_3_urls, url_kw)        
    # except:
    #     level_4_urls = []
    #     crawled_level_4_urls = []

    # Combine all URLs across levels, removing duplicates
    final_urls = list(dict.fromkeys(url + level_0_urls + level_1_urls))

    # Print the final list of unique URLs and their count
    print(final_urls)
    print(f"Total URLs: {len(final_urls)}")    

    # Open the CSV file in write mode ('w'), this will overwrite any existing file
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Iterate over each final_url
        for final_url in final_urls:
            # Write each URL as a new row
            writer.writerow([final_url])