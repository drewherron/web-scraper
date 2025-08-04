import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
from collections import deque
import re
import mimetypes
import random
import argparse

# A set to keep track of URLs that have been visited
visited_urls = set()

# User agent to identify as a bot
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; WebsiteScraper/1.0; +http://example.com/bot)'
}

def sanitize_filename(path):
    """
    Sanitize a URL path to be a valid filename/path on the local filesystem.
    """
    # Remove query parameters and fragments
    path = path.split('?')[0].split('#')[0]

    # Decode URL encoding
    path = unquote(path)

    # Replace invalid characters
    path = re.sub(r'[<>:"|?*]', '_', path)

    return path

def get_file_extension(url, content_type):
    """
    Determine appropriate file extension based on URL and content type.
    """
    # First try to get extension from URL
    parsed = urlparse(url)
    path = parsed.path
    if '.' in path:
        return path.split('.')[-1].lower()

    # Fall back to content type
    if content_type:
        # Map common content types to extensions
        type_map = {
            'text/html': 'html',
            'text/css': 'css',
            'application/javascript': 'js',
            'text/javascript': 'js',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/svg+xml': 'svg',
            'application/pdf': 'pdf',
            'application/xml': 'xml',
            'text/xml': 'xml',
        }

        for mime, ext in type_map.items():
            if mime in content_type:
                return ext

    return 'html'  # Default to HTML

def process_css_content(css_content, current_url, domain_name, urls_to_visit):
    """
    Process CSS content to find and rewrite URLs in @import and url() statements.
    """
    # Pattern to find URLs in CSS
    url_pattern = r'(@import\s+["\']?|url\s*\(\s*["\']?)([^"\'\)]+)(["\']?\s*\)?)'

    def replace_url(match):
        prefix = match.group(1)
        url = match.group(2)
        suffix = match.group(3)

        # Make URL absolute
        absolute_url = urljoin(current_url, url)
        parsed = urlparse(absolute_url)

        # Check if it's within our domain
        if parsed.netloc == domain_name:
            if absolute_url not in visited_urls:
                urls_to_visit.append(absolute_url)

            # Convert to relative path
            # This is simplified - in production you'd calculate the actual relative path
            relative_path = parsed.path.lstrip('/')
            if parsed.query:
                relative_path += '?' + parsed.query

            return prefix + relative_path + suffix
        else:
            # Keep external URLs as-is
            return match.group(0)

    return re.sub(url_pattern, replace_url, css_content)

