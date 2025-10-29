"""
Action Handler class implementation

Handles browser interactions including clicking, typing, scrolling, waiting,
and text extraction with robust error handling and element validation.
"""

import time
import logging
from typing import Optional, Union, Tuple, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    ElementClickInterceptedException, StaleElementReferenceException,
    InvalidSelectorException, WebDriverException
)

from ..core.exceptions import BrowserError


class ActionHandler:
    """
    Action Handler class for performing browser interactions.
    
    Provides methods for clicking, typing, scrolling, waiting, and text extraction
    with comprehensive error handling and element validation.
    """
    
    def __init__(self, driver: webdriver.Remote):
        """
        Initialize action handler with WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance
            
        Raises:
            BrowserError: If driver is None or invalid
        """
        if not driver:
            raise BrowserError(
                "Cannot initialize ActionHandler: WebDriver is None",
                browser_state="invalid_driver"
            )
        
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.default_timeout = 10
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
        self.logger.debug("ActionHandler initialized successfully")
    
    def click_element(self, selector: str, timeout: int = None, 
                     coordinates: Tuple[int, int] = None) -> bool:
        """
        Click an element by selector or coordinates.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            timeout: Maximum time to wait for element (uses default if None)
            coordinates: Optional (x, y) coordinates for direct clicking
            
        Returns:
            bool: True if click was successful
            
        Raises:
            BrowserError: If element cannot be found or clicked
        """
        timeout = timeout or self.default_timeout
        
        try:
            if coordinates:
                return self._click_by_coordinates(coordinates)
            else:
                return self._click_by_selector(selector, timeout)
                
        except Exception as e:
            raise BrowserError(
                f"Failed to click element: {selector}",
                action_type="click",
                target=selector,
                browser_state="active",
                context={"timeout": timeout, "coordinates": coordinates},
                original_exception=e
            )
    
    def fill_form_field(self, selector: str, value: str, timeout: int = None,
                       clear_first: bool = True) -> bool:
        """
        Fill a form field with the specified value.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            value: Text value to enter
            timeout: Maximum time to wait for element
            clear_first: Whether to clear field before typing
            
        Returns:
            bool: True if text was entered successfully
            
        Raises:
            BrowserError: If element cannot be found or text cannot be entered
        """
        timeout = timeout or self.default_timeout
        
        if not isinstance(value, str):
            value = str(value)
        
        for attempt in range(self.retry_attempts):
            try:
                element = self._find_element_with_wait(selector, timeout)
                
                # Validate element is interactable
                if not element.is_enabled():
                    raise BrowserError(
                        f"Form field is not enabled: {selector}",
                        action_type="type",
                        target=selector,
                        browser_state="active"
                    )
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Clear field if requested
                if clear_first:
                    element.clear()
                    time.sleep(0.2)
                
                # Enter text
                element.send_keys(value)
                
                # Verify text was entered
                entered_value = element.get_attribute('value') or element.text
                if value in entered_value or entered_value in value:
                    self.logger.debug(f"Successfully filled form field: {selector}")
                    return True
                else:
                    self.logger.warning(f"Text verification failed for field: {selector}")
                
                return True
                
            except StaleElementReferenceException:
                if attempt < self.retry_attempts - 1:
                    self.logger.debug(f"Stale element, retrying... (attempt {attempt + 1})")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    self.logger.debug(f"Fill field attempt {attempt + 1} failed, retrying...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise BrowserError(
                        f"Failed to fill form field: {selector}",
                        action_type="type",
                        target=selector,
                        browser_state="active",
                        context={"value": value, "timeout": timeout, "clear_first": clear_first},
                        original_exception=e
                    )
        
        return False
    
    def scroll_page(self, direction: str, amount: int = 1, 
                   element_selector: str = None) -> bool:
        """
        Scroll the page or a specific element.
        
        Args:
            direction: Scroll direction ("up", "down", "left", "right")
            amount: Number of scroll units (pixels or wheel steps)
            element_selector: Optional selector for element to scroll
            
        Returns:
            bool: True if scroll was successful
            
        Raises:
            BrowserError: If scroll operation fails
        """
        direction = direction.lower()
        valid_directions = ["up", "down", "left", "right"]
        
        if direction not in valid_directions:
            raise BrowserError(
                f"Invalid scroll direction: {direction}",
                action_type="scroll",
                target=element_selector or "page",
                context={"valid_directions": valid_directions}
            )
        
        try:
            if element_selector:
                return self._scroll_element(element_selector, direction, amount)
            else:
                return self._scroll_page(direction, amount)
                
        except Exception as e:
            raise BrowserError(
                f"Failed to scroll {direction}",
                action_type="scroll",
                target=element_selector or "page",
                browser_state="active",
                context={"direction": direction, "amount": amount},
                original_exception=e
            )
    
    def wait_for_element(self, selector: str, timeout: int = 10,
                        condition: str = "presence") -> bool:
        """
        Wait for an element to meet specified condition.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            timeout: Maximum time to wait in seconds
            condition: Wait condition ("presence", "visible", "clickable")
            
        Returns:
            bool: True if element condition is met within timeout
            
        Raises:
            BrowserError: If element condition is not met within timeout
        """
        valid_conditions = ["presence", "visible", "clickable"]
        
        if condition not in valid_conditions:
            raise BrowserError(
                f"Invalid wait condition: {condition}",
                action_type="wait",
                target=selector,
                context={"valid_conditions": valid_conditions}
            )
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            by_locator = self._get_by_locator(selector)
            
            if condition == "presence":
                wait.until(EC.presence_of_element_located(by_locator))
            elif condition == "visible":
                wait.until(EC.visibility_of_element_located(by_locator))
            elif condition == "clickable":
                wait.until(EC.element_to_be_clickable(by_locator))
            
            self.logger.debug(f"Element condition '{condition}' met for: {selector}")
            return True
            
        except TimeoutException:
            raise BrowserError(
                f"Element condition '{condition}' not met within {timeout}s: {selector}",
                action_type="wait",
                target=selector,
                browser_state="active",
                context={"timeout": timeout, "condition": condition}
            )
        except Exception as e:
            raise BrowserError(
                f"Failed to wait for element: {selector}",
                action_type="wait",
                target=selector,
                browser_state="active",
                context={"timeout": timeout, "condition": condition},
                original_exception=e
            )
    
    def extract_text(self, selector: str, timeout: int = None,
                    attribute: str = None) -> str:
        """
        Extract text content from an element.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            timeout: Maximum time to wait for element
            attribute: Optional attribute name to extract instead of text
            
        Returns:
            str: Extracted text content or attribute value
            
        Raises:
            BrowserError: If element cannot be found or text cannot be extracted
        """
        timeout = timeout or self.default_timeout
        
        try:
            element = self._find_element_with_wait(selector, timeout)
            
            if attribute:
                text = element.get_attribute(attribute)
                if text is None:
                    text = ""
            else:
                text = element.text.strip()
                
                # If no text content, try getting value attribute (for input fields)
                if not text:
                    value = element.get_attribute('value')
                    if value:
                        text = value.strip()
            
            self.logger.debug(f"Extracted text from {selector}: {len(text)} characters")
            return text
            
        except Exception as e:
            raise BrowserError(
                f"Failed to extract text from element: {selector}",
                action_type="extract",
                target=selector,
                browser_state="active",
                context={"timeout": timeout, "attribute": attribute},
                original_exception=e
            )
    
    def extract_multiple_elements(self, selector: str, timeout: int = None,
                                 attribute: str = None) -> List[str]:
        """
        Extract text from multiple elements matching the selector.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            timeout: Maximum time to wait for elements
            attribute: Optional attribute name to extract instead of text
            
        Returns:
            List[str]: List of extracted text content or attribute values
            
        Raises:
            BrowserError: If elements cannot be found or text cannot be extracted
        """
        timeout = timeout or self.default_timeout
        
        try:
            # Wait for at least one element to be present
            self.wait_for_element(selector, timeout, "presence")
            
            elements = self._find_elements(selector)
            results = []
            
            for element in elements:
                try:
                    if attribute:
                        text = element.get_attribute(attribute) or ""
                    else:
                        text = element.text.strip()
                        if not text:
                            value = element.get_attribute('value')
                            if value:
                                text = value.strip()
                    
                    results.append(text)
                    
                except StaleElementReferenceException:
                    # Skip stale elements
                    continue
            
            self.logger.debug(f"Extracted text from {len(results)} elements matching: {selector}")
            return results
            
        except Exception as e:
            raise BrowserError(
                f"Failed to extract text from multiple elements: {selector}",
                action_type="extract",
                target=selector,
                browser_state="active",
                context={"timeout": timeout, "attribute": attribute},
                original_exception=e
            )
    
    def is_element_present(self, selector: str) -> bool:
        """
        Check if an element is present in the DOM.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            
        Returns:
            bool: True if element is present
        """
        try:
            self._find_element(selector)
            return True
        except (NoSuchElementException, InvalidSelectorException):
            return False
        except Exception:
            return False
    
    def is_element_visible(self, selector: str) -> bool:
        """
        Check if an element is visible on the page.
        
        Args:
            selector: CSS selector, XPath, or element identifier
            
        Returns:
            bool: True if element is visible
        """
        try:
            element = self._find_element(selector)
            return element.is_displayed()
        except (NoSuchElementException, InvalidSelectorException):
            return False
        except Exception:
            return False
    
    def _click_by_selector(self, selector: str, timeout: int) -> bool:
        """Click element by selector with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                element = self._find_element_with_wait(selector, timeout)
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Try regular click first
                try:
                    element.click()
                    self.logger.debug(f"Successfully clicked element: {selector}")
                    return True
                    
                except ElementClickInterceptedException:
                    # Try JavaScript click if regular click is intercepted
                    self.logger.debug(f"Regular click intercepted, trying JavaScript click: {selector}")
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                
            except StaleElementReferenceException:
                if attempt < self.retry_attempts - 1:
                    self.logger.debug(f"Stale element, retrying... (attempt {attempt + 1})")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    self.logger.debug(f"Click attempt {attempt + 1} failed, retrying...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise
        
        return False
    
    def _click_by_coordinates(self, coordinates: Tuple[int, int]) -> bool:
        """Click at specific coordinates."""
        try:
            x, y = coordinates
            action_chains = ActionChains(self.driver)
            action_chains.move_by_offset(x, y).click().perform()
            
            # Reset mouse position
            action_chains.move_by_offset(-x, -y).perform()
            
            self.logger.debug(f"Successfully clicked at coordinates: ({x}, {y})")
            return True
            
        except Exception as e:
            raise BrowserError(
                f"Failed to click at coordinates: {coordinates}",
                action_type="click",
                target=f"coordinates_{coordinates}",
                browser_state="active",
                original_exception=e
            )
    
    def _scroll_page(self, direction: str, amount: int) -> bool:
        """Scroll the entire page."""
        scroll_scripts = {
            "down": f"window.scrollBy(0, {amount * 100});",
            "up": f"window.scrollBy(0, -{amount * 100});",
            "right": f"window.scrollBy({amount * 100}, 0);",
            "left": f"window.scrollBy(-{amount * 100}, 0);"
        }
        
        script = scroll_scripts[direction]
        self.driver.execute_script(script)
        time.sleep(0.5)  # Allow scroll to complete
        
        self.logger.debug(f"Scrolled page {direction} by {amount} units")
        return True
    
    def _scroll_element(self, selector: str, direction: str, amount: int) -> bool:
        """Scroll a specific element."""
        element = self._find_element_with_wait(selector, self.default_timeout)
        
        scroll_scripts = {
            "down": f"arguments[0].scrollTop += {amount * 100};",
            "up": f"arguments[0].scrollTop -= {amount * 100};",
            "right": f"arguments[0].scrollLeft += {amount * 100};",
            "left": f"arguments[0].scrollLeft -= {amount * 100};"
        }
        
        script = scroll_scripts[direction]
        self.driver.execute_script(script, element)
        time.sleep(0.5)  # Allow scroll to complete
        
        self.logger.debug(f"Scrolled element {selector} {direction} by {amount} units")
        return True
    
    def _find_element_with_wait(self, selector: str, timeout: int) -> WebElement:
        """Find element with explicit wait."""
        wait = WebDriverWait(self.driver, timeout)
        by_locator = self._get_by_locator(selector)
        
        try:
            element = wait.until(EC.presence_of_element_located(by_locator))
            return element
        except TimeoutException:
            raise BrowserError(
                f"Element not found within {timeout}s: {selector}",
                action_type="find",
                target=selector,
                browser_state="active",
                context={"timeout": timeout}
            )
    
    def _find_element(self, selector: str) -> WebElement:
        """Find element without wait."""
        by_locator = self._get_by_locator(selector)
        return self.driver.find_element(*by_locator)
    
    def _find_elements(self, selector: str) -> List[WebElement]:
        """Find multiple elements."""
        by_locator = self._get_by_locator(selector)
        return self.driver.find_elements(*by_locator)
    
    def _get_by_locator(self, selector: str) -> Tuple[str, str]:
        """
        Convert selector string to Selenium By locator tuple.
        
        Args:
            selector: CSS selector, XPath, or other selector
            
        Returns:
            Tuple[str, str]: (By method, selector value)
        """
        # Determine selector type and return appropriate By locator
        if selector.startswith('//') or selector.startswith('('):
            return (By.XPATH, selector)
        elif selector.startswith('#'):
            return (By.ID, selector[1:])
        elif selector.startswith('.'):
            return (By.CLASS_NAME, selector[1:])
        elif '[' in selector and ']' in selector:
            return (By.CSS_SELECTOR, selector)
        elif selector.startswith('name='):
            return (By.NAME, selector[5:])
        elif selector.startswith('tag='):
            return (By.TAG_NAME, selector[4:])
        elif selector.startswith('link='):
            return (By.LINK_TEXT, selector[5:])
        elif selector.startswith('partial_link='):
            return (By.PARTIAL_LINK_TEXT, selector[13:])
        else:
            # Default to CSS selector
            return (By.CSS_SELECTOR, selector)