import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import io
from urllib.parse import quote

def search_google_scholar(query, num_results=100):
    """
    Scrape research papers from Google Scholar based on query
    """
    # Replace spaces with '+' for URL formatting
    formatted_query = quote(query)
    papers = []
    
    # Google Scholar shows maximum 10 results per page, so we need to paginate
    for start in range(0, min(num_results, 100), 10):
        # URL for Google Scholar search with pagination
        url = f"https://scholar.google.com/scholar?q={formatted_query}&hl=en&as_sdt=0,5&start={start}&num=10"
        
        # Headers to mimic a browser visit (helps avoid blocking)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            # Send request with increased timeout
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract paper information
            paper_entries = soup.find_all('div', class_='gs_ri')
            
            for entry in paper_entries:
                # Extract title and link
                title_element = entry.find('h3', class_='gs_rt')
                if title_element and title_element.a:
                    title = title_element.a.text
                    link = title_element.a.get('href', '')
                else:
                    title = title_element.text if title_element else "No title available"
                    link = ""
                
                # Extract authors, publication, year
                author_info = entry.find('div', class_='gs_a')
                author_text = author_info.text if author_info else "No author information"
                
                # Extract snippet/abstract
                snippet = entry.find('div', class_='gs_rs')
                snippet_text = snippet.text if snippet else "No abstract available"
                
                # Extract citation count
                citation_info = entry.find('div', class_='gs_fl')
                citation_text = "Citations not available"
                if citation_info:
                    for a_tag in citation_info.find_all('a'):
                        if 'Cited by' in a_tag.text:
                            citation_text = a_tag.text
                            break
                
                papers.append({
                    'title': title,
                    'authors': author_text,
                    'abstract': snippet_text,
                    'citations': citation_text,
                    'link': link,
                    'source': 'Google Scholar'
                })
            
            # Add delay between requests to avoid rate limiting
            time.sleep(random.uniform(1.5, 3))
            
            if len(papers) >= num_results:
                break
        
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching Google Scholar results: {e}")
            # Continue with next page despite error
            time.sleep(random.uniform(2, 4))
            continue
    
    return papers[:num_results]

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

# Modified ResearchGate function with better error handling
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
    
    # Use session to maintain cookies
    session = requests.Session()
    
    for retry in range(max_retries):
        try:
            # Add random delay between retries
            if retry > 0:
                time.sleep(random.uniform(3, 7))
            
            # Send request with session
            response = session.get(url, headers=headers, timeout=20)
            
            # Check for 403 error
            if response.status_code == 403:
                # Try with a completely different browser signature
                user_agents = [
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57'
                ]
                headers['User-Agent'] = user_agents[retry % len(user_agents)]
                
                # Different referer
                headers['Referer'] = 'https://scholar.google.com/'
                
                continue
                
                response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all paper entries
            paper_entries = soup.select('div.search-result-item')
            
            # If we found entries, process them
            if paper_entries:
                for entry in paper_entries[:max_results]:
                    # Extract title and link
                    title_element = entry.select_one('a.search-result-title')
                    if title_element:
                        title = title_element.text.strip()
                        link = "https://www.researchgate.net" + title_element.get('href', '') if title_element.get('href', '').startswith('/') else title_element.get('href', '')
                    else:
                        title = "No title available"
                        link = ""
                    
                    # Extract authors
                    author_elements = entry.select('div.publication-author-list span[itemprop="name"]')
                    authors_text = ', '.join([author.text.strip() for author in author_elements]) if author_elements else "No authors available"
                    
                    # Extract abstract
                    abstract = "Abstract not available in search results. Click the link to view full details."
                    
                    # Extract publication info and metrics
                    pub_date_element = entry.select_one('div.publication-meta-date')
                    pub_date = pub_date_element.text.strip() if pub_date_element else ""
                    
                    # Try to extract citation count
                    citation_element = entry.select_one('div.publication-meta-stats')
                    citation_text = citation_element.text.strip() if citation_element else "Metrics not available"
                    
                    # Combine publication date and metrics
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
                    
                    return papers[:max_results]
        
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    papers = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
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
