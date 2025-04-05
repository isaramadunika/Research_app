import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import io
from urllib.parse import quote


def search_google_scholar_with_serpapi(query, num_results=100, api_key=None):
    """
    Search Google Scholar using SerpAPI.
    This is a more reliable approach as SerpAPI handles all anti-scraping measures.
    Requires a SerpAPI key (free trial available at serpapi.com).
    
    Parameters:
    query (str): The search query
    num_results (int): Number of results to retrieve (max 100)
    api_key (str): Your SerpAPI key. If None, will try to get from environment variable
    
    Returns:
    list: List of paper dictionaries with title, authors, abstract, etc.
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.environ.get("SERPAPI_KEY")
        if not api_key:
            st.error("No SerpAPI key provided. Get one at https://serpapi.com/")
            return []
    
    # Base parameters for all requests
    base_params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "hl": "en",  # Language
        "as_sdt": "0,5"  # Search all document types
    }
    
    all_papers = []
    papers_per_page = 10  # SerpAPI usually returns 10 results per page
    
    # Calculate how many pages we need
    num_pages = (num_results + papers_per_page - 1) // papers_per_page
    
    st.info(f"Fetching up to {num_results} papers using SerpAPI (estimated {num_pages} pages)")
    
    # Loop through the pages
    for page in range(num_pages):
        start_index = page * papers_per_page
        
        # Update parameters for pagination
        params = base_params.copy()
        params["start"] = start_index
        
        try:
            st.info(f"Fetching page {page + 1}...")
            
            # Make request to SerpAPI
            response = requests.get("https://serpapi.com/search", params=params)
            
            # Check if request was successful
            if response.status_code != 200:
                st.error(f"Error: Received status code {response.status_code} from SerpAPI")
                if response.status_code == 401:
                    st.error("Authentication error: Check your API key")
                break
            
            # Parse JSON response
            data = response.json()
            
            # Check for error
            if "error" in data:
                st.error(f"SerpAPI Error: {data['error']}")
                break
            
            # Extract organic results
            organic_results = data.get("organic_results", [])
            
            if not organic_results:
                st.warning("No more results available")
                break
            
            # Process each result
            for result in organic_results:
                title = result.get("title", "No title available")
                link = result.get("link", "")
                
                # Extract authors and publication info
                publication_info = result.get("publication_info", {})
                authors_text = publication_info.get("summary", "No author information")
                
                # Extract snippet/abstract
                snippet = result.get("snippet", "No abstract available")
                
                # Extract citation count
                citation_info = result.get("inline_links", {}).get("cited_by", {})
                citation_count = citation_info.get("total", 0)
                citation_text = f"Cited by {citation_count}" if citation_count else "Citations not available"
                
                # Create paper dictionary
                paper = {
                    'title': title,
                    'authors': authors_text,
                    'abstract': snippet,
                    'citations': citation_text,
                    'link': link,
                    'source': 'Google Scholar via SerpAPI'
                }
                
                all_papers.append(paper)
                
                # Check if we have enough papers
                if len(all_papers) >= num_results:
                    break
            
            # Check if we have enough papers
            if len(all_papers) >= num_results:
                break
            
            # Add a small delay between pages to be nice to the API
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            st.error(f"Error fetching results from SerpAPI: {str(e)}")
            break
    
    return all_papers[:num_results]

# Alternative using scholarly library
def try_scholarly_search(query, num_results=100):
    """Try to search using the scholarly library"""
    try:
        from scholarly import scholarly
        import scholarly.scholarly as sch
        
        st.info("Using scholarly library to search Google Scholar")
        papers = []
        
        # Configure scholarly to use a proxy if needed
        # scholarly.use_proxy(...)
        
        # Sometimes scholarly needs to be configured with proxies to avoid blocking
        # See: https://scholarly.readthedocs.io/en/latest/Config.html
        
        # Get a generator of publications
        search_query = scholarly.search_pubs(query)
        
        # Iterate through search results
        for i in range(min(num_results, 100)):
            try:
                publication = next(search_query)
                
                # Extract the relevant information
                title = publication.get('bib', {}).get('title', 'No title available')
                authors = publication.get('bib', {}).get('author', [])
                authors_text = ', '.join(authors) if authors else 'No author information'
                abstract = publication.get('bib', {}).get('abstract', 'No abstract available')
                citations = publication.get('num_citations', 0)
                citation_text = f"Cited by {citations}" if citations else "Citations not available"
                link = publication.get('pub_url', '')
                
                papers.append({
                    'title': title,
                    'authors': authors_text,
                    'abstract': abstract,
                    'citations': citation_text,
                    'link': link,
                    'source': 'Google Scholar via scholarly'
                })
                
                # Small delay to avoid triggering limits
                time.sleep(random.uniform(1, 3))
                
            except StopIteration:
                # No more results
                break
            except Exception as e:
                st.warning(f"Error fetching scholarly result {i+1}: {str(e)}")
                time.sleep(random.uniform(5, 10))
                continue
        
        return papers
    
    except ImportError:
        st.error("scholarly library is not installed. Install it with: pip install scholarly")
        return []
    except Exception as e:
        st.error(f"Error with scholarly search: {str(e)}")
        return []

# Function to try multiple methods and return the first one that works
def multi_method_search(query, num_results=100, serpapi_key=None):
    """Try multiple methods to get Google Scholar results and return the first successful one"""
    
    # Method 1: Try SerpAPI if key is provided
    if serpapi_key:
        st.info("Trying SerpAPI method...")
        papers = search_google_scholar_with_serpapi(query, num_results, serpapi_key)
        if papers:
            return papers
    
    # Method 2: Try scholarly
    st.info("Trying scholarly method...")
    papers = try_scholarly_search(query, num_results)
    if papers:
        return papers
    
    # Method 3: Fall back to a more reliable source - Semantic Scholar API
    # This is not Google Scholar but is a reliable academic search API
    st.info("Falling back to Semantic Scholar API...")
    papers = search_semantic_scholar(query, num_results)
    return papers

def search_semantic_scholar(query, num_results=100):
    """
    Search Semantic Scholar API as a fallback
    This is a free, reliable API for academic papers
    """
    papers = []
    
    # Semantic Scholar API endpoint
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    try:
        # Set parameters
        params = {
            "query": query,
            "limit": min(num_results, 100),
            "fields": "title,authors,abstract,citationCount,url,year"
        }
        
        # Make request
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            st.error(f"Semantic Scholar API error: Status code {response.status_code}")
            return papers
            
        data = response.json()
        
        # Process papers
        for paper in data.get("data", []):
            # Extract authors
            authors = [author.get("name", "") for author in paper.get("authors", [])]
            authors_text = ", ".join(authors) if authors else "No author information"
            
            # Create paper entry
            papers.append({
                "title": paper.get("title", "No title available"),
                "authors": authors_text,
                "abstract": paper.get("abstract", "No abstract available"),
                "citations": f"Cited by {paper.get('citationCount', 0)}",
                "link": paper.get("url", ""),
                "source": "Semantic Scholar API"
            })
            
    except Exception as e:
        st.error(f"Error with Semantic Scholar API: {str(e)}")
        
    return papers

# Example usage:
# Get your API key from https://serpapi.com/ (they offer a free trial)
# papers = multi_method_search("machine learning", num_results=100, serpapi_key="your_serpapi_key_here")

def search_arxiv(query, max_results=100):
    """
    Scrape research papers from arXiv based on query
    """
    # Format query for arXiv API
    formatted_query = query.replace(' ', '+')
    url = f"http://export.arxiv.org/api/query?search_query=all:{formatted_query}&start=0&max_results={max_results}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Parse XML content
        soup = BeautifulSoup(response.content, 'xml')
        
        papers = []
        entries = soup.find_all('entry')
        
        for entry in entries:
            title = entry.find('title').text if entry.find('title') else "No title available"
            title = re.sub(r'\s+', ' ', title).strip()  # Clean up whitespace
            
            # Get authors
            authors = entry.find_all('author')
            author_names = [author.find('name').text for author in authors if author.find('name')]
            authors_text = ', '.join(author_names) if author_names else "No authors available"
            
            # Get abstract
            abstract = entry.find('summary').text if entry.find('summary') else "No abstract available"
            abstract = re.sub(r'\s+', ' ', abstract).strip()  # Clean up whitespace
            
            # Get link
            link = entry.find('id').text if entry.find('id') else ""
            pdf_link = ""
            links = entry.find_all('link')
            for link_tag in links:
                if link_tag.get('title') == 'pdf':
                    pdf_link = link_tag.get('href')
                    break
            
            # Get published date
            published = entry.find('published').text[:10] if entry.find('published') else "Date unknown"
            
            papers.append({
                'title': title,
                'authors': authors_text,
                'abstract': abstract,
                'citations': f"Published: {published}",
                'link': pdf_link if pdf_link else link,
                'source': 'arXiv'
            })
        
        return papers[:max_results]
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching arXiv results: {e}")
        return []

def search_research_gate(query, max_results=100):
    """
    Scrape research papers from ResearchGate based on query
    """
    formatted_query = quote(query)
    url = f"https://www.researchgate.net/search/publication?q={formatted_query}"
    
    # Enhanced headers with more realistic browser fingerprint
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/search?q=research+papers+researchgate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="114", "Chromium";v="114", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'DNT': '1',
    }

    papers = []
    max_retries = 3
    session = requests.Session()

    try:
        for retry in range(max_retries):
            # Add random delay between retries
            if retry > 0:
                time.sleep(random.uniform(3, 7))

            response = session.get(url, headers=headers, timeout=20)

            if response.status_code == 403:
                # Try different headers
                user_agents = [
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57'
                ]
                headers['User-Agent'] = user_agents[retry % len(user_agents)]
                headers['Referer'] = 'https://scholar.google.com/'
                continue

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            paper_entries = soup.select('div.search-result-item')

            if paper_entries:
                for entry in paper_entries[:max_results]:
                    title_element = entry.select_one('a.search-result-title')
                    title = title_element.text.strip() if title_element else "No title available"
                    link = (
                        "https://www.researchgate.net" + title_element.get('href', '')
                        if title_element and title_element.get('href', '').startswith('/')
                        else (title_element.get('href', '') if title_element else "")
                    )

                    author_elements = entry.select('div.publication-author-list span[itemprop="name"]')
                    authors_text = ', '.join([author.text.strip() for author in author_elements]) if author_elements else "No authors available"

                    abstract = "Abstract not available in search results. Click the link to view full details."

                    pub_date_element = entry.select_one('div.publication-meta-date')
                    pub_date = pub_date_element.text.strip() if pub_date_element else ""

                    citation_element = entry.select_one('div.publication-meta-stats')
                    citation_text = citation_element.text.strip() if citation_element else "Metrics not available"

                    pub_info = []
                    if pub_date:
                        pub_info.append(pub_date)
                    if citation_text and citation_text != "Metrics not available":
                        pub_info.append(citation_text)

                    combined_info = " | ".join(pub_info) if pub_info else "Publication info not available"

                    papers.append({
                        'title': title,
                        'authors': authors_text,
                        'abstract': abstract,
                        'citations': combined_info,
                        'link': link,
                        'source': 'ResearchGate'
                    })
        return papers

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching ResearchGate results: {e}")
        return []

def search_semantic_scholar(query, max_results=100):
    """
    Scrape research papers from Semantic Scholar based on query
    """
    formatted_query = quote(query)
    url = f"https://www.semanticscholar.org/search?q={formatted_query}&sort=relevance"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    papers = []
    
    try:
        # Send request
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all paper entries (adjust these selectors based on actual site structure)
        paper_entries = soup.select('div.result-item')
        
        for entry in paper_entries[:max_results]:
            # Extract title and link
            title_element = entry.select_one('a.search-result-title')
            if title_element:
                title = title_element.text.strip()
                link = "https://www.semanticscholar.org" + title_element.get('href', '')
            else:
                title = "No title available"
                link = ""
            
            # Extract authors
            author_elements = entry.select('a.author-list__link')
            authors_text = ', '.join([author.text for author in author_elements]) if author_elements else "No authors available"
            
            # Extract abstract
            abstract_element = entry.select_one('div.search-result-abstract')
            abstract = abstract_element.text.strip() if abstract_element else "No abstract available"
            
            # Extract citation count
            citation_element = entry.select_one('span.citation-stat__count')
            citation_text = f"Cited by {citation_element.text}" if citation_element else "Citations not available"
            
            papers.append({
                'title': title,
                'authors': authors_text,
                'abstract': abstract,
                'citations': citation_text,
                'link': link,
                'source': 'Semantic Scholar'
            })
        
        return papers[:max_results]
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching Semantic Scholar results: {e}")
        return []

def search_core(query, max_results=100):
    """
    Scrape research papers from CORE based on query
    """
    formatted_query = quote(query)
    url = f"https://core.ac.uk/search?q={formatted_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    papers = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all paper entries (adjust selectors based on site structure)
        paper_entries = soup.select('article.search-result')
        
        for entry in paper_entries[:max_results]:
            # Extract title and link
            title_element = entry.select_one('h3.title a')
            if title_element:
                title = title_element.text.strip()
                link = "https://core.ac.uk" + title_element.get('href', '') if title_element.get('href', '').startswith('/') else title_element.get('href', '')
            else:
                title = "No title available"
                link = ""
            
            # Extract authors
            author_element = entry.select_one('div.authors')
            authors_text = author_element.text.strip() if author_element else "No authors available"
            
            # Extract abstract
            abstract_element = entry.select_one('div.description')
            abstract = abstract_element.text.strip() if abstract_element else "No abstract available"
            
            # Extract publication info
            pub_element = entry.select_one('div.publisher')
            pub_text = pub_element.text.strip() if pub_element else "Publication info not available"
            
            papers.append({
                'title': title,
                'authors': authors_text,
                'abstract': abstract,
                'citations': pub_text,
                'link': link,
                'source': 'CORE'
            })
        
        return papers[:max_results]
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching CORE results: {e}")
        return []

def search_springer(query, max_results=100):
    """
    Scrape research papers from SpringerLink based on query
    """
    formatted_query = quote(query)
    url = f"https://link.springer.com/search?query={formatted_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    papers = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all paper entries
        paper_entries = soup.select('li.has-cover')
        
        for entry in paper_entries[:max_results]:
            # Extract title and link
            title_element = entry.select_one('h2 a')
            if title_element:
                title = title_element.text.strip()
                link = "https://link.springer.com" + title_element.get('href', '') if title_element.get('href', '').startswith('/') else title_element.get('href', '')
            else:
                title = "No title available"
                link = ""
            
            # Extract authors
            author_elements = entry.select('span.authors__name')
            authors_text = ', '.join([author.text.strip() for author in author_elements]) if author_elements else "No authors available"
            
            # Extract publication date
            date_element = entry.select_one('p.meta')
            date_text = date_element.text.strip() if date_element else "Date not available"
            
            # Extract content type (e.g., article, book chapter)
            type_element = entry.select_one('span.content-type')
            content_type = type_element.text.strip() if type_element else "Content type not specified"
            
            # No abstract available on search page
            abstract = "Abstract not available on search page. Click the link to view full details."
            
            papers.append({
                'title': title,
                'authors': authors_text,
                'abstract': abstract,
                'citations': f"{content_type} | {date_text}",
                'link': link,
                'source': 'SpringerLink'
            })
        
        return papers[:max_results]
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching SpringerLink results: {e}")
        return []

def search_science_direct(query, max_results=100):
    """
    Scrape research papers from ScienceDirect based on query
    """
    formatted_query = quote(query)
    url = f"https://www.sciencedirect.com/search?qs={formatted_query}"
    
    # Enhanced headers to avoid "unsupported_browser" error
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'sec-ch-ua': '"Google Chrome";v="114", "Chromium";v="114", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
    }
    
    papers = []
    
    # Use session to maintain cookies
    session = requests.Session()
    
    try:
        # Add random delay before request
        time.sleep(random.uniform(2, 4))
        
        # Send request with session
        response = session.get(url, headers=headers, timeout=20)
        
        # Check for 'unsupported_browser' in URL
        if 'unsupported_browser' in response.url:
            time.sleep(2)
            # Try with a different User-Agent
            headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15'
            response = session.get(url, headers=headers, timeout=20)
            
            if 'unsupported_browser' in response.url:
                st.warning("ScienceDirect reports unsupported browser. Skipping this source.")
                return []
        
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all paper entries
        paper_entries = soup.select('li.ResultItem')
        
        for entry in paper_entries[:max_results]:
            # Extract title and link
            title_element = entry.select_one('h2 a')
            if title_element:
                title = title_element.text.strip()
                link = "https://www.sciencedirect.com" + title_element.get('href', '') if title_element.get('href', '').startswith('/') else title_element.get('href', '')
            else:
                title = "No title available"
                link = ""
            
            # Extract authors
            author_elements = entry.select('.Authors li')
            authors_text = ', '.join([author.text.strip() for author in author_elements]) if author_elements else "No authors available"
            
            # Extract publication info
            pub_element = entry.select_one('.SubType')
            pub_date_element = entry.select_one('.srctitle-date-fields')
            
            pub_info = []
            if pub_element:
                pub_info.append(pub_element.text.strip())
            if pub_date_element:
                pub_info.append(pub_date_element.text.strip())
            
            pub_text = ' | '.join(pub_info) if pub_info else "Publication info not available"
            
            # Extract abstract
            abstract_element = entry.select_one('.ResultText')
            abstract = abstract_element.text.strip() if abstract_element else "No abstract available"
            
            papers.append({
                'title': title,
                'authors': authors_text,
                'abstract': abstract,
                'citations': pub_text,
                'link': link,
                'source': 'ScienceDirect'
            })
        
        return papers[:max_results]
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching ScienceDirect results: {e}")
        return []

def main():
    st.set_page_config(
        page_title="ROODY RESEARCH ENGINE",
        page_icon="📚",
        layout="wide"
    )
    
    # Custom CSS for styling
    st.markdown("""
    <style>
    .research-header {
        background-color: #1E3A8A;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        color: white;
    }
    
    .stMarkdown {
        color: white;
        text-align: justify;
    }
    /* Add specific styling for abstract container */
    .stMarkdownContainer.abstract-container {
    background-color: #f7f7f7;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
    font-style: italic;
    }
    
    .footer {
        background-color: #1E3A8A;
        padding: 15px;
        border-radius: 10px;
        margin-top: 30px;
        color: white;
        text-align: center;
    }
    
    .contact-info {
        margin-top: 10px;
        font-size: 14px;
    }
    
    .logo-text {
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header section with branding
    st.markdown("""
    <div class="research-header">
        <div class="logo-text">ROODY RESEARCH ENGINE</div>
        <h3 style="text-align: center;">Find research papers across multiple academic databases</h3>
        <p style="text-align: center;">Helping students easily search and find relevant research papers</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Search parameters with improved UI
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        search_query = st.text_input("Enter a research topic:", placeholder="e.g., machine learning, climate change, etc.")
    
    with col2:
        sources = st.multiselect(
            "Select sources:",
            ["Google Scholar", "arXiv", "ResearchGate", "Semantic Scholar", "CORE", "SpringerLink", "ScienceDirect"],
            default=["Google Scholar", "arXiv"]
        )
    
    with col3:
        num_results = st.number_input("Results per source:", min_value=5, max_value=100, value=20, step=5)
    
    # Advanced options in expandable section
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            sort_option = st.selectbox("Sort results by:", ["Relevance", "Date (newest first)", "Citations (highest first)"])
        with col2:
            filter_option = st.selectbox("Filter results:", ["All papers", "Full text available only", "Recent (last 5 years)"])
    
    # Add search button with better styling
    search_button = st.button("🔍 Search for Papers", type="primary", use_container_width=True)
    
    if search_button or 'search_performed' in st.session_state:
        if not search_query:
            st.warning("Please enter a search query")
            return
            
        if not sources:
            st.warning("Please select at least one source")
            return
            
        if search_button:
            st.session_state['search_performed'] = True
            st.session_state['search_query'] = search_query
            st.session_state['sources'] = sources
            st.session_state['num_results'] = num_results
        else:
            search_query = st.session_state['search_query']
            sources = st.session_state['sources']
            num_results = st.session_state['num_results']
        
        progress_text = "Searching academic databases. Please wait..."
        progress_bar = st.progress(0, text=progress_text)
        
        papers = []
        total_sources = len(sources)
        
        for i, source in enumerate(sources):
            progress_bar.progress((i / total_sources), text=f"Searching {source}...")
            
            if source == "Google Scholar":
                google_papers = search_google_scholar(search_query, num_results)
                papers.extend(google_papers)
                time.sleep(random.uniform(1, 2))
            
            elif source == "arXiv":
                arxiv_papers = search_arxiv(search_query, num_results)
                papers.extend(arxiv_papers)
                time.sleep(random.uniform(0.5, 1))
            
            elif source == "ResearchGate":
                researchgate_papers = search_research_gate(search_query, num_results)
                papers.extend(researchgate_papers)
                time.sleep(random.uniform(1, 2))
            
            elif source == "Semantic Scholar":
                semantic_papers = search_semantic_scholar(search_query, num_results)
                papers.extend(semantic_papers)
                time.sleep(random.uniform(1, 2))
            
            elif source == "CORE":
                core_papers = search_core(search_query, num_results)
                papers.extend(core_papers)
                time.sleep(random.uniform(1, 2))
            
            elif source == "SpringerLink":
                springer_papers = search_springer(search_query, num_results)
                papers.extend(springer_papers)
                time.sleep(random.uniform(1, 2))
            
            elif source == "ScienceDirect":
                science_direct_papers = search_science_direct(search_query, num_results)
                papers.extend(science_direct_papers)
                time.sleep(random.uniform(1, 2))
        
        progress_bar.progress(1.0, text="Search completed!")
        time.sleep(0.5)
        progress_bar.empty()
        
        if papers:
            # Apply sorting if selected
            if sort_option == "Date (newest first)":
                # This is just an example - actual implementation would depend on date extraction
                pass
            elif sort_option == "Citations (highest first)":
                # Example citation sorting logic (would need proper citation number extraction)
                pass
            
            # Apply filtering if selected
            if filter_option == "Recent (last 5 years)":
                # Example filtering logic
                pass
            elif filter_option == "Full text available only":
                # Example filtering logic
                papers = [paper for paper in papers if paper['link']]
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(papers)
            
            # Show results count and summary
            st.success(f"Found {len(papers)} research papers on '{search_query}' from {len(sources)} sources")
            
            # Source distribution visualization
            source_counts = df['source'].value_counts()
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Results by Source")
                st.bar_chart(source_counts)
            
            with col2:
                st.subheader("Summary")
                for source, count in source_counts.items():
                    st.write(f"- {source}: {count} papers")
            
            # Display papers with tabs for different sources
            st.subheader("Research Papers")
            
            # Create tabs for each source
            tabs = st.tabs(["All Sources"] + list(source_counts.index))
            
            # All Sources tab
            with tabs[0]:
                for i, paper in enumerate(papers):
                    with st.expander(f"{i+1}. {paper['title']} ({paper['source']})"):
                        st.markdown(f"**Authors:** {paper['authors']}")
                        st.markdown(f"<div class='abstract-container'><strong>Abstract:</strong> {paper['abstract']}</div>", unsafe_allow_html=True)
                        st.markdown(f"**{paper['citations']}**")
                        if paper['link']:
                            st.markdown(f"[View Paper]({paper['link']})")
                        st.markdown("---")
            
            # Tabs for each source
            for i, source in enumerate(source_counts.index, 1):
                with tabs[i]:
                    source_papers = df[df['source'] == source]
                    for j, (_, paper) in enumerate(source_papers.iterrows()):
                        with st.expander(f"{j+1}. {paper['title']}"):
                            st.markdown(f"**Authors:** {paper['authors']}")
                            st.markdown(f"<div class='abstract-container'><strong>Abstract:</strong> {paper['abstract']}</div>", unsafe_allow_html=True)
                            st.markdown(f"**{paper['citations']}**")
                            if paper['link']:
                                st.markdown(f"[View Paper]({paper['link']})")
                            st.markdown("---")
            
            # Add download options
            st.subheader("Download Results")
            col1, col2 = st.columns(2)
            
            csv = df.to_csv(index=False).encode('utf-8')
            with col1:
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"research_papers_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            
            # Create Excel file - Fixed for missing xlsxwriter dependency
            try:
                # Try to create Excel file if xlsxwriter is available
                excel_file = io.BytesIO()
                with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Research Papers", index=False)
                excel_data = excel_file.getvalue()
                
                with col2:
                    st.download_button(
                        label="Download as Excel",
                        data=excel_data,
                        file_name=f"research_papers_{search_query.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            except ImportError:
                with col2:
                    st.error("Excel download not available. Please install openpyxl package.")
                    st.info("Run: pip install openpyxl")
        else:
            st.warning("No research papers found. Try a different search term or source.")
    
    # Footer with contact information
    st.markdown("""
    <div class="footer">
        <p>© 2025 ROODY RESEARCH ENGINE - Developed by Isara Madunika</p>
        <p>NSBM Green University</p>
        <div class="contact-info">
            <p>Contact: <a href="mailto:isharamadunika9@gmail.com" style="color: white;">isharamadunika9@gmail.com</a> | 
            <a href="https://www.linkedin.com/in/isara-madunika-0686a3261" target="_blank" style="color: white;">LinkedIn</a> | 
            +94 770 264 992</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