def scrape_website(base_url, max_retries=3, delay=0.5, randomize=0):
    """
    Scrapes a website recursively, downloading all local content and rewriting links.
    """
    # Parse the base URL to get the domain name
    domain_name = urlparse(base_url).netloc
    output_dir = domain_name

    # Create the main output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # Use a deque as a queue for URLs to visit
    urls_to_visit = deque([base_url])

    while urls_to_visit:
        current_url = urls_to_visit.popleft()

        # If we have already processed this URL, skip it
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)
        print(f"Processing: {current_url}")

        # Add delay to be respectful to the server
        if delay > 0:
            actual_delay = delay
            if randomize > 0:
                # Add random variation to the delay
                actual_delay = delay + random.uniform(-randomize, randomize)
                actual_delay = max(0.1, actual_delay)  # Ensure minimum delay of 0.1s
            time.sleep(actual_delay)

        # Try to fetch the URL with retries
        response = None
        for attempt in range(max_retries):
            try:
                response = requests.get(current_url, headers=HEADERS, timeout=30, allow_redirects=True)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"Error fetching {current_url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    continue  # Skip this URL

        if not response:
            continue

        # Handle redirects by updating current_url
        if response.history:
            current_url = response.url
            print(f"  Redirected to: {current_url}")

        # Create a local path that mirrors the website's structure
        parsed_url = urlparse(current_url)
        local_path = sanitize_filename(parsed_url.path.lstrip('/'))

        if not local_path:
            local_path = 'index.html'

        local_path = os.path.join(output_dir, local_path)

        # Determine content type
        content_type = response.headers.get('content-type', '').lower()

        # If path doesn't have an extension, add one based on content type
        if '.' not in os.path.basename(local_path):
            ext = get_file_extension(current_url, content_type)
            if ext != 'html' or 'text/html' in content_type:
                local_path += f'.{ext}'

        # Ensure the local directory exists
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # Process based on content type
        if 'text/html' in content_type:
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all tags that can contain links
            link_attrs = {
                'a': 'href',
                'link': 'href',
                'img': 'src',
                'script': 'src',
                'source': 'src',
                'video': 'src',
                'audio': 'src',
                'iframe': 'src',
                'embed': 'src',
                'object': 'data',
                'form': 'action',
            }

            for tag_name, attr_name in link_attrs.items():
                for tag in soup.find_all(tag_name):
                    if tag.has_attr(attr_name):
                        link = tag[attr_name]
                        if not link or link.startswith('javascript:') or link.startswith('mailto:'):
                            continue

                        # Make link absolute
                        absolute_link = urljoin(current_url, link)
                        parsed_link = urlparse(absolute_link)

                        # Check if within domain
                        if parsed_link.netloc == domain_name:
                            clean_url = absolute_link.split('#')[0]  # Remove fragments
                            if clean_url not in visited_urls:
                                urls_to_visit.append(clean_url)

                            # Calculate relative path
                            target_path = sanitize_filename(parsed_link.path.lstrip('/'))
                            if not target_path:
                                target_path = 'index.html'

                            # Add extension if needed
                            if '.' not in os.path.basename(target_path) and tag_name in ['img', 'script', 'link']:
                                # This is simplified - ideally we'd HEAD request to check type
                                if tag_name == 'img':
                                    target_path += '.jpg'  # Assume jpg, will be corrected when downloaded
                                elif tag_name == 'script':
                                    target_path += '.js'
                                elif tag_name == 'link' and 'stylesheet' in str(tag.get('rel', '')):
                                    target_path += '.css'

                            target_full_path = os.path.join(output_dir, target_path)
                            relative_path = os.path.relpath(target_full_path, start=local_dir or output_dir)
                            relative_path = relative_path.replace('\\', '/')  # Ensure forward slashes

                            tag[attr_name] = relative_path

            # Also process inline styles for URLs
            for tag in soup.find_all(style=True):
                style = tag['style']
                if 'url(' in style:
                    # Simple URL extraction from inline styles
                    tag['style'] = process_css_content(style, current_url, domain_name, urls_to_visit)

            # Save the modified HTML
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))

        elif 'text/css' in content_type:
            # Process CSS files
            css_content = response.text
            processed_css = process_css_content(css_content, current_url, domain_name, urls_to_visit)

            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(processed_css)

        else:
            # Binary files (images, PDFs, etc.)
            with open(local_path, 'wb') as f:
                f.write(response.content)

    print(f"\nScraping complete!")
    print(f"Website saved to '{output_dir}' directory.")
    print(f"Total URLs processed: {len(visited_urls)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Recursively scrape a website and save it for offline viewing.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python scrape_website.py https://example.com

  # Slow, gentle scraping with 2 second delays
  python scrape_website.py https://example.com --delay 2

  # Human-like scraping with randomized delays (1-3 seconds)
  python scrape_website.py https://example.com --delay 2 --randomize 1
        """
    )

    parser.add_argument('url', help='The URL to start scraping from')
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--randomize', '-r',
        type=float,
        default=0,
        help='Randomization range for delay in seconds. The actual delay will be: delay ± randomize'
    )

    args = parser.parse_args()

    # Validate URL
    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print(f"Error: '{args.url}' is not a valid URL.")
        print("Please include the protocol (http:// or https://)")
        sys.exit(1)

    # Validate delay arguments
    if args.delay < 0:
        print("Error: Delay must be non-negative")
        sys.exit(1)

    if args.randomize < 0:
        print("Error: Randomize must be non-negative")
        sys.exit(1)

    if args.randomize > args.delay:
        print("Warning: Randomization range is larger than delay. This may result in very short delays.")

    print(f"Starting scrape of {args.url}")
    print(f"Delay: {args.delay}s" + (f" ± {args.randomize}s" if args.randomize > 0 else ""))
    print()

    scrape_website(args.url, delay=args.delay, randomize=args.randomize)
