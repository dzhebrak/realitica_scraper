Extracts new (for last N days) real estate objects from the realitica.com in accordance with the specified criteria.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Replace `RealiticaSpider.start_urls` with list of your own start urls.

```bash
scrapy crawl realitica -o output_filename.csv -t csv
```