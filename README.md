# Basic Web Scraper

This is a recursive website scraper that downloads entire websites for offline viewing while preserving the original structure and (hopefully) functionality.

Probably worthless, since you can just use `wget` or `scrapy`, but... here's another option.

## Features

- **Recursive downloading**: Automatically follows and downloads all linked pages within the same domain
- **Structure preservation**: Maintains the original directory structure for offline browsing
- **Link rewriting**: Automatically updates all internal links to work with local files
- **Resource handling**: Downloads all images, PDFs, CSS files, JavaScript, and other assets
- **Respectful scraping**: Configurable delays between requests with optional randomization to avoid overwhelming servers
- **CSS processing**: Parses and updates URLs within CSS files and inline styles
- **Smart retry logic**: Automatically retries failed downloads with exponential backoff
- **Domain boundary**: Stays within the target domain, won't follow external links

## Usage

### Basic usage:
```bash
python web_scraper.py https://example.com
```

### With custom delay between requests:
```bash
python web_scraper.py https://example.com --delay 2
```

### With randomized delays:
```bash
python web_scraper.py https://example.com --delay 2 --randomize 0.5
```
This will create delays between 1.5 and 2.5 seconds (2 ± 0.5).

### Command-line Arguments

- `url` (required): The starting URL to scrape
- `--delay`, `-d`: Delay between requests in seconds (default: 0.5)
- `--randomize`, `-r`: Randomization range for delay in seconds (default: 0)

## How It Works

1. **Starting Point**: The scraper begins at the URL you provide
2. **Page Processing**: Each HTML page is downloaded and parsed for links
3. **Link Discovery**: All links to the same domain are added to the download queue
4. **Resource Downloading**: Images, CSS, JavaScript, PDFs, and other files are downloaded
5. **Link Rewriting**: All links in HTML and CSS files are rewritten to work locally
6. **Directory Structure**: Files are saved matching the original URL structure

## Limitations

- **JavaScript-rendered content**: Sites that load content dynamically with JavaScript won't be fully captured
- **Login-protected content**: Cannot access content behind authentication
- **Very large sites**: May take a very long time for sites with thousands of pages
- **Streaming content**: Videos and audio streams are not downloaded

## Disclaimer

This tool is provided as-is for educational and archival purposes. Users are responsible for ensuring their use complies with applicable laws, regulations, and website terms of service. Author not responsible for misuse.
