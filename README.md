# Roody Research Engine

## Overview

Roody Research Engine is a comprehensive academic paper search tool built with Streamlit that allows users to search for research papers across multiple academic databases, including:

- Google Scholar
- arXiv
- ResearchGate
- Semantic Scholar
- CORE
- SpringerLink
- ScienceDirect

The application provides a unified interface for searching, filtering, and exporting research paper information.

## Features

- **Multi-source Search**: Query multiple academic databases simultaneously
- **Customizable Results**: Control the number of results per source
- **Advanced Filtering**: Sort by relevance, date, or citation count
- **Data Visualization**: View source distribution through interactive charts
- **Export Options**: Download results as CSV or Excel files
- **Responsive UI**: Clean, intuitive interface with expandable paper details

## Technical Implementation

The engine is built using:
- **Streamlit**: For the web application framework
- **BeautifulSoup**: For HTML parsing and web scraping
- **Pandas**: For data manipulation and export
- **Requests**: For HTTP requests to academic databases

## Usage

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/roody-research-engine.git
cd roody-research-engine
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

### Required Dependencies

Create a `requirements.txt` file with the following contents:

```
streamlit
requests
beautifulsoup4
pandas
lxml
openpyxl
```

## How It Works

The application works by:

1. Taking a user query and selected sources
2. Sending web requests to each selected academic database
3. Parsing the HTML responses to extract paper information
4. Consolidating results into a unified interface
5. Providing filtering, sorting, and export capabilities

## Implementation Details

### Search Functions

The application implements separate search functions for each academic database:

- `search_google_scholar()`: Scrapes Google Scholar results
- `search_arxiv()`: Uses the arXiv API
- `search_research_gate()`: Scrapes ResearchGate
- `search_semantic_scholar()`: Scrapes Semantic Scholar
- `search_core()`: Scrapes CORE
- `search_springer()`: Scrapes SpringerLink
- `search_science_direct()`: Scrapes ScienceDirect

Each function handles the specific structure and requirements of its respective source.

### Handling Rate Limiting

The application implements several strategies to avoid being rate-limited:

- Random delays between requests
- Rotating user agents
- Session persistence
- Retry logic with backoff

### Data Presentation

Results are presented in an organized manner:

- Each paper is displayed in an expandable section
- Papers are organized by source using tabs
- Key information (title, authors, abstract, citations) is clearly formatted
- Links to original papers are provided when available

## Future Improvements

Potential enhancements include:

- Adding more academic sources
- Implementing more advanced filtering options
- Adding citation export functionality
- Implementing user accounts for saving searches
- Adding semantic analysis of paper abstracts
- Implementing PDF preview functionality

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

Developed by Isara Madunika
- Email: isharamadunika9@gmail.com
- LinkedIn: [Isara Madunika](https://www.linkedin.com/in/isara-madunika-0686a3261)
- Phone: +94 770 264 992

## License

This project is licensed under the MIT License - see the LICENSE file for details.
