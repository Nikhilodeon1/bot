"""
Web Scraper class implementation

Provides structured data scraping methods with CSS selectors, link extraction,
metadata parsing capabilities, and file download functionality.
"""

import os
import re
import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ..core.exceptions import BrowserError


class WebScraper:
    """
    Web Scraper class for extracting structured data from web pages.
    
    Provides methods for scraping structured data using CSS selectors,
    extracting links with optional filtering, parsing page metadata,
    and downloading files from URLs.
    """
    
    def __init__(self, driver: Optional[WebDriver] = None):
        """
        Initialize web scraper with optional WebDriver instance.
        
        Args:
            driver: Optional Selenium WebDriver instance for browser-based scraping
        """
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # Set up session headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        self.logger.info("WebScraper initialized")
    
    def scrape_structured_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Scrape structured data from the current page using CSS selectors.
        
        Args:
            selectors: Dictionary mapping field names to CSS selectors
            
        Returns:
            Dict containing scraped data with field names as keys
            
        Raises:
            BrowserError: If browser is not available or scraping fails
        """
        if not self.driver:
            raise BrowserError(
                "Cannot scrape structured data: WebDriver not available",
                browser_state="no_driver",
                context={"selectors": list(selectors.keys())}
            )
        
        try:
            scraped_data = {}
            
            for field_name, selector in selectors.items():
                try:
                    # Find elements using CSS selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if not elements:
                        self.logger.warning(f"No elements found for selector '{selector}' (field: {field_name})")
                        scraped_data[field_name] = None
                        continue
                    
                    # Extract data based on number of elements found
                    if len(elements) == 1:
                        # Single element - extract text, attribute, or value
                        element = elements[0]
                        scraped_data[field_name] = self._extract_element_data(element)
                    else:
                        # Multiple elements - extract as list
                        scraped_data[field_name] = [
                            self._extract_element_data(element) for element in elements
                        ]
                    
                    self.logger.debug(f"Scraped field '{field_name}': {len(elements)} elements found")
                    
                except Exception as e:
                    self.logger.error(f"Error scraping field '{field_name}' with selector '{selector}': {e}")
                    scraped_data[field_name] = None
            
            self.logger.info(f"Structured data scraping completed: {len(scraped_data)} fields processed")
            return scraped_data
            
        except Exception as e:
            raise BrowserError(
                "Failed to scrape structured data",
                browser_state="active",
                context={"selectors": list(selectors.keys())},
                original_exception=e
            )
    
    def extract_links(self, filter_pattern: str = None) -> List[str]:
        """
        Extract all links from the current page with optional filtering.
        
        Args:
            filter_pattern: Optional regex pattern to filter links
            
        Returns:
            List of URLs found on the page
            
        Raises:
            BrowserError: If browser is not available or link extraction fails
        """
        if not self.driver:
            raise BrowserError(
                "Cannot extract links: WebDriver not available",
                browser_state="no_driver",
                context={"filter_pattern": filter_pattern}
            )
        
        try:
            # Get current page URL for resolving relative links
            current_url = self.driver.current_url
            
            # Find all anchor elements with href attributes
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            
            links = []
            compiled_pattern = None
            
            if filter_pattern:
                try:
                    compiled_pattern = re.compile(filter_pattern)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{filter_pattern}': {e}")
                    compiled_pattern = None
            
            for element in link_elements:
                try:
                    href = element.get_attribute("href")
                    if not href:
                        continue
                    
                    # Convert relative URLs to absolute URLs
                    absolute_url = urljoin(current_url, href)
                    
                    # Apply filter if provided
                    if compiled_pattern:
                        if not compiled_pattern.search(absolute_url):
                            continue
                    
                    # Avoid duplicates
                    if absolute_url not in links:
                        links.append(absolute_url)
                        
                except Exception as e:
                    self.logger.debug(f"Error processing link element: {e}")
                    continue
            
            self.logger.info(f"Extracted {len(links)} links from page")
            if filter_pattern:
                self.logger.debug(f"Applied filter pattern: {filter_pattern}")
            
            return links
            
        except Exception as e:
            raise BrowserError(
                "Failed to extract links from page",
                browser_state="active",
                context={"filter_pattern": filter_pattern},
                original_exception=e
            )
    
    def get_page_metadata(self) -> Dict[str, str]:
        """
        Extract metadata from the current page (title, description, keywords, etc.).
        
        Returns:
            Dict containing page metadata
            
        Raises:
            BrowserError: If browser is not available or metadata extraction fails
        """
        if not self.driver:
            raise BrowserError(
                "Cannot get page metadata: WebDriver not available",
                browser_state="no_driver"
            )
        
        try:
            metadata = {}
            
            # Extract page title
            try:
                metadata['title'] = self.driver.title or ""
            except Exception:
                metadata['title'] = ""
            
            # Extract current URL
            try:
                metadata['url'] = self.driver.current_url or ""
            except Exception:
                metadata['url'] = ""
            
            # Extract meta tags
            meta_selectors = {
                'description': 'meta[name="description"]',
                'keywords': 'meta[name="keywords"]',
                'author': 'meta[name="author"]',
                'robots': 'meta[name="robots"]',
                'viewport': 'meta[name="viewport"]',
                'charset': 'meta[charset]',
                'og:title': 'meta[property="og:title"]',
                'og:description': 'meta[property="og:description"]',
                'og:image': 'meta[property="og:image"]',
                'og:url': 'meta[property="og:url"]',
                'twitter:title': 'meta[name="twitter:title"]',
                'twitter:description': 'meta[name="twitter:description"]',
                'twitter:image': 'meta[name="twitter:image"]'
            }
            
            for meta_name, selector in meta_selectors.items():
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content = elements[0].get_attribute("content")
                        if content:
                            metadata[meta_name] = content
                        elif meta_name == 'charset':
                            # For charset meta tag, get the charset attribute
                            charset = elements[0].get_attribute("charset")
                            if charset:
                                metadata[meta_name] = charset
                except Exception as e:
                    self.logger.debug(f"Error extracting meta tag '{meta_name}': {e}")
            
            # Extract canonical URL
            try:
                canonical_elements = self.driver.find_elements(By.CSS_SELECTOR, 'link[rel="canonical"]')
                if canonical_elements:
                    canonical_url = canonical_elements[0].get_attribute("href")
                    if canonical_url:
                        metadata['canonical'] = canonical_url
            except Exception as e:
                self.logger.debug(f"Error extracting canonical URL: {e}")
            
            # Extract language
            try:
                html_elements = self.driver.find_elements(By.TAG_NAME, "html")
                if html_elements:
                    lang = html_elements[0].get_attribute("lang")
                    if lang:
                        metadata['language'] = lang
            except Exception as e:
                self.logger.debug(f"Error extracting language: {e}")
            
            self.logger.info(f"Extracted page metadata: {len(metadata)} fields")
            return metadata
            
        except Exception as e:
            raise BrowserError(
                "Failed to extract page metadata",
                browser_state="active",
                original_exception=e
            )
    
    def download_file(self, url: str, destination: str) -> bool:
        """
        Download a file from the specified URL to the destination path.
        
        Args:
            url: URL of the file to download
            destination: Local file path where the file should be saved
            
        Returns:
            bool: True if download was successful, False otherwise
            
        Raises:
            BrowserError: If download fails due to network or file system errors
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise BrowserError(
                    f"Invalid URL format: {url}",
                    context={"url": url, "destination": destination}
                )
            
            # Create destination directory if it doesn't exist
            destination_dir = os.path.dirname(destination)
            if destination_dir and not os.path.exists(destination_dir):
                os.makedirs(destination_dir, exist_ok=True)
            
            self.logger.info(f"Starting download from {url} to {destination}")
            
            # Download file with streaming to handle large files
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check content type and size
            content_type = response.headers.get('content-type', '')
            content_length = response.headers.get('content-length')
            
            if content_length:
                file_size = int(content_length)
                self.logger.debug(f"File size: {file_size} bytes, Content-Type: {content_type}")
            
            # Write file in chunks
            chunk_size = 8192
            total_downloaded = 0
            
            with open(destination, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        file.write(chunk)
                        total_downloaded += len(chunk)
            
            # Verify file was written
            if os.path.exists(destination) and os.path.getsize(destination) > 0:
                self.logger.info(f"Successfully downloaded {total_downloaded} bytes to {destination}")
                return True
            else:
                self.logger.error(f"Download failed: file not created or empty")
                return False
                
        except requests.exceptions.RequestException as e:
            raise BrowserError(
                f"Network error downloading file from {url}",
                context={"url": url, "destination": destination, "error_type": "network"},
                original_exception=e
            )
        except OSError as e:
            raise BrowserError(
                f"File system error saving to {destination}",
                context={"url": url, "destination": destination, "error_type": "filesystem"},
                original_exception=e
            )
        except Exception as e:
            raise BrowserError(
                f"Unexpected error downloading file from {url}",
                context={"url": url, "destination": destination, "error_type": "unknown"},
                original_exception=e
            )
    
    def _extract_element_data(self, element) -> Any:
        """
        Extract data from a web element based on its type and attributes.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Extracted data (text, attribute value, or structured data)
        """
        try:
            tag_name = element.tag_name.lower()
            
            # Handle different element types
            if tag_name in ['input', 'textarea']:
                # For form elements, get the value
                value = element.get_attribute('value')
                return value if value is not None else element.text
            
            elif tag_name == 'img':
                # For images, get src and alt attributes
                return {
                    'src': element.get_attribute('src'),
                    'alt': element.get_attribute('alt'),
                    'title': element.get_attribute('title')
                }
            
            elif tag_name == 'a':
                # For links, get href and text
                return {
                    'href': element.get_attribute('href'),
                    'text': element.text.strip(),
                    'title': element.get_attribute('title')
                }
            
            elif tag_name in ['select']:
                # For select elements, get selected option
                try:
                    from selenium.webdriver.support.ui import Select
                    select = Select(element)
                    selected_option = select.first_selected_option
                    return {
                        'value': selected_option.get_attribute('value'),
                        'text': selected_option.text
                    }
                except Exception:
                    return element.text.strip()
            
            else:
                # For other elements, get text content
                text = element.text.strip()
                
                # If no text, try to get useful attributes
                if not text:
                    for attr in ['data-value', 'value', 'title', 'alt']:
                        attr_value = element.get_attribute(attr)
                        if attr_value:
                            return attr_value
                
                return text
                
        except Exception as e:
            self.logger.debug(f"Error extracting element data: {e}")
            return None
    
    def set_driver(self, driver: WebDriver) -> None:
        """
        Set the WebDriver instance for browser-based scraping.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.logger.debug("WebDriver instance updated")
    
    def close_session(self) -> None:
        """Close the requests session and cleanup resources."""
        if self.session:
            self.session.close()
            self.logger.debug("Requests session closed")